"""Shared configuration & paths for the application."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running from a PyInstaller-packaged .exe."""
    return getattr(sys, "frozen", False)


def get_base_dir() -> Path:
    """Base data directory (portable: next to the exe / project root)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


# Directory holding all app data (profiles + settings)
DATA_DIR = get_base_dir() / "EdgeProfiles"
PROFILES_DIR = DATA_DIR / "profiles"          # one user-data-dir per profile
PROFILES_FILE = DATA_DIR / "profiles.json"     # profile list metadata
SETTINGS_FILE = DATA_DIR / "settings.json"     # shared settings

# Common Edge install locations on Windows
_EDGE_CANDIDATES = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path(os.environ.get("LocalAppData", ""))
    / "Microsoft" / "Edge" / "Application" / "msedge.exe",
]

DEFAULT_SETTINGS = {
    "edge_path": "",          # empty = auto-detect
    "start_url": "",          # URL opened on launch (empty = default page)
    "launch_delay_ms": 600,   # delay between launches to avoid congestion
}


def detect_edge_path() -> str:
    """Auto-detect the msedge.exe path. Returns '' if not found."""
    for candidate in _EDGE_CANDIDATES:
        if candidate and candidate.is_file():
            return str(candidate)
    return ""


def ensure_dirs() -> None:
    """Create the data directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def open_in_explorer(path: Path) -> None:
    """Open a directory in the system file manager (Windows: Explorer)."""
    ensure_dirs()
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path))  # noqa: S606 - Windows-only, path is app-controlled


def load_settings() -> dict:
    """Read settings.json, filling in any missing default values."""
    ensure_dirs()
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.is_file():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                settings.update({k: data[k] for k in data if k in DEFAULT_SETTINGS})
        except (json.JSONDecodeError, OSError):
            pass
    if not settings.get("edge_path"):
        settings["edge_path"] = detect_edge_path()
    return settings


def save_settings(settings: dict) -> None:
    """Save settings.json."""
    ensure_dirs()
    clean = {k: settings.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS}
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
