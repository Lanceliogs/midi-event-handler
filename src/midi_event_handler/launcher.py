import subprocess
import time
from pathlib import Path
import yaml
import webbrowser
import argparse

from midi_event_handler.main import run_app
from midi_event_handler.debug import list_ports, listen_ports
from midi_event_handler.tools.logtools import setup_logger
from midi_event_handler.tools.tray import setup_tray_icon
from midi_event_handler.core.config import (
    default_app_conf,
    WHATSNEW_PATH,
    is_embedded,
)
from midi_event_handler.web.shutdown import request_shutdown

import logging

log = logging.getLogger(__name__)


# === Runtime Paths ===
RUNTIME_DIR = Path(".runtime")
RESTART_FLAG = RUNTIME_DIR / "restart.flag"
ICON_PATH = Path("meh-icon.ico")

# === Config Load ===
with open("config.yaml", "r") as f:
    conf = yaml.safe_load(f)

app_conf: dict = conf.get("app", default_app_conf())


# === App Launch ===
def launch_app(console_mode=False):
    command = ["meh.exe", "--app"] if is_embedded() else ["poetry", "run", "start-app"]

    if console_mode:
        command.append("--console")

    log.info(f"Launching app: {' '.join(command)}")

    # Hide console window on Windows unless console mode
    kwargs = {}
    if is_embedded() and not console_mode:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    return subprocess.Popen(command, **kwargs)


def wait_for_exit_or_restart(proc):
    """Wait for process to exit or restart flag. Returns 'restart' or 'exit'."""
    while True:
        if RESTART_FLAG.exists():
            log.warning("🔁 Restart flag detected")
            return "restart"

        # Check if process exited
        ret = proc.poll()
        if ret is not None:
            log.info(f"🛑 Process exited with code {ret}")
            return "exit"

        time.sleep(0.5)


def monitor_loop(console_mode=False):
    port = app_conf.get("port", 8000)

    dashboard_url = f"http://127.0.0.1:{port}/meh/ui/dashboard"
    whatsnew_url = f"http://127.0.0.1:{port}/meh/ui/whatsnew"

    setup_tray_icon(dashboard_url)
    webbrowser.open(whatsnew_url if WHATSNEW_PATH.exists() else dashboard_url)

    RUNTIME_DIR.mkdir(exist_ok=True)

    while True:
        proc = launch_app(console_mode=console_mode)
        action = wait_for_exit_or_restart(proc)

        if action == "restart":
            request_shutdown(port)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                log.warning("TimeoutError detected. Killing the child instead.")
                proc.kill()
            finally:
                RESTART_FLAG.unlink(missing_ok=True)
            # Loop continues, app will restart
        else:
            # Process exited (from tray quit or crash)
            break


def main():
    setup_logger()

    parser = argparse.ArgumentParser(
        description="MIDI Event Handler Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Default app mode (no subcommand or --app for backwards compat)
    parser.add_argument("--app", action="store_true", help="Run app directly (no monitoring)")
    parser.add_argument("--console", action="store_true", help="Keep console attached for logging")

    # Debug subcommand
    debug_parser = subparsers.add_parser("debug", help="MIDI debug tools")
    debug_subparsers = debug_parser.add_subparsers(dest="debug_command", required=True)

    # debug list
    debug_subparsers.add_parser("list", help="List all available MIDI ports")

    # debug listen
    listen_parser = debug_subparsers.add_parser("listen", help="Listen to MIDI input ports")
    listen_parser.add_argument("ports", nargs="+", help="Port names (or partial matches) to listen on")

    args = parser.parse_args()

    if args.command == "debug":
        if args.debug_command == "list":
            list_ports()
        elif args.debug_command == "listen":
            listen_ports(args.ports)
    elif args.app:
        host = app_conf.get("host", "127.0.0.1")
        port = app_conf.get("port", 8000)
        run_app(host=host, port=port)
    else:
        # Monitoring loop (default in compiled mode)
        monitor_loop(console_mode=args.console)


if __name__ == "__main__":
    main()
