import subprocess
import shutil
from pathlib import Path
import sys

OUTPUT_DIR = Path("build")
APP_ENTRY = "src/midi_event_handler/entrypoint.py"
LAUNCHER_ENTRY = "src/midi_event_handler/launcher.py"
LOGGING_CONFIG = "logging_configs/config.yaml"


def run():
    print("🔄 Cleaning old build directory...")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    print(f"\n🔨 Building main app ({APP_ENTRY})...")
    result = subprocess.run([
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--follow-imports",
        f"--include-data-files={LOGGING_CONFIG}={LOGGING_CONFIG}",
        f"--output-dir={OUTPUT_DIR}",
        APP_ENTRY,
    ], check=True)
    if result.returncode != 0:
        print("❌ App build failed!")
        sys.exit(1)

    print(f"\n🔨 Building launcher ({LAUNCHER_ENTRY})...")
    result = subprocess.run([
        sys.executable, "-m", "nuitka",
        "--standalone",
        f"--output-dir={OUTPUT_DIR}",
        f"--nofollow-import-to=midi_event_handler",
        LAUNCHER_ENTRY,
    ], check=True)
    if result.returncode != 0:
        print("❌ Launcher build failed!")
        sys.exit(1)

    print(f"\n✅ Build complete! Output in: {OUTPUT_DIR}")

    # Rename app binary
    original_app_exe = OUTPUT_DIR / "entrypoint.dist" / "entrypoint.exe"
    renamed_app_exe = OUTPUT_DIR / "entrypoint.dist" / "app.exe"

    if original_app_exe.exists():
        original_app_exe.rename(renamed_app_exe)
        print(f"✅ Renamed: {original_app_exe.name} ➜ {renamed_app_exe.name}")
    else:
        print(f"⚠️ Expected file not found: {original_app_exe}")
