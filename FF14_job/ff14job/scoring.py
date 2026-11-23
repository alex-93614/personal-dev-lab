"""回答から特性ベクトルを算出し、各ジョブとの相性度を計算する。"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .data import AXES, AXIS_KEYS, AXIS_MAP, JOB_MAP, JOBS, QUESTIONS, ROLES, Job

# 選択式設問でジョブが直接一致したときの加点（相性度ポイント）
JOB_BONUS_POINTS = 4.0
# 距離 → 類似度 の変換係数（類似度 = 1 - 距離 × 係数）
DISTANCE_SCALE = 1.15
# 類似度に占めるコサイン類似度の割合
COSINE_MIX = 0.5


class AnswerError(ValueError):
    """回答データが不正なときに送出する。"""


# ---------------------------------------------------------------- エンコード
def encode_answers(answers: list[int]) -> str:
    """回答リスト（各 1 始まり）を共有用の数字列にする。"""
    return "".join(str(a) for a in answers)


def decode_answers(code: str) -> list[int]:
    """共有用の数字列を回答リストに戻す（不正なら AnswerError）。"""
    code = (code or "").strip()
    if len(code) != len(QUESTIONS) or not code.isdigit():
        raise AnswerError("回答コードの形式が正しくありません。")
    answers = [int(c) for c in code]
    validate_answers(answers)
    return answers


def validate_answers(answers: list[int]) -> None:
    if len(answers) != len(QUESTIONS):
        raise AnswerError(f"回答数が {len(QUESTIONS)} 問分ありません。")
    for q, a in zip(QUESTIONS, answers):
        if not isinstance(a, int) or not 1 <= a <= q.choices:
            raise AnswerError(f"{q.id} の回答が範囲外です。")


def answers_from_mapping(data) -> list[int]:
    """フォームや JSON の {q01: "3", ...} から回答リストを作る。"""
    answers: list[int] = []
    for q in QUESTIONS:
        raw = data.get(q.id)
        try:
            answers.append(int(raw))
        except (TypeError, ValueError):
            raise AnswerError(f"未回答の設問があります（{q.id}）。") from None
    validate_answers(answers)
    return answers


# ---------------------------------------------------------------- 計算
@dataclass
class JobScore:
    job: Job
    score: int          # 0〜99 の相性度
    distance: float
    bonus: float


@dataclass
class Diagnosis:
    answers: list[int]
    traits: dict[str, float]
    ranking: list[JobScore]
    roles: list[dict]
    reasons: list[str]

    @property
    def top(self) -> JobScore:
        return self.ranking[0]

    @property
    def code(self) -> str:
        return encode_answers(self.answers)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "traits": {k: round(v, 3) for k, v in self.traits.items()},
            "ranking": [
                {"key": s.job.key, "name": s.job.name, "role": s.job.role, "score": s.score}
                for s in self.ranking
            ],
            "roles": [{"key": r["role"].key, "label": r["role"].label, "score": r["score"]}
                      for r in self.roles],
            "reasons": self.reasons,
        }


def compute_traits(answers: list[int]) -> tuple[dict[str, float], dict[str, float]]:
    """特性ベクトル（各軸 0〜1）とジョブ別ボーナスを返す。"""
    total = {k: 0.0 for k in AXIS_KEYS}
    span = {k: 0.0 for k in AXIS_KEYS}
    bonus = {j.key: 0.0 for j in JOBS}

    for q, ans in zip(QUESTIONS, answers):
        if q.kind == "scale":
            v = (ans - 3) / 2.0          # -1.0 〜 +1.0
            for k, w in q.weights.items():
                total[k] += v * w
                span[k] += abs(w)
        else:
            opt = q.options[ans - 1]
            for k, w in opt.weights.items():
                total[k] += w
            for k in AXIS_KEYS:
                span[k] += max(abs(o.weights.get(k, 0.0)) for o in q.options)
            for jk, b in opt.jobs.items():
                bonus[jk] += b

    traits = {k: 0.5 + 0.5 * max(-1.0, min(1.0, total[k] / span[k])) if span[k] else 0.5
              for k in AXIS_KEYS}
    return traits, bonus


def job_distance(traits: dict[str, float], job: Job) -> float:
    """重み付きユークリッド距離（0〜1）。"""
    num = sum(a.weight * (traits[a.key] - job.profile[a.key]) ** 2 for a in AXES)
    den = sum(a.weight for a in AXES)
    return math.sqrt(num / den)


def job_cosine(traits: dict[str, float], job: Job) -> float:
    """中立(0.5)からの“傾き”同士のコサイン類似度（-1〜1）。

    距離だけだと、回答が中立寄りの人に“全体的に中庸なジョブ”ばかり出やすいため、
    「どちらに寄っているか」の一致度も加味する。
    """
    u = [(traits[a.key] - 0.5) * math.sqrt(a.weight) for a in AXES]
    j = [(job.profile[a.key] - 0.5) * math.sqrt(a.weight) for a in AXES]
    nu = math.sqrt(sum(x * x for x in u))
    nj = math.sqrt(sum(x * x for x in j))
    if nu < 1e-9 or nj < 1e-9:
        return 0.0
    return sum(x * y for x, y in zip(u, j)) / (nu * nj)


def job_similarity(traits: dict[str, float], job: Job) -> tuple[float, float]:
    """(類似度 0〜1, 距離) を返す。"""
    d = job_distance(traits, job)
    by_distance = max(0.0, 1.0 - d * DISTANCE_SCALE)
    by_cosine = (job_cosine(traits, job) + 1.0) / 2.0
    return COSINE_MIX * by_cosine + (1.0 - COSINE_MIX) * by_distance, d


ROLE_AXES = ("tank", "heal", "dps")


def _reasons(traits: dict[str, float], job: Job, bonus: float) -> list[str]:
    """上位ジョブとの「マッチ理由」を最大 4 件作る。

    ロール軸は“やりたい”側だけを 1 件、残りはスタイル軸から傾きの大きい順に選ぶ。
    """
    role_cands, style_cands = [], []
    for a in AXES:
        lean = traits[a.key] - 0.5
        if abs(lean) < 0.12 or abs(traits[a.key] - job.profile[a.key]) > 0.3:
            continue
        if (job.profile[a.key] - 0.5) * lean <= 0:
            continue
        if a.key in ROLE_AXES:
            if lean > 0:
                role_cands.append((lean * a.weight, a.high_reason))
        else:
            style_cands.append((abs(lean), a.high_reason if lean > 0 else a.low_reason))
    role_cands.sort(key=lambda c: c[0], reverse=True)
    style_cands.sort(key=lambda c: c[0], reverse=True)
    reasons = [t for _, t in role_cands[:1]] + [t for _, t in style_cands]
    reasons = reasons[:3]
    if bonus > 0:
        reasons.append(f"好みの武器・雰囲気が「{job.name}」とぴったり一致")
    return reasons


def diagnose(answers: list[int]) -> Diagnosis:
    validate_answers(answers)
    traits, bonus = compute_traits(answers)

    ranking: list[JobScore] = []
    for job in JOBS:
        sim, d = job_similarity(traits, job)
        raw = 100.0 * sim + bonus[job.key] * JOB_BONUS_POINTS
        ranking.append(JobScore(job, int(round(max(1.0, min(99.0, raw)))), d, bonus[job.key]))
    # 同点時は距離が近い順
    ranking.sort(key=lambda s: (-s.score, s.distance))

    roles = []
    for role in ROLES:
        best = max((s for s in ranking if s.job.role == role.key), key=lambda s: s.score)
        roles.append({"role": role, "score": best.score, "best": best.job})

    top = ranking[0]
    return Diagnosis(answers, traits, ranking, roles, _reasons(traits, top.job, top.bonus))


def trait_rows(traits: dict[str, float]) -> list[dict]:
    """両極バー表示用の行データ。"""
    return [{"axis": a, "value": traits[a.key], "pct": round(traits[a.key] * 100)} for a in AXES]


def job_by_key(key: str) -> Job | None:
    return JOB_MAP.get((key or "").upper())


def axis_label(key: str) -> str:
    return AXIS_MAP[key].label
