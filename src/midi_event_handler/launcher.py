import subprocess
import time
import sys
from pathlib import Path
import yaml
import webbrowser
import builtins

is_compiled = '__compiled__' in globals()

RUNTIME_DIR = Path(".runtime")
RESTART_FLAG = RUNTIME_DIR / "restart.flag"

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

def watch_for_restart():
    while True:
        if RESTART_FLAG.exists():
            print("Restart flag detected.")
            return True
        time.sleep(0.5)

def main():
    webbrowser.open(f"http://127.0.0.1:{app_conf.get('port', 8000)}/dashboard")
    
    RUNTIME_DIR.mkdir(exist_ok=True)
    while True:
        proc = launch_app()
        if watch_for_restart():
            proc.terminate()
            print(f"App returned {proc.wait()}")
            RESTART_FLAG.unlink(missing_ok=True)
        else:
            break

if __name__ == "__main__":
    main()
