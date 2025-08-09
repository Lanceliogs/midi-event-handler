import subprocess
import time
import signal
from pathlib import Path
import yaml
import webbrowser
import argparse

from midi_event_handler.main import run_app
from midi_event_handler.tools.logtools import setup_logger
from midi_event_handler.tools.tray import setup_tray_icon
from midi_event_handler.core.config import (
    default_app_conf, RUNTIME_PATH, WHATSNEW_PATH
)
from midi_event_handler.web.shutdown import request_shutdown

import logging
log = logging.getLogger(__name__)

# === App Compilation Check ===
is_compiled = '__compiled__' in globals()

# === Runtime Paths ===
RUNTIME_DIR = Path(".runtime")
RESTART_FLAG = RUNTIME_DIR / "restart.flag"
EXIT_FLAG = RUNTIME_DIR / "exit.flag"
ICON_PATH = Path("meh-icon.ico")

# === Config Load ===
with open("config.yaml", "r") as f:
    conf = yaml.safe_load(f)

app_conf: dict = conf.get("app", default_app_conf())

# === App Launch ===
def launch_app():
    command = ["launcher.exe", "--app"] if is_compiled else ["poetry", "run", "start-app"]
    log.info(f"Launching app: {' '.join(command)}")
    return subprocess.Popen(command)


def watch_for_flag():
    while True:
        if RESTART_FLAG.exists():
            log.warning("🔁 Restart flag detected")
            return "restart"
        if EXIT_FLAG.exists():
            log.warning("🛑 Exit flag detected")
            return "exit"
        time.sleep(0.5)


def monitor_loop():
    port = app_conf.get('port', 8000)

    dashboard_url = f"http://127.0.0.1:{port}/meh.ui/dashboard"
    whatsnew_url = f"http://127.0.0.1:{port}/meh.ui/whatsnew"

    setup_tray_icon(dashboard_url)
    webbrowser.open(whatsnew_url if WHATSNEW_PATH.exists() else dashboard_url)

    RUNTIME_DIR.mkdir(exist_ok=True)

    while True:
        proc = launch_app()
        flag = watch_for_flag()

        request_shutdown(port)
        try:
            proc.wait(timeout=10)
        except KeyboardInterrupt:
            log.warning("KeyboardInterrupt detected in child process")
        except subprocess.TimeoutExpired:
            log.warning("TimeoutError detected. Killing the child instead.")
            proc.kill()
        finally:
            RESTART_FLAG.unlink(missing_ok=True)
            EXIT_FLAG.unlink(missing_ok=True)
        
        if flag == "exit":
            break
        if flag != "restart":
            log.warning(f"Unknown flag: {flag}")
            break


def main():
    setup_logger()

    parser = argparse.ArgumentParser(description="MIDI Event Handler Launcher")
    parser.add_argument("--app", action="store_true", help="Run app directly (no monitoring)")
    args = parser.parse_args()

    if args.app:
        host = app_conf.get('host', '127.0.0.1')
        port = app_conf.get('port', 8000)
        run_app(host=host, port=port)
    else:
        # Monitoring loop (default in compiled mode)
        monitor_loop()


if __name__ == "__main__":
    main()
