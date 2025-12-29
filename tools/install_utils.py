import sys
import subprocess
import shlex
from typing import List, Tuple, Optional


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a subprocess command safely and return (code, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def pip_available() -> bool:
    code, out, err = _run([sys.executable, "-m", "pip", "--version"])
    return code == 0


def get_pip_version() -> Optional[str]:
    code, out, err = _run([sys.executable, "-m", "pip", "--version"])
    if code == 0:
        return out
    return None


def prompt_yes_no(message: str, default: bool = False) -> bool:
    """Prompt the user for yes/no in interactive shells.
    If stdin is not a tty, return default.
    """
    try:
        if not sys.stdin.isatty():
            return default
        choice = input(f"{message} [y/N]: ").strip().lower()
        return choice in ("y", "yes")
    except Exception:
        return default


def ensure_packages(packages: List[str], auto_confirm: bool = False) -> Tuple[List[str], List[str]]:
    """Ensure Python packages are importable. If missing, offer to install via pip.

    Returns (installed, failed) lists.
    """
    installed: List[str] = []
    failed: List[str] = []
    missing: List[str] = []

    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            installed.append(pkg)
        except Exception:
            missing.append(pkg)

    if not missing:
        return installed, failed

    # Ask once for confirmation
    do_install = auto_confirm or prompt_yes_no(
        f"Install missing packages via pip: {', '.join(missing)}?", default=False
    )

    if not do_install:
        return installed, missing  # treat missing as failed for reporting

    for pkg in missing:
        code, out, err = _run([sys.executable, "-m", "pip", "install", pkg])
        if code == 0:
            try:
                __import__(pkg.replace('-', '_'))
                installed.append(pkg)
            except Exception:
                failed.append(pkg)
        else:
            failed.append(pkg)

    return installed, failed
