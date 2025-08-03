import os
import requests

HTMX_VERSION = "1.9.10"
HTMX_URL = f"https://unpkg.com/htmx.org@{HTMX_VERSION}/dist/htmx.min.js"

CSS_PATH = "src/midi_event_handler/web/static/css"
JS_PATH = "src/midi_event_handler/web/static/js"
HTMX_TARGET = os.path.join(JS_PATH, "htmx.min.js")

def ensure_dirs():
    print("\n[._.] Creating static directories...")
    os.makedirs(CSS_PATH, exist_ok=True)
    os.makedirs(JS_PATH, exist_ok=True)

def download_htmx():
    print(f"\n[._.] Downloading HTMX v{HTMX_VERSION}...")
    response = requests.get(HTMX_URL)
    response.raise_for_status()
    with open(HTMX_TARGET, "wb") as f:
        f.write(response.content)
    print(f"\n[*o*] HTMX downloaded successfully!")
    print(f"      CSS: {CSS_PATH}")
    print(f"      JS : {JS_PATH}")

def setup_web():
    ensure_dirs()
    download_htmx()
