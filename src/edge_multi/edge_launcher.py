"""Launch / close Microsoft Edge for each profile (each profile is isolated)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .profile_manager import Profile

# Hide the PowerShell console window used by the close helpers.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class EdgeLauncherError(Exception):
    """Raised when Edge cannot be launched."""


def _build_args(edge_path: str, profile: Profile, start_urls: list[str] | None = None) -> list[str]:
    """Build the command-line arguments for one profile.

    A dedicated --user-data-dir per profile keeps cookies/logins fully isolated.
    Each URL in start_urls is opened in its own tab.
    """
    args: list[str] = [
        edge_path,
        f"--user-data-dir={profile.user_data_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    for url in start_urls or []:
        url = url.strip()
        if url:
            args.append(url)
    return args


def launch_profile(
    edge_path: str, profile: Profile, start_urls: list[str] | None = None
) -> subprocess.Popen:
    """Open Edge for a single profile. Returns the process object."""
    if not edge_path or not Path(edge_path).is_file():
        raise EdgeLauncherError(
            "msedge.exe not found. Please check the Edge path in Settings."
        )
    profile.user_data_dir.mkdir(parents=True, exist_ok=True)
    args = _build_args(edge_path, profile, start_urls)
    try:
        # Avoid shell=True to prevent injection; pass the argument list directly.
        return subprocess.Popen(args, close_fds=True)
    except OSError as exc:
        raise EdgeLauncherError(f"Cannot launch Edge: {exc}") from exc


def launch_profiles(
    edge_path: str,
    profiles: list[Profile],
    start_urls: list[str] | None = None,
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
            launch_profile(edge_path, profile, start_urls)
        except EdgeLauncherError as exc:
            error = str(exc)
        results.append((profile, error))
        if on_progress is not None:
            on_progress(profile, error)
        if delay_s and index < len(profiles) - 1:
            time.sleep(delay_s)
    return results


def _kill_msedge_by_data_dir(data_dir: str, prefix_match: bool) -> None:
    """Terminate msedge.exe processes whose command line uses the given data dir.

    prefix_match=False  -> only the exact profile (data_dir followed by a space).
    prefix_match=True   -> every profile located under data_dir (used for clear-all).
    Windows-only; relies on PowerShell + CIM, fails silently if unavailable.
    """
    safe_dir = data_dir.replace("'", "''")
    like = f"*--user-data-dir={safe_dir}*" if prefix_match else f"*--user-data-dir={safe_dir} *"
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$dir='{safe_dir}';"
        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" |"
        " Where-Object { $_.CommandLine -and "
        f"($_.CommandLine -replace '\"','') -like '{like}'" "}"
        " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            creationflags=_NO_WINDOW,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def close_profile(profile: Profile, wait_s: float = 1.2) -> None:
    """Close every Edge window/process opened for this profile, then wait briefly
    so Windows releases file locks before the data folder can be removed."""
    _kill_msedge_by_data_dir(str(profile.user_data_dir), prefix_match=False)
    if wait_s > 0:
        time.sleep(wait_s)


def close_all_in_dir(profiles_dir: Path, wait_s: float = 1.2) -> None:
    """Close all Edge sessions whose data dirs live under profiles_dir."""
    _kill_msedge_by_data_dir(str(profiles_dir), prefix_match=True)
    if wait_s > 0:
        time.sleep(wait_s)
