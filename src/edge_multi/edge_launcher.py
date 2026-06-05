"""Launch Microsoft Edge for each profile (each profile is an isolated session)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .profile_manager import Profile


class EdgeLauncherError(Exception):
    """Raised when Edge cannot be launched."""


def _build_args(edge_path: str, profile: Profile, start_url: str = "") -> list[str]:
    """Build the command-line arguments for one profile.

    A dedicated --user-data-dir per profile keeps cookies/logins fully isolated.
    """
    args: list[str] = [
        edge_path,
        f"--user-data-dir={profile.user_data_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    url = start_url.strip()
    if url:
        args.append(url)
    return args


def launch_profile(edge_path: str, profile: Profile, start_url: str = "") -> subprocess.Popen:
    """Open Edge for a single profile. Returns the process object."""
    if not edge_path or not Path(edge_path).is_file():
        raise EdgeLauncherError(
            "msedge.exe not found. Please check the Edge path in Settings."
        )
    profile.user_data_dir.mkdir(parents=True, exist_ok=True)
    args = _build_args(edge_path, profile, start_url)
    try:
        # Avoid shell=True to prevent injection; pass the argument list directly.
        return subprocess.Popen(args, close_fds=True)
    except OSError as exc:
        raise EdgeLauncherError(f"Cannot launch Edge: {exc}") from exc


def launch_profiles(
    edge_path: str,
    profiles: list[Profile],
    start_url: str = "",
    delay_ms: int = 600,
    on_progress=None,
) -> list[tuple[Profile, str | None]]:
    """Open multiple profiles one by one, with a delay between each launch.

    on_progress(profile, error) is called after each profile (error=None on success).
    Returns a list of (profile, error) to summarize the results.
    """
    results: list[tuple[Profile, str | None]] = []
    delay_s = max(0, int(delay_ms)) / 1000.0
    for index, profile in enumerate(profiles):
        error: str | None = None
        try:
            launch_profile(edge_path, profile, start_url)
        except EdgeLauncherError as exc:
            error = str(exc)
        results.append((profile, error))
        if on_progress is not None:
            on_progress(profile, error)
        if delay_s and index < len(profiles) - 1:
            time.sleep(delay_s)
    return results
