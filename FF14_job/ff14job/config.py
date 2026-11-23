"""アプリ設定。"""
from __future__ import annotations

import os

HOST = os.environ.get("FF14JOB_HOST", "127.0.0.1")
BROWSER_HOST = os.environ.get("FF14JOB_BROWSER_HOST", "ff14job.localhost")
PORT = int(os.environ.get("FF14JOB_PORT", "5815"))
