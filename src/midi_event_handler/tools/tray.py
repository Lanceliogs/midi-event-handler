import webbrowser
import threading
from pathlib import Path
from pystray import Icon, MenuItem as Item, Menu
from PIL import Image

ICON_PATH = Path("meh-icon.ico")

def on_exit(icon, item):
    icon.stop()

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
