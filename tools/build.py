import subprocess
import shutil
from pathlib import Path
import sys

import htmlmin
import csscompressor
import rjsmin

# --- Configuration ----------------------------------
OUTPUT_DIR = Path("build")

APP_ENTRY = "src/midi_event_handler/entrypoint.py"
LAUNCHER_ENTRY = "src/midi_event_handler/launcher.py"

SRC_CONFIG = "config.yaml"
BUILD_CONFIG = "config.yaml"

SRC_STATIC_DIR = "src/midi_event_handler/web/static"
BUILD_STATIC_DIR = "static"
SRC_TEMPLATES_DIR = "src/midi_event_handler/web/templates"
BUILD_TEMPLATES_DIR = "templates"

FINAL_APP_DIR_NAME = "Release"

# --- NUITKA -------------------------------------------------------------------- 

def minify_static_files(output_dir: Path):
    print(f"\n🔄 Minifying web files recursively in: {output_dir}")

    # Minify HTML
    for html_file in output_dir.rglob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
            minified = htmlmin.minify(content, remove_comments=True, remove_empty_space=True)
            html_file.write_text(minified, encoding="utf-8")
            print(f"🧼 Minified HTML: {html_file}")
        except Exception as e:
            print(f"❌ Failed to minify HTML {html_file}: {e}")

    # Minify CSS
    for css_file in output_dir.rglob("*.css"):
        try:
            content = css_file.read_text(encoding="utf-8")
            minified = csscompressor.compress(content)
            css_file.write_text(minified, encoding="utf-8")
            print(f"🧼 Minified CSS: {css_file}")
        except Exception as e:
            print(f"❌ Failed to minify CSS {css_file}: {e}")

    # Minify JavaScript
    for js_file in output_dir.rglob("*.js"):
        try:
            content = js_file.read_text(encoding="utf-8")
            minified = rjsmin.jsmin(content)
            js_file.write_text(minified, encoding="utf-8")
            print(f"🧼 Minified JS: {js_file}")
        except Exception as e:
            print(f"❌ Failed to minify JS {js_file}: {e}")

    print(f"\n✅ Minify complete of {output_dir}")

def run():
    print("🔄 Cleaning old build directory...")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    print(f"\n🔨 Building main app ({APP_ENTRY})...")
    result = subprocess.run([
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--follow-imports",
        f"--include-data-files={SRC_CONFIG}={BUILD_CONFIG}",
        f"--include-data-dir={SRC_STATIC_DIR}={BUILD_STATIC_DIR}",
        f"--include-data-dir={SRC_TEMPLATES_DIR}={BUILD_TEMPLATES_DIR}",
        "--windows-icon-from-ico=meh-icon.ico",
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
        "--windows-icon-from-ico=meh-icon.ico",
        LAUNCHER_ENTRY,
    ], check=True)
    if result.returncode != 0:
        print("❌ Launcher build failed!")
        sys.exit(1)

    print(f"\n✅ Build complete! Output in: {OUTPUT_DIR}\n")

    # Rename app binary
    orig_app = OUTPUT_DIR / "entrypoint.dist" / "entrypoint.exe"
    renamed_app = OUTPUT_DIR / "entrypoint.dist" / "app.exe"

    if orig_app.exists():
        orig_app.rename(renamed_app)
        print(f"✅ App renamed: {orig_app.name} ➜ {renamed_app.name}")
    else:
        print(f"⚠️ Expected file not found: {orig_app}")

    # Moving launcher.exe to app.dist 
    orig_launcher = OUTPUT_DIR / "launcher.dist" / "launcher.exe"
    moved_launcher = OUTPUT_DIR / "entrypoint.dist" / "launcher.exe"
    
    if orig_launcher.exists():
        orig_launcher.rename(moved_launcher)
        print(f"✅ Launcher moved: {orig_launcher.name} ➜ {moved_launcher.name}")
    else:
        print(f"⚠️ Expected file not found: {orig_launcher}")

    minify_static_files(OUTPUT_DIR / "entrypoint.dist")

    # Renaming the whole app dir

    shutil.move(OUTPUT_DIR / "entrypoint.dist", OUTPUT_DIR / FINAL_APP_DIR_NAME)
    print(f"\n✅ Application directory renamed as {FINAL_APP_DIR_NAME}\n")


# --- INNO SETUP -------------------------------------------------------

INNOSETUP_CONF = Path(".innosetup.conf")

def get_iscc_path():
    # Try cached path
    if INNOSETUP_CONF.exists():
        saved = INNOSETUP_CONF.read_text(encoding="utf-8").strip()
        if Path(saved).exists():
            return saved

    # Prompt user
    print("❌ Inno Setup compiler (ISCC.exe) not found.")
    user_input = input("🔍 Please enter the full path to ISCC.exe: ").strip()
    if not Path(user_input).exists():
        print("❌ Invalid path. Exiting.")
        sys.exit(1)

    # Save for next time
    INNOSETUP_CONF.write_text(user_input, encoding="utf-8")
    return user_input


def build_inno_installer():
    # Adjust this to your actual .iss file location
    ISS_FILE = Path("installer.iss")
    iscc_path = get_iscc_path()

    print(f"[._.] Running Inno Setup Compiler:\n    {iscc_path}\n")
    result = subprocess.run([iscc_path, str(ISS_FILE)], check=False)

    if result.returncode == 0:
        print("[*o*] Installer created successfully.")
    else:
        print("❌ Inno Setup failed.")
