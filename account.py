"""Read local Claude account info from ~/.claude.json (no network needed).

Claude Code caches the signed-in account under `oauthAccount`. We surface the
same fields the /usage panel's Account section shows.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(os.path.expanduser("~")) / ".claude.json"

# Friendly names for known organizationType values; unknown values are
# title-cased as a fallback so new plans still read sensibly.
_PLAN_LABELS = {
    "claude_team": "Claude team",
    "claude_enterprise": "Claude enterprise",
    "claude_max": "Claude Max",
    "claude_pro": "Claude Pro",
}


@dataclass
class Account:
    display_name: str | None = None
    email: str | None = None
    organization: str | None = None
    plan: str | None = None
    auth_method: str = "Claude AI"
    extra_usage_enabled: bool = False


def _plan_label(org_type: str | None, seat_tier: str | None) -> str | None:
    if org_type:
        if org_type in _PLAN_LABELS:
            return _PLAN_LABELS[org_type]
        return org_type.replace("claude_", "Claude ").replace("_", " ").title()
    if seat_tier:
        return seat_tier.replace("_", " ").title()
    return None


def load() -> Account:
    """Best-effort account load. Never raises — returns blanks on any problem."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Account()

    oauth = data.get("oauthAccount") or {}
    return Account(
        display_name=oauth.get("displayName"),
        email=oauth.get("emailAddress"),
        organization=oauth.get("organizationName"),
        plan=_plan_label(oauth.get("organizationType"), oauth.get("seatTier")),
        auth_method="Claude AI",
        extra_usage_enabled=bool(oauth.get("hasExtraUsageEnabled")),
    )
