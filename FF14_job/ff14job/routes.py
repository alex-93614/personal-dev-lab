"""ページと JSON API のルーティング。"""
from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .charts import job_tags, radar_svg
from .data import AXES, JOBS, QUESTIONS, ROLES, SCALE_LABELS
from .scoring import AnswerError, answers_from_mapping, decode_answers, diagnose, trait_rows

bp = Blueprint("main", __name__)


@bp.app_template_global()
def tags_for(job):
    return job_tags(job)


@bp.get("/")
def index():
    jobs_by_role = {r.key: [j for j in JOBS if j.role == r.key] for r in ROLES}
    return render_template("index.html", active="index", jobs_by_role=jobs_by_role, axes=AXES)


@bp.get("/quiz")
def quiz():
    prefill: list[int] | None = None
    if request.args.get("a"):
        try:
            prefill = decode_answers(request.args["a"])
        except AnswerError:
            prefill = None
    return render_template("quiz.html", active="quiz", questions=QUESTIONS,
                           scale_labels=SCALE_LABELS, prefill=prefill)


@bp.post("/result")
def submit():
    try:
        answers = answers_from_mapping(request.form)
    except AnswerError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.quiz"))
    return redirect(url_for("main.result", a="".join(map(str, answers))))


@bp.get("/result")
def result():
    try:
        answers = decode_answers(request.args.get("a", ""))
    except AnswerError as exc:
        flash(str(exc) + " もう一度診断してください。", "error")
        return redirect(url_for("main.quiz"))
    diag = diagnose(answers)
    top = diag.top
    return render_template(
        "result.html",
        active="result",
        diag=diag,
        top=top,
        runners=diag.ranking[1:3],
        traits=trait_rows(diag.traits),
        radar=radar_svg(diag.traits, compare=top.job.profile, compare_color=top.job.color),
        share_url=url_for("main.result", a=diag.code, _external=True),
    )


@bp.get("/jobs")
def jobs():
    jobs_by_role = {r.key: [j for j in JOBS if j.role == r.key] for r in ROLES}
    return render_template("jobs.html", active="jobs", jobs_by_role=jobs_by_role)


# ---------------------------------------------------------------- JSON API
@bp.get("/api/questions")
def api_questions():
    return jsonify([
        {
            "id": q.id,
            "category": q.category,
            "text": q.text,
            "kind": q.kind,
            "choices": SCALE_LABELS if q.kind == "scale" else [o.label for o in q.options],
        }
        for q in QUESTIONS
    ])


@bp.post("/api/diagnose")
def api_diagnose():
    payload = request.get_json(silent=True) or {}
    try:
        if isinstance(payload.get("code"), str):
            answers = decode_answers(payload["code"])
        else:
            answers = answers_from_mapping(payload.get("answers") or {})
    except AnswerError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(diagnose(answers).to_dict())
