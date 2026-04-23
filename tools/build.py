# build_embedded.py — Builds a self-contained release (embedded Python + wheel)
import argparse
import subprocess
import sys
import time
import shutil
import zipfile
import urllib.request
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("This build script only runs on Windows.")

PY_VERSION = "3.12.10"
PY_EMBED_URL = f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
RELEASE_DIR = BUILD_DIR / "release"
CACHE_DIR = ROOT / ".build-cache"
PYTHON_DIR = RELEASE_DIR / "python"
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

TOOLS_DIR = Path(__file__).resolve().parent

SRC_DIR = ROOT / "src" / "midi_event_handler"

BUNDLE_ITEMS = [
    (ROOT / "config.yaml",       RELEASE_DIR / "config.yaml"),
    (ROOT / "meh-icon.ico",      RELEASE_DIR / "meh-icon.ico"),
    (CACHE_DIR / "meh.exe",      RELEASE_DIR / "meh.exe"),
    (SRC_DIR / "web" / "static",    RELEASE_DIR / "static"),
    (SRC_DIR / "web" / "templates", RELEASE_DIR / "templates"),
]


# --- Helpers ------------------------------------------------------------------

def _read_base_version() -> str:
    import tomllib
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        raise RuntimeError(f"Missing {pyproject}")
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    version = data.get("project", {}).get("version") or data.get("tool", {}).get("poetry", {}).get("version")
    if not version:
        raise RuntimeError("No version found in pyproject.toml")
    return version


def _git(*args) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=str(ROOT), stderr=subprocess.DEVNULL,
    ).decode().strip()


# --- Build steps --------------------------------------------------------------

def _stamp_version() -> str:
    """Write version files for release and installer."""
    base = _read_base_version()
    short = _git("rev-parse", "--short", "HEAD")
    dirty = _git("status", "--porcelain") != ""
    full_version = f"{base}.{short}"
    if dirty:
        full_version += ".dirty"
    
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Full version with git hash for the app
    (RELEASE_DIR / "version.txt").write_text(full_version + "\n", encoding="utf-8")
    
    # Base version for installer naming
    (BUILD_DIR / "installer_version.txt").write_text(base + "\n", encoding="utf-8")
    
    print(f"      version: {full_version}")
    return full_version


def _save_dirty_patch():
    """If the repo has uncommitted changes, save a patch in the release."""
    if _git("status", "--porcelain") == "":
        return
    print("[._.] Repo is dirty — saving patch...")
    patch = _git("diff", "HEAD")
    if patch:
        patch_file = RELEASE_DIR / "dirty.patch"
        patch_file.write_text(patch + "\n", encoding="utf-8")
        print("      + dirty.patch")


def _check_prerequisites():
    config_file = ROOT / "config.yaml"
    if not config_file.exists():
        raise RuntimeError(f"Missing {config_file}")


def _clean_release(clean_python: bool = False):
    """Remove everything in the release dir, optionally including embedded Python."""
    if not RELEASE_DIR.exists():
        return
    if clean_python:
        print("[._.] Cleaning previous release dir (including python/)...")
        shutil.rmtree(RELEASE_DIR)
    else:
        print("[._.] Cleaning previous release dir (keeping python/)...")
        for item in RELEASE_DIR.iterdir():
            if item.name == "python":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def _download(url: str, dest: Path):
    """Download a file if not already cached."""
    if dest.exists():
        print(f"      cached: {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"      downloading: {dest.name} ...")
    urllib.request.urlretrieve(url, dest)


def _setup_embedded_python():
    """Download, extract, and bootstrap pip in the embedded Python."""
    embed_zip = CACHE_DIR / f"python-{PY_VERSION}-embed-amd64.zip"
    get_pip = CACHE_DIR / "get-pip.py"

    print("[._.] Fetching build dependencies...")
    _download(PY_EMBED_URL, embed_zip)
    _download(GET_PIP_URL, get_pip)

    python_exe = PYTHON_DIR / "python.exe"
    if python_exe.exists():
        print(f"[._.] Reusing embedded Python in {PYTHON_DIR}")
        return

    print(f"[._.] Extracting embedded Python {PY_VERSION}...")
    PYTHON_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(embed_zip) as zf:
        zf.extractall(PYTHON_DIR)

    pth_files = list(PYTHON_DIR.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("No ._pth file found in embedded Python")
    pth_file = pth_files[0]
    content = pth_file.read_text(encoding="utf-8")
    content = content.replace("#import site", "import site")
    pth_file.write_text(content, encoding="utf-8")

    print("[._.] Bootstrapping pip...")
    subprocess.run(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        check=True,
    )


def _build_wheel() -> Path:
    """Build a wheel using poetry."""
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        for old in dist_dir.glob("*.whl"):
            old.unlink()
    print("[._.] Building wheel (poetry build)...")
    subprocess.run(["poetry", "build", "-f", "wheel"], cwd=str(ROOT), check=True)
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError("No wheel produced")
    print(f"      {wheels[0].name}")
    return wheels[0]


def _install_deps(wheel: Path, force: bool = False):
    python_exe = PYTHON_DIR / "python.exe"
    if force:
        print("[._.] Force-reinstalling package (keeping deps)...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--no-warn-script-location", "--force-reinstall", "--no-deps", str(wheel)],
            check=True,
        )
        print("[._.] Ensuring dependencies are up to date...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--no-warn-script-location", str(wheel)],
            check=True,
        )
    else:
        print("[._.] Installing wheel into embedded Python...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--no-warn-script-location", str(wheel)],
            check=True,
        )


def _copy_bundle():
    print("[._.] Copying assets...")
    for src, dst in BUNDLE_ITEMS:
        if not src.exists():
            print(f"      SKIP (not found): {src.name}")
            continue
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"      + {src.name}")


def _copy_scripts():
    print("[._.] Copying launcher scripts...")
    if not SCRIPTS_DIR.exists():
        print("      SKIP (no scripts folder)")
        return
    for script in SCRIPTS_DIR.iterdir():
        if script.is_file() and script.suffix == ".bat":
            shutil.copy2(script, RELEASE_DIR / script.name)
            print(f"      + {script.name}")


def _build_cli_exe():
    """Compile meh.c into meh.exe using gcc with icon resource."""
    cli_dir = TOOLS_DIR / "cli"
    meh_c = cli_dir / "meh.c"
    meh_rc = cli_dir / "meh.rc"
    meh_ico = ROOT / "meh-icon.ico"
    meh_res = CACHE_DIR / "meh.res.o"
    meh_exe = CACHE_DIR / "meh.exe"
    
    if not meh_c.exists():
        print("[._.] No meh.c found, skipping CLI exe build")
        return
    
    # Check if rebuild is needed
    sources = [meh_c, meh_rc, meh_ico]
    source_times = [s.stat().st_mtime for s in sources if s.exists()]
    
    if meh_exe.exists() and source_times:
        exe_time = meh_exe.stat().st_mtime
        if exe_time > max(source_times):
            print("[._.] CLI exe is up to date")
            return
    
    print("[._.] Compiling CLI exe (gcc)...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Compile resource file (icon) if it exists
        if meh_rc.exists():
            subprocess.run(
                ["windres", str(meh_rc), "-O", "coff", "-o", str(meh_res)],
                check=True,
                cwd=str(cli_dir)
            )
            # Link with resource (console app)
            subprocess.run(
                ["gcc", "-static", "-O2", "-o", str(meh_exe), str(meh_c), str(meh_res)],
                check=True,
                cwd=str(cli_dir)
            )
            meh_res.unlink(missing_ok=True)
        else:
            # No icon, just compile
            subprocess.run(
                ["gcc", "-static", "-O2", "-o", str(meh_exe), str(meh_c)],
                check=True,
                cwd=str(cli_dir)
            )
        print(f"      + meh.exe")
    except FileNotFoundError:
        print("      SKIP (gcc/windres not found in PATH)")
    except subprocess.CalledProcessError as e:
        print(f"      FAILED: {e}")




# --- Inno Setup installer -----------------------------------------------------

INNOSETUP_CONF = ROOT / ".innosetup.conf"

def _get_iscc_path():
    if INNOSETUP_CONF.exists():
        saved = INNOSETUP_CONF.read_text(encoding="utf-8").strip()
        if Path(saved).exists():
            return saved

    print("[X_X] Inno Setup compiler (ISCC.exe) not found.")
    user_input = input("    Enter the full path to ISCC.exe: ").strip()
    if not Path(user_input).exists():
        raise RuntimeError("Invalid path to ISCC.exe")

    INNOSETUP_CONF.write_text(user_input, encoding="utf-8")
    return user_input


def build_installer():
    """Build the Inno Setup installer for the embedded release."""
    start = time.perf_counter()
    
    iss_file = ROOT / "installer.iss"
    if not iss_file.exists():
        raise RuntimeError(f"Missing {iss_file}")
    
    version_file = BUILD_DIR / "installer_version.txt"
    if not version_file.exists():
        raise RuntimeError(f"Missing {version_file} — run build first")
    
    iscc_path = _get_iscc_path()
    
    print(f"[._.] Running Inno Setup Compiler...")
    result = subprocess.run([iscc_path, str(iss_file)], check=False)
    
    if result.returncode == 0:
        print("[*o*] Installer created successfully.")
    else:
        print("[X_X] Inno Setup failed.")
    
    print(f"Build took {time.perf_counter() - start:.2f}s")


# --- Main entry point ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build a self-contained release archive.")
    parser.add_argument("--clean", action="store_true", help="Remove and recreate the embedded Python from scratch.")
    parser.add_argument("--force", action="store_true", help="Force-reinstall the package without touching dependencies.")
    args = parser.parse_args()

    start = time.perf_counter()
    try:
        _check_prerequisites()
        _clean_release(clean_python=args.clean)
        _setup_embedded_python()
        wheel = _build_wheel()
        _install_deps(wheel, force=args.force)
        _build_cli_exe()
        _copy_bundle()
        _copy_scripts()
        version = _stamp_version()
        _save_dirty_patch()
        print(f"\n[*o*] Release built: {RELEASE_DIR}")
    except Exception as e:
        print(f"\n[X_X] Build failed: {e}")
        raise
    finally:
        print(f"Build took {time.perf_counter() - start:.2f}s")
