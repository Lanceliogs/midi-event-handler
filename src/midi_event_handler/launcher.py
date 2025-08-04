import subprocess
import time
import sys
from pathlib import Path
import yaml
import webbrowser
import builtins

import threading
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image

# --- Parameters ----------------------------------------------------------
is_compiled = '__compiled__' in globals()

RUNTIME_DIR = Path(".runtime")
RESTART_FLAG = RUNTIME_DIR / "restart.flag"
EXIT_FLAG = RUNTIME_DIR / "exit.flag"

ICON_PATH = Path("meh-icon.ico")

def setup_tray_icon(url: str):
    image = Image.open(ICON_PATH)

    icon = Icon(
        "midi_event_handler",
        image,
        "MIDI Event Handler",
        menu=Menu(
            Item("Open Dashboard", lambda icon, item:  webbrowser.open(url)),
            Item("Quit", on_exit)
        )
    )

    # Run the icon in a separate thread so it doesn't block
    threading.Thread(target=icon.run, daemon=True).start()

def on_exit(icon, item):
    icon.stop()
    exit_flag = Path(".runtime") / "exit.flag"
    exit_flag.touch()

# --- App config -------------------------------------------------

conf = {}
with open("config.yaml", "r") as f:
    conf = yaml.safe_load(f)

# I left the non used args as example,
# but they should ne be used in production.
def default_app_conf() -> dict:
    return {
        "host": "127.0.0.1",
        "port": 8000,
        #"reload": False,
        #"local": False,
        #"mapping": None
    }

app_conf: dict = conf.get("app", default_app_conf())

def launch_app():
    
    command = ["app.exe"] if is_compiled else ["poetry", "run", "start-app"]
    
    command += [
            "--host", app_conf.get('host', '127.0.0.1'),
            "--port", str(app_conf.get('port', 8000))
        ]
    
    # Optional args
    if app_conf.get("mapping"):
        command.append("--mapping")
        command.append(app_conf.get("mapping"))
    if app_conf.get("reload"):
        command.append("--reload")

    print(f"Starting app with command:\n  > {' '.join(command)}")
    return subprocess.Popen(command)


def watch_for_flag():
    while True:
        if RESTART_FLAG.exists():
            print("Restart flag detected")
            return "restart"
        if EXIT_FLAG.exists():
            print("Exit flag detected")
            return "exit"
        time.sleep(0.5)


def main():
    url = f"http://127.0.0.1:{app_conf.get('port', 8000)}/dashboard"
    setup_tray_icon(url)

    webbrowser.open(url)
    
    RUNTIME_DIR.mkdir(exist_ok=True)
    while True:
        proc = launch_app()
        flag = watch_for_flag()

        # It's either restart or exit
        proc.terminate()
        print(f"App returned {proc.wait()}")
        if flag == "restart":
            RESTART_FLAG.unlink(missing_ok=True)
        elif flag == "exit":
            EXIT_FLAG.unlink(missing_ok=True)
            break
        else:
            break
    
    # We kill the flags at the end if needed
    RESTART_FLAG.unlink(missing_ok=True)
    EXIT_FLAG.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
