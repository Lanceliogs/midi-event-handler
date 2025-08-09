import subprocess
import shutil
from pathlib import Path
import sys
import os
import time

import htmlmin
import csscompressor
import rjsmin

# --- Configuration ----------------------------------
OUTPUT_DIR = Path("build")

LAUNCHER_ENTRY = "src/midi_event_handler/launcher.py"

SRC_CONFIG = "config.yaml"
BUILD_CONFIG = "config.yaml"

SRC_STATIC_DIR = "src/midi_event_handler/web/static"
BUILD_STATIC_DIR = "static"
SRC_TEMPLATES_DIR = "src/midi_event_handler/web/templates"
BUILD_TEMPLATES_DIR = "templates"

FINAL_APP_DIR_NAME = "Release"

JOBS = 8

ICON_ICO = "meh-icon.ico"

CONSOLE_MODE = "attach"

# --- NUITKA -------------------------------------------------------------------- 

def make_nuitka_build_command(
    script: str | Path, use_lto=True, use_clang=False, jobs=8,
    windows_console_mode=None,
    include_data_dir=[],
    include_data_files=[],
    include_modules=[],
    nofollows=[]
):
    # Base args
    command = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--follow-imports"
    ]

    # Includes args
    for f1, f2 in include_data_files:
        command.append(f"--include-data-files={f1}={f2}")
    for d1, d2 in include_data_dir:
        command.append(f"--include-data-dir={d1}={d2}")
    for m in include_modules:
        command.append(f"--include-module={m}")
    for m in nofollows:
        command.append(f"--nofollow-import-to={m}")

    if windows_console_mode:
        if windows_console_mode not in ("force", "disable", "attach", "hide"):
            raise ValueError("Invalid wnidows console mode")
        command.append(f"--windows-console-mode={windows_console_mode}")

    # Others
    command += [
        f"--windows-icon-from-ico={ICON_ICO}",
        f"--output-dir={OUTPUT_DIR}",
        f"--jobs={jobs}",
        script
    ]

    # Optional enhancements
    if use_lto:
        command.append("--lto=yes")
    if use_clang:
        command.append("--clang")

    return command

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
    total_start = time.perf_counter()
    print("🔄 Cleaning old build directory...")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    print(f"\n🔨 Building app ({LAUNCHER_ENTRY})...")
    command = make_nuitka_build_command(
        LAUNCHER_ENTRY,
        use_lto=True, use_clang=False, jobs=8,
        include_data_files=[
            (SRC_CONFIG, BUILD_CONFIG),
            (ICON_ICO, ICON_ICO)],
        include_data_dir=[
            (SRC_STATIC_DIR, BUILD_STATIC_DIR),
            (SRC_TEMPLATES_DIR, BUILD_TEMPLATES_DIR)
        ],
        windows_console_mode="attach",
        include_modules=["mido.backends.rtmidi"] # PIL for launcher
    )
    result = subprocess.run(command, check=True)
    if result.returncode != 0:
        print("❌ App build failed!")
        sys.exit(1)

    print(f"\n✅ Build complete! Output in: {OUTPUT_DIR}\n")

    minify_static_files(OUTPUT_DIR / "launcher.dist")

    # Renaming the whole app dir
    old_path = OUTPUT_DIR / "launcher.dist"
    release_path = OUTPUT_DIR / FINAL_APP_DIR_NAME
    old_path.rename(release_path)
    print(f"\n✅ Application directory renamed as {FINAL_APP_DIR_NAME}\n")

    version_path = release_path / "version.txt"
    update_version_file(version_path)

    total_time = time.perf_counter() - total_start
    print(f"\n🏁 Build completed in {total_time:.2f}s")


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
    total_start = time.perf_counter()

    ISS_FILE = Path("installer.iss")
    iscc_path = get_iscc_path()

    print(f"[._.] Running Inno Setup Compiler:\n    {iscc_path}\n")
    result = subprocess.run([iscc_path, str(ISS_FILE)], check=False)

    if result.returncode == 0:
        print("[*o*] Installer created successfully.")
    else:
        print("❌ Inno Setup failed.")

    total_time = time.perf_counter() - total_start
    print(f"\n🏁 Build completed in {total_time:.2f}s")

def update_version_file(path: Path = Path("version.txt")):
    result = subprocess.run([
        "poetry", "version", "--short"],
        check=True,
        capture_output=True,
        text=True
    )
    version = result.stdout.strip()
    path.write_text(version)
    if result.returncode == 0:
        print(f"[*o*] Version updated: {version}")
    else:
        print("❌ Could not update version.")
