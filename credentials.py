"""Read the local Claude OAuth credentials and refresh the access token.

Cross-platform credential storage:
  * Windows / Linux : ~/.claude/.credentials.json  (a JSON file)
  * macOS           : the login Keychain (read via the `security` CLI)

The tracker never stores or transmits your token anywhere except to
api.anthropic.com / platform.claude.com (the same hosts Claude Code uses).
"""
from __future__ import annotations

import getpass
import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests

IS_MAC = platform.system() == "Darwin"

# Claude Code's public OAuth client id (used only to refresh the token).
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
REFRESH_URL = "https://platform.claude.com/v1/oauth/token"

CREDENTIALS_PATH = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"

# macOS Keychain generic-password service names to try, most likely first.
KEYCHAIN_SERVICES = ("Claude Code-credentials", "Claude Code", "claude-code")

# Refresh a bit before the token actually expires.
EXPIRY_SKEW_MS = 5 * 60 * 1000

# Windows-only flag so the `claude --version` probe never flashes a console.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class CredentialsError(Exception):
    """Raised when credentials are missing or unusable (i.e. not signed in)."""


@dataclass
class Credentials:
    access_token: str
    refresh_token: str | None
    expires_at_ms: int | None

    @property
    def is_expired(self) -> bool:
        if not self.expires_at_ms:
            return False
        return (time.time() * 1000) >= (self.expires_at_ms - EXPIRY_SKEW_MS)


def _detect_claude_version() -> str:
    """User-Agent must look like `claude-code/<version>` or the endpoint
    throttles hard. Detect the installed CLI, fall back to a recent version."""
    try:
        out = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW,
        ).stdout.strip()
        token = out.split()[0]  # e.g. "2.1.148 (Claude Code)"
        if token and token[0].isdigit():
            return token
    except Exception:
        pass
    return "2.1.148"


CLAUDE_VERSION = _detect_claude_version()
USER_AGENT = f"claude-code/{CLAUDE_VERSION}"


# --- raw credential blob I/O (platform-specific) ------------------------
def _credentials_path(config_dir: Path | None = None) -> Path:
    return (config_dir / ".credentials.json") if config_dir else CREDENTIALS_PATH


def _keychain_read(config_dir: Path | None = None) -> str:
    """Return the raw JSON blob Claude Code stores in the macOS login Keychain.

    Claude Code writes the item under service "Claude Code-credentials" with the
    account set to the current user. We try that first (account-qualified, then
    without), then the other known service names, and finally the file — which
    is what Claude Code itself falls back to when the Keychain can't be reached
    (e.g. over SSH, where `security` returns errSecInteractionNotAllowed).
    """
    user = getpass.getuser()
    for service in KEYCHAIN_SERVICES:
        for cmd in (
            ["security", "find-generic-password", "-s", service, "-a", user, "-w"],
            ["security", "find-generic-password", "-s", service, "-w"],
        ):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            except FileNotFoundError as e:
                raise CredentialsError("`security` CLI not found (macOS only).") from e
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()

    credentials_path = _credentials_path(config_dir)
    if credentials_path.exists():  # rare on macOS, but Claude Code's own fallback
        return credentials_path.read_text(encoding="utf-8")
    raise CredentialsError(
        "No Claude credentials found in the macOS Keychain. "
        "Sign in with `claude` first (and grant Keychain access if prompted)."
    )


def _read_raw(config_dir: Path | None = None) -> str:
    if IS_MAC:
        return _keychain_read(config_dir)
    credentials_path = _credentials_path(config_dir)
    if not credentials_path.exists():
        raise CredentialsError(
            f"Not signed in: {credentials_path} not found. "
            "Run `claude` and sign in first."
        )
    try:
        return credentials_path.read_text(encoding="utf-8")
    except OSError as e:
        raise CredentialsError(f"Could not read credentials: {e}") from e


def load(config_dir: Path | None = None) -> Credentials:
    """Load credentials. Raises CredentialsError if not signed in."""
    raw = _read_raw(config_dir)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CredentialsError(f"Credentials are not valid JSON: {e}") from e

    oauth = data.get("claudeAiOauth") or {}
    token = oauth.get("accessToken")
    if not token:
        raise CredentialsError(
            "No OAuth access token found — sign in with Claude Code "
            "(subscription login, not an API key)."
        )
    return Credentials(
        access_token=token,
        refresh_token=oauth.get("refreshToken"),
        expires_at_ms=oauth.get("expiresAt"),
    )


def _persist(access_token: str, refresh_token: str, expires_at_ms: int,
             config_dir: Path | None = None) -> None:
    """Persist refreshed tokens where the platform keeps them.

    On macOS we deliberately do NOT write back to the Keychain — Claude Code
    owns that item and rewriting it risks corrupting it. The refreshed token is
    used in-memory for this run instead; Claude Code refreshes it on its own.
    """
    if IS_MAC:
        return
    try:
        data = json.loads(_credentials_path(config_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    oauth = data.setdefault("claudeAiOauth", {})
    oauth["accessToken"] = access_token
    oauth["refreshToken"] = refresh_token
    oauth["expiresAt"] = expires_at_ms
    _credentials_path(config_dir).write_text(json.dumps(data, indent=2), encoding="utf-8")


def refresh(creds: Credentials, config_dir: Path | None = None) -> Credentials:
    """Exchange the refresh token for a new access token and persist it."""
    if not creds.refresh_token:
        raise CredentialsError("Access token expired and no refresh token available.")

    resp = requests.post(
        REFRESH_URL,
        json={
            "grant_type": "refresh_token",
            "refresh_token": creds.refresh_token,
            "client_id": CLIENT_ID,
        },
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        timeout=20,
    )
    if resp.status_code != 200:
        raise CredentialsError(
            f"Token refresh failed ({resp.status_code}). "
            "You may need to sign in again with `claude`."
        )
    payload = resp.json()
    new_access = payload["access_token"]
    new_refresh = payload.get("refresh_token", creds.refresh_token)
    expires_at_ms = int(time.time() * 1000) + int(payload.get("expires_in", 43200)) * 1000
    _persist(new_access, new_refresh, expires_at_ms, config_dir)
    return Credentials(new_access, new_refresh, expires_at_ms)


def get_valid(config_dir: Path | None = None) -> Credentials:
    """Load credentials, refreshing if expired. Raises CredentialsError if unusable."""
    creds = load(config_dir)
    if creds.is_expired:
        creds = refresh(creds, config_dir)
    return creds
