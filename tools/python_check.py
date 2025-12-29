import sys
import platform
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

from .install_utils import pip_available, get_pip_version, ensure_packages


MANDATORY_PACKAGES = [
    "ccxt",
    "pandas",
    "numpy",
    "pandas_ta",
    "matplotlib",
    "mplfinance",
    "opencv-python",
    "scikit-learn",
    "joblib",
    "pyyaml",
    "python-telegram-bot",
    "google-api-python-client",
    "google-auth-oauthlib",
]

OPTIONAL_PACKAGES = [
    "xgboost",
]


@dataclass
class PythonEnvResult:
    component: str
    status: str
    notes: str
    details: Dict


def _venv_active() -> bool:
    return (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def check_python_env(auto_install: bool = False) -> PythonEnvResult:
    py_ver = platform.python_version()
    ok_version = sys.version_info >= (3, 10)
    venv_on = _venv_active()
    pip_ok = pip_available()
    pip_ver = get_pip_version() or "unavailable"

    status = "OK" if (ok_version and pip_ok) else "FAILED"
    notes = []
    if not ok_version:
        notes.append("Python >= 3.10 required")
    if not venv_on:
        notes.append("venv not active (warning)")
    if not pip_ok:
        notes.append("pip not available")

    # Try installing mandatory + optional
    installed, failed = ensure_packages(MANDATORY_PACKAGES + OPTIONAL_PACKAGES, auto_install)

    if failed:
        status = "FAILED"
        notes.append(f"Missing/failed installs: {', '.join(failed)}")
    else:
        if status == "OK":
            status = "OK"
        notes.append(f"Installed/available: {', '.join(installed)}")

    return PythonEnvResult(
        component="Python",
        status=status,
        notes="; ".join(notes),
        details={
            "python_version": py_ver,
            "venv_active": venv_on,
            "pip_version": pip_ver,
            "installed_packages": installed,
            "failed_packages": failed,
        },
    )
