"""FF14 ジョブ適性診断アプリ。"""
from __future__ import annotations

import os

from flask import Flask

from .data import AXES, JOBS, QUESTIONS, ROLE_MAP, ROLES


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.urandom(24))
    if config:
        app.config.update(config)
    app.json.ensure_ascii = False

    from .routes import bp
    app.register_blueprint(bp)

    # マクロ（import 先）からも参照できるよう globals に登録する
    app.jinja_env.globals.update(
        ROLES=ROLES,
        ROLE_MAP=ROLE_MAP,
        JOB_COUNT=len(JOBS),
        QUESTION_COUNT=len(QUESTIONS),
        AXIS_COUNT=len(AXES),
    )
    return app
