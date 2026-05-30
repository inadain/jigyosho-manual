#!/usr/bin/env python3
"""
030_事業所マニュアル — HTML変更を自動検知してGitHubへプッシュ
"""
import time
import subprocess
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

REPO_DIR = Path(__file__).parent
LOG_FILE = REPO_DIR / "auto_push.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

DEBOUNCE = 5  # 変更後、この秒数待ってからプッシュ（連続保存をまとめる）
_timer = None


def git_push():
    try:
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        # 変更がなければスキップ
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        if not status.stdout.strip():
            log.info("変更なし — スキップ")
            return

        subprocess.run(
            ["git", "commit", "-m", "マニュアル更新（自動コミット）"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        push = subprocess.run(
            ["git", "push"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        if push.returncode == 0:
            log.info("✓ GitHubへプッシュ完了")
        else:
            log.error(f"プッシュ失敗: {push.stderr.strip()}")
    except Exception as e:
        log.error(f"エラー: {e}")


class HtmlHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".html" and not path.name.startswith("."):
            self._schedule(path.name)

    def on_created(self, event):
        self.on_modified(event)

    def _schedule(self, name):
        global _timer
        if _timer:
            _timer.cancel()
        import threading
        log.info(f"変更検知: {name} — {DEBOUNCE}秒後にプッシュ")
        _timer = threading.Timer(DEBOUNCE, git_push)
        _timer.start()


if __name__ == "__main__":
    log.info(f"監視開始: {REPO_DIR}")
    observer = Observer()
    observer.schedule(HtmlHandler(), str(REPO_DIR), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
