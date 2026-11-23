"""FF14 ジョブ適性診断アプリ 起動スクリプト。"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

# 仮想環境 (.venv) を有効化せずにシステムの python から実行された場合、
# 自動でワークスペースの .venv\Scripts\python.exe に切り替えて再実行する
try:
    import flask as _flask  # noqa: F401
except ModuleNotFoundError:
    _here = Path(__file__).resolve().parent
    for _cand in (_here / ".venv" / "Scripts" / "python.exe",
                  _here.parent / ".venv" / "Scripts" / "python.exe"):
        if _cand.exists() and _cand.resolve() != Path(sys.executable).resolve():
            raise SystemExit(subprocess.call([str(_cand), __file__, *sys.argv[1:]]))
    raise

from ff14job import create_app
from ff14job.config import BROWSER_HOST, HOST, PORT

app = create_app()


def main() -> None:
    url = f"http://{BROWSER_HOST}:{PORT}"
    if os.environ.get("FF14JOB_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"FF14 Job Finder starting at {url} (Ctrl+C to stop)")
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
