import subprocess
import time
import sys
from pathlib import Path

is_frozen = getattr(sys, 'frozen', False)

RUNTIME_DIR = Path(".runtime")
RESTART_FLAG = RUNTIME_DIR / "restart.flag"

def launch_app():
    command = ["app.exe"] if is_frozen else \
        ["poetry", "run", "start-app"]
    return subprocess.Popen(command)

def watch_for_restart():
    while True:
        if RESTART_FLAG.exists():
            print("Restart flag detected.")
            return True
        time.sleep(0.5)

def main():
    RUNTIME_DIR.mkdir(exist_ok=True)
    while True:
        proc = launch_app()
        if watch_for_restart():
            proc.terminate()
            proc.wait()
            RESTART_FLAG.unlink(missing_ok=True)
        else:
            break

if __name__ == "__main__":
    main()
