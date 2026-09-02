"""Discover the local Claude Code profiles the tracker can monitor.

Each ``CLAUDE_CONFIG_DIR`` has its own credentials and cached account details.
The normal profile is ``~/.claude``; additional profiles conventionally use
names such as ``~/.claude-jvorster63``.  ``CLAUDE_USAGE_CONFIG_DIRS`` can be
set to a semicolon-separated list when automatic discovery is not suitable.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    config_dir: Path

    @property
    def key(self) -> str:
        return str(self.config_dir).lower()


_SETTINGS_PATH = Path.home() / ".claude-usage-tracker.json"


def discover() -> list[Profile]:
    """Return usable Claude config directories in a stable, useful order."""
    home = Path.home()
    configured = os.environ.get("CLAUDE_USAGE_CONFIG_DIRS", "").strip()
    if configured:
        candidates = [Path(part.strip()).expanduser()
                      for part in configured.split(";") if part.strip()]
    else:
        default = home / ".claude"
        candidates = [default] + sorted(home.glob(".claude-*"), key=lambda p: p.name.lower())

    profiles: list[Profile] = []
    seen: set[str] = set()
    for index, directory in enumerate(candidates):
        try:
            directory = directory.resolve()
        except OSError:
            continue
        key = str(directory).lower()
        # The default macOS profile keeps credentials in Keychain, not a file.
        # Keep it even without .credentials.json so the existing single-profile
        # Keychain behaviour remains intact.
        is_default = index == 0 and directory.name == ".claude"
        if key in seen or (not is_default and not (directory / ".credentials.json").is_file()):
            continue
        seen.add(key)
        profiles.append(Profile(directory))
    return profiles


def load_active_key() -> str | None:
    """Read the locally persisted active profile, if one was selected."""
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        key = data.get("active_profile")
        return key.lower() if isinstance(key, str) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_active(profile: Profile) -> None:
    """Persist the active profile locally; no account data or tokens are stored."""
    _SETTINGS_PATH.write_text(
        json.dumps({"active_profile": str(profile.config_dir)}, indent=2),
        encoding="utf-8",
    )
