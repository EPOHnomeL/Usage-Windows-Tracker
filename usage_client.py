"""Query the Claude subscription usage endpoint and normalise the response."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

import credentials

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


class UsageError(Exception):
    pass


@dataclass
class Limit:
    kind: str                 # "session" | "weekly_all" | "weekly_scoped"
    percent: float
    resets_at: datetime | None
    label: str                # human-friendly name

    @property
    def resets_in_text(self) -> str:
        if not self.resets_at:
            return ""
        delta = self.resets_at - datetime.now(timezone.utc)
        secs = int(delta.total_seconds())
        if secs <= 0:
            return "resetting now"
        h, rem = divmod(secs, 3600)
        m = rem // 60
        if h >= 24:
            d = h // 24
            return f"resets in {d}d {h % 24}h"
        if h:
            return f"resets in {h}h {m}m"
        return f"resets in {m}m"


@dataclass
class Usage:
    limits: list[Limit] = field(default_factory=list)

    @property
    def session(self) -> Limit | None:
        return next((l for l in self.limits if l.kind == "session"), None)

    @property
    def primary_percent(self) -> float | None:
        """The number shown on the tray icon: the session (5-hour) limit."""
        s = self.session
        return s.percent if s else (self.limits[0].percent if self.limits else None)


_LABELS = {
    "session": "Session (5-hour)",
    "weekly_all": "Weekly (all models)",
    "weekly_scoped": "Weekly",
}


def _parse_reset(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _label_for(item: dict) -> str:
    kind = item.get("kind", "")
    base = _LABELS.get(kind, kind or "Limit")
    scope = item.get("scope") or {}
    model = (scope.get("model") or {}).get("display_name")
    if kind == "weekly_scoped" and model:
        return f"Weekly ({model})"
    return base


def fetch(config_dir: Path | None = None) -> Usage:
    """Fetch current usage. Raises UsageError / CredentialsError on failure."""
    creds = credentials.get_valid(config_dir)
    headers = {
        "Authorization": f"Bearer {creds.access_token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": credentials.USER_AGENT,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.get(USAGE_URL, headers=headers, timeout=20)
    except requests.RequestException as e:
        raise UsageError(f"Network error: {e}") from e

    if resp.status_code == 401:
        # Token may have just gone stale; force a refresh and retry once.
        creds = credentials.refresh(credentials.load(config_dir), config_dir)
        headers["Authorization"] = f"Bearer {creds.access_token}"
        resp = requests.get(USAGE_URL, headers=headers, timeout=20)

    if resp.status_code == 429:
        raise UsageError("Rate limited (429) — will retry on next poll.")
    if resp.status_code != 200:
        raise UsageError(f"Usage request failed ({resp.status_code}).")

    data = resp.json()
    limits: list[Limit] = []

    raw = data.get("limits")
    if isinstance(raw, list):
        for item in raw:
            pct = item.get("percent")
            if pct is None:
                continue
            limits.append(
                Limit(
                    kind=item.get("kind", ""),
                    percent=float(pct),
                    resets_at=_parse_reset(item.get("resets_at")),
                    label=_label_for(item),
                )
            )
    else:
        # Fallback for the older/deprecated flat shape.
        legacy = {
            "five_hour": ("session", "Session (5-hour)"),
            "seven_day": ("weekly_all", "Weekly (all models)"),
            "seven_day_opus": ("weekly_scoped", "Weekly (Opus)"),
            "seven_day_sonnet": ("weekly_scoped", "Weekly (Sonnet)"),
        }
        for key, (kind, label) in legacy.items():
            block = data.get(key)
            if isinstance(block, dict) and block.get("utilization") is not None:
                limits.append(
                    Limit(kind, float(block["utilization"]),
                          _parse_reset(block.get("resets_at")), label)
                )

    if not limits:
        raise UsageError("Usage response had no recognisable limits.")
    return Usage(limits=limits)


if __name__ == "__main__":
    u = fetch()
    for l in u.limits:
        print(f"{l.label:24} {l.percent:5.1f}%  {l.resets_in_text}")
    print("PRIMARY (tray):", u.primary_percent)
