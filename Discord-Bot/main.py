import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WATCH_EXTENSIONS = {".py", ".json", ".env"}
IGNORE_DIRS = {".venv", "__pycache__"}


def iter_watched_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix in WATCH_EXTENSIONS:
            files.append(path)
    return files


def snapshot() -> dict[Path, float]:
    return {path: path.stat().st_mtime for path in iter_watched_files()}


def start_bot() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "bot.py"], cwd=ROOT)


def stop_bot(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        process.send_signal(signal.CTRL_BREAK_EVENT if hasattr(signal, "CTRL_BREAK_EVENT") else signal.SIGTERM)
    else:
        process.send_signal(signal.SIGTERM)

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    print("Starting Kingshot bot dev watcher. Press Ctrl+C to stop.")
    before = snapshot()
    process = start_bot()

    try:
        while True:
            time.sleep(1)

            if process.poll() is not None:
                print("bot.py stopped. Restarting in 2s...")
                time.sleep(2)
                process = start_bot()
                before = snapshot()
                continue

            current = snapshot()
            if current != before:
                print("File change detected. Restarting bot.py...")
                stop_bot(process)
                process = start_bot()
                before = snapshot()
    except KeyboardInterrupt:
        print("\nStopping dev watcher...")
        stop_bot(process)


if __name__ == "__main__":
    main()
