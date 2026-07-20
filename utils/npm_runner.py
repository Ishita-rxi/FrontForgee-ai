"""
Shells out to the real npm on a per-session project directory.

Unlike a one-shot temp folder, a session's workdir is kept around for the
life of the session: `npm install` only has to run once (it's the slow
step, since node_modules can be large), and every later style swap only
needs a fast `npm run build` against files that already have their
dependencies installed. That's what makes "swap a color, see the real
rebuilt app a few seconds later" workable.
"""

import shutil
import subprocess
from pathlib import Path


def npm_available() -> bool:
    return shutil.which("npm") is not None


def node_version() -> str:
    if not shutil.which("node"):
        return ""
    try:
        out = subprocess.run("node --version", shell=True, capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def _run(cmd: str, cwd: Path, timeout: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        log = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, log
    except subprocess.TimeoutExpired as exc:
        return False, f"Command timed out after {timeout}s.\n{exc.stdout or ''}{exc.stderr or ''}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Failed to run command: {exc}"


def write_project_files(workdir: Path, files: dict):
    """Write/overwrite the project's source files. Does not touch
    node_modules, so this is safe to call again after a style swap."""
    for rel_path, content in files.items():
        full_path = workdir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")


def npm_install(workdir: Path, timeout: int = 240) -> tuple[bool, str]:
    return _run("npm install", workdir, timeout)


def npm_build(workdir: Path, timeout: int = 120) -> tuple[bool, str]:
    return _run("npm run build", workdir, timeout)


def dist_dir_for(workdir: Path) -> Path:
    return workdir / "dist"


def collect_dist_files(dist_dir: Path) -> dict:
    files = {}
    for path in dist_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(dist_dir).as_posix()
            files[rel] = path.read_bytes()
    return files
