"""Profile management: add / rename / delete / persist."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from . import config


@dataclass
class Profile:
    """An isolated Edge profile (with its own user-data-dir)."""

    id: str
    name: str
    folder: str                 # user-data-dir folder name (relative to PROFILES_DIR)
    note: str = ""

    @property
    def user_data_dir(self) -> Path:
        return config.PROFILES_DIR / self.folder


def _slugify(name: str) -> str:
    """Convert a name into a safe folder name."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    return slug or "profile"


class ProfileManager:
    """Read/write the profile list to profiles.json."""

    def __init__(self) -> None:
        config.ensure_dirs()
        self._profiles: list[Profile] = []
        self.load()

    # ----- read/write -----
    def load(self) -> None:
        self._profiles = []
        if not config.PROFILES_FILE.is_file():
            return
        try:
            with config.PROFILES_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, list):
            return
        for item in data:
            try:
                self._profiles.append(
                    Profile(
                        id=str(item["id"]),
                        name=str(item["name"]),
                        folder=str(item["folder"]),
                        note=str(item.get("note", "")),
                    )
                )
            except (KeyError, TypeError):
                continue

    def save(self) -> None:
        config.ensure_dirs()
        data = [asdict(p) for p in self._profiles]
        with config.PROFILES_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ----- queries -----
    @property
    def profiles(self) -> list[Profile]:
        return list(self._profiles)

    def get(self, profile_id: str) -> Profile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def default_name(self) -> str:
        """Generate a default unique name like 'Profile 1', 'Profile 2'..."""
        existing = {p.name for p in self._profiles}
        i = 1
        while f"Profile {i}" in existing:
            i += 1
        return f"Profile {i}"

    def _unique_folder(self, base: str) -> str:
        existing = {p.folder for p in self._profiles}
        folder = base
        i = 1
        while folder in existing or (config.PROFILES_DIR / folder).exists():
            i += 1
            folder = f"{base}_{i}"
        return folder

    # ----- operations -----
    def add(self, name: str, note: str = "") -> Profile:
        name = name.strip()
        if not name:
            raise ValueError("Profile name must not be empty.")
        folder = self._unique_folder(_slugify(name))
        profile = Profile(id=uuid.uuid4().hex[:12], name=name, folder=folder, note=note)
        profile.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._profiles.append(profile)
        self.save()
        return profile

    def rename(self, profile_id: str, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Profile name must not be empty.")
        profile = self.get(profile_id)
        if profile is None:
            raise KeyError(profile_id)
        profile.name = new_name
        self.save()

    def delete(self, profile_id: str, remove_data: bool = True) -> None:
        profile = self.get(profile_id)
        if profile is None:
            return
        if remove_data and profile.user_data_dir.exists():
            shutil.rmtree(profile.user_data_dir, ignore_errors=True)
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self.save()
