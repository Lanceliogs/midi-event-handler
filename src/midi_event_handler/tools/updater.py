# updater.py
import requests
import re
from pathlib import Path
from packaging import version

from midi_event_handler.core.config import get_updates_config

GITHUB_OWNER = "Lanceliogs"
GITHUB_REPO = "midi-event-handler"
API_URL_ALL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
FILENAME_PATTERN = re.compile(r"midi-event-handler-setup_.*\.exe")

def format_release_notes(tag: str, notes: str) -> str:
    return f"## **Version**: {tag}\n---\n{notes.strip()}"

def get_latest_release_asset(current_version: str = "v0.0.0"):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    include_prereleases = get_updates_config().get("prereleases", False)

    response = requests.get(API_URL_ALL, headers=headers)
    response.raise_for_status()
    releases = response.json()

    for release in releases:
        if not include_prereleases and release.get("prerelease", False):
            continue

        tag = release.get("tag_name", "").strip()
        if not tag:
            continue

        notes = release.get("body", "")

        # Compare versions
        if version.parse(tag) <= version.parse(current_version):
            continue  # Skip older or equal versions

        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if FILENAME_PATTERN.fullmatch(name):
                return asset["browser_download_url"], name, tag, notes

    # No newer version found
    return None


def download_with_progress_tray(url, output_path, update_progress):
    headers = {"Accept": "application/octet-stream"}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percent = int((downloaded / total) * 100)
                        update_progress(percent)
