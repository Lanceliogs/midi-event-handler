import threading
import subprocess
import sys
import webbrowser
from pathlib import Path
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image

from midi_event_handler.core.config import (
    WHATSNEW_PATH,
    WHATSNEW_SEEN_PATH,
    get_current_version,
    safe_runtime_path,
    get_app_config,
)

from midi_event_handler.tools.updater import (
    get_latest_release_asset,
    download_with_progress_tray,
    format_release_notes,
)

from midi_event_handler.web.shutdown import request_shutdown

ICON_PATH = Path("meh-icon.ico")

tray_state = {"status_text": "Idle", "check_enabled": True}

tray_icon = None  # Global for access in callbacks


# --- Menu Builder ---


def build_menu(icon):
    return Menu(
        Item("Open Dashboard", lambda icon, item: webbrowser.open(icon.url)),
        Item(lambda item: f"Status: {tray_state['status_text']}", None, enabled=False),
        Item(
            "Check for Updates",
            lambda icon, item: run_update_check_threaded(icon),
            enabled=tray_state["check_enabled"],
        ),
        Item("Quit", on_exit),
    )


# --- Status and Menu Updates ---


def set_status(text):
    tray_state["status_text"] = text
    tray_icon.update_menu()


def disable_menu_item():
    tray_state["check_enabled"] = False
    tray_icon.update_menu()


def enable_menu_item():
    tray_state["check_enabled"] = True
    tray_icon.update_menu()


# --- Updater Integration ---


def launch_installer_detached(installer_path):
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen([str(installer_path)], **kwargs)


def run_update_check_threaded(icon):
    def update_progress(p):
        set_status(f"Downloading... {p}%")

    def task():
        try:
            disable_menu_item()
            set_status("Checking...")

            current_version = get_current_version(with_commit=False)
            result = get_latest_release_asset(current_version=current_version)
            if result is None:
                set_status("Up-to-date ✅")
                icon.notify(f"No new version (current: {current_version})", "Updater")
                return

            url, filename, latest_tag, notes = result

            # Download the new version
            download_path = safe_runtime_path() / filename
            set_status(f"Downloading {filename}")
            icon.notify(f"Downloading {filename}...", "Updater")
            download_with_progress_tray(url, download_path, update_progress)

            # Write version notes and clear seen marker
            WHATSNEW_PATH.write_text(format_release_notes(latest_tag, notes))
            WHATSNEW_SEEN_PATH.unlink(missing_ok=True)

            # Detach and run installer
            launch_installer_detached(download_path)

            # Exit current app
            set_status("Exiting...")
            icon.notify("App will close now for update", "Updater")
            port = get_app_config().get("port", 8000)
            request_shutdown(port)
            tray_icon.stop()

        except Exception as e:
            set_status("Failed ❌")
            icon.notify(f"Update failed: {e}", "Updater")
        finally:
            enable_menu_item()

    threading.Thread(target=task, daemon=True).start()


# --- Tray Setup ---


def setup_tray_icon(url: str):
    global tray_icon
    image = Image.open(ICON_PATH)

    tray_icon = Icon("midi_event_handler", image, "MIDI Event Handler")
    tray_icon.menu = build_menu(tray_icon)
    tray_icon.url = url  # Pass URL to open dashboard callback

    threading.Thread(target=tray_icon.run, daemon=True).start()


# --- Exit ---


def on_exit(icon, item):
    port = get_app_config().get("port", 8000)
    request_shutdown(port)
    icon.stop()
