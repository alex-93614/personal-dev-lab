"""結果画面用の表示ヘルパー（レーダーチャート SVG・特徴タグ）。"""
from __future__ import annotations

import math

from markupsafe import Markup, escape

from .data import AXES, Job


def radar_svg(values: dict[str, float], compare: dict[str, float] | None = None,
              size: int = 340, color: str = "#fcd34d", compare_color: str = "#a8d2e6") -> Markup:
    """特性値（0〜1）のレーダーチャートを SVG 文字列で返す。

    compare を渡すと、比較用の多角形（ジョブの特性など）を重ねて描く。
    """
    cx = cy = size / 2
    radius = size / 2 - 58
    n = len(AXES)

    def point(i: int, r: float) -> tuple[float, float]:
        ang = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    def poly(vals: dict[str, float]) -> str:
        pts = (point(i, radius * max(0.04, vals[a.key])) for i, a in enumerate(AXES))
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    parts = [f'<svg class="radar" viewBox="0 0 {size} {size}" role="img" aria-label="特性レーダーチャート">']
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, radius * ring) for i in range(n)))
        cls = "radar-ring radar-ring-mid" if ring == 0.5 else "radar-ring"
        parts.append(f'<polygon class="{cls}" points="{pts}"/>')
    for i in range(n):
        x, y = point(i, radius)
        parts.append(f'<line class="radar-spoke" x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"/>')
    if compare:
        parts.append(f'<polygon class="radar-compare" style="--rc:{escape(compare_color)}" points="{poly(compare)}"/>')
    parts.append(f'<polygon class="radar-area" style="--rc:{escape(color)}" points="{poly(values)}"/>')
    for i, a in enumerate(AXES):
        x, y = point(i, radius * max(0.04, values[a.key]))
        parts.append(f'<circle class="radar-dot" style="--rc:{escape(color)}" cx="{x:.1f}" cy="{y:.1f}" r="3.2"/>')
        lx, ly = point(i, radius + 26)
        anchor = "middle" if abs(lx - cx) < 8 else ("start" if lx > cx else "end")
        parts.append(
            f'<text class="radar-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{escape(a.label)}'
            f'<tspan class="radar-val" x="{lx:.1f}" dy="15">{round(values[a.key] * 100)}</tspan></text>'
        )
    parts.append("</svg>")
    return Markup("".join(parts))


def job_tags(job: Job) -> list[str]:
    """ジョブの特性値から、ひと目で分かる特徴タグを作る。"""
    p = job.profile
    tags: list[str] = []
    if p["complexity"] >= 0.7:
        tags.append("テクニカル")
    elif p["complexity"] <= 0.3:
        tags.append("シンプル操作")
    if p["mobility"] >= 0.8:
        tags.append("高機動")
    elif p["mobility"] <= 0.2:
        tags.append("詠唱じっくり")
    if p["burst"] >= 0.85:
        tags.append("バースト型")
    if p["synergy"] >= 0.75:
        tags.append("味方強化")
    elif p["synergy"] <= 0.2:
        tags.append("自己完結")
    if p["planning"] >= 0.85:
        tags.append("計画型")
    elif p["planning"] <= 0.25:
        tags.append("アドリブ型")
    if job.role not in ("healer",) and p["heal"] >= 0.3:
        tags.append("回復・蘇生も可" if job.role in ("caster",) else "自己回復")
    if p["dps"] >= 1.0:
        tags.append("火力特化")
    return tags
