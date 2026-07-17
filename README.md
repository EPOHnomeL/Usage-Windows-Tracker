# Claude Usage Tracker (Windows tray)

A tiny system-tray app that shows your **Claude subscription session usage** as a
live percentage bar next to the Windows clock — the same "Session (5-hour)"
number that Claude Code's `/usage` command and claude.ai show. Hover for the
exact figure and reset time; **double-click for a full Account & Usage window**.

![tray icon examples](_preview/icon_78.png)
![details window](_preview/window.png)

## Details window

Double-click the tray icon (or right-click → **Show details…**) to open an
Account & Usage panel styled like Claude Code's `/usage`:

- **Account** — auth method, email, organization, and plan (read locally from
  `~/.claude.json`, no network call).
- **Usage** — every limit (Session 5-hour, Weekly all-models, Weekly per-model)
  with a coloured progress bar and a reset countdown.
- **Refresh now** button and a "last updated" timestamp. The window updates
  live on each poll while it's open.

> Not (yet) included: the "What's contributing to your limits usage?" breakdown
> from `/usage`. That's analytics Claude Code computes from your local session
> logs using its own heuristics; reproducing it faithfully is a separate piece
> of work. Ask if you'd like an approximate version added.

## How it works

- Reads your existing Claude sign-in token from `%USERPROFILE%\.claude\.credentials.json`
  (the token Claude Code already stores — **no separate login needed**).
- Every 5 minutes it calls Anthropic's usage endpoint
  (`GET https://api.anthropic.com/api/oauth/usage`) and redraws the tray icon.
- Refreshes the access token automatically when it expires.
- The colour shifts green → amber → orange → red as you approach your limit.

Your token is only ever sent to Anthropic's own hosts (`api.anthropic.com` /
`platform.claude.com`) — the same ones Claude Code uses. Nothing is stored or
sent anywhere else.

## ⚠️ Please read: terms-of-service note

As of early 2026, Anthropic restricts these OAuth tokens to the official Claude
Code CLI and claude.ai, and using them from a third-party tool is technically
against the consumer Terms of Service. This app is a personal, **read-only**
monitor of *your own* account and polls infrequently (default every 5 min) to
stay gentle — but be aware:

- The `/api/oauth/usage` endpoint is **undocumented** and could change or break
  without notice.
- There is a real (if small) risk that using tokens outside official clients
  could flag your account.

Use at your own discretion. You can raise `POLL_SECONDS` in `tray_app.py` to be
even more conservative.

## Requirements

- Windows
- Python 3.9+ (`py --version`)
- You must be signed in to Claude Code with a **Pro/Max subscription** login
  (not an API key). If `claude` works in your terminal, you're set.

## Setup

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

Double-click **`start-tracker.vbs`** — it launches the app with no console
window. A small numbered gauge appears in your tray.

Or from a terminal (shows logs):

```powershell
.\.venv\Scripts\python.exe tray_app.py
```

## Start automatically at login

```powershell
powershell -ExecutionPolicy Bypass -File install-startup.ps1
```

To undo:

```powershell
powershell -ExecutionPolicy Bypass -File install-startup.ps1 -Remove
```

## The tray menu (right-click)

- **Session / Weekly limits** — every limit with its % and reset countdown.
- **Show details…** — open the Account & Usage window (also the double-click action).
- **Refresh now** — poll immediately.
- **Quit** — exit the app.

## Troubleshooting

- **Grey dash icon / "Not signed in"** — open a terminal, run `claude`, sign in
  with your subscription, then use *Refresh now*.
- **Icon too small to read the number** — Windows shrinks tray icons; hover to
  see the exact percentage and reset time in the tooltip.
- **"Rate limited (429)"** — transient; it retries automatically. Don't lower
  `POLL_SECONDS`.

## Files

| File | Purpose |
|------|---------|
| `tray_app.py` | Tray app: icon, menu, details window, 5-min polling loop |
| `usage_client.py` | Calls the usage endpoint, normalises limits |
| `credentials.py` | Reads local token, refreshes it when expired |
| `account.py` | Reads account info (email/org/plan) from `~/.claude.json` |
| `details_window.py` | The Account & Usage popup window (tkinter) |
| `icon.py` | Draws the percentage-bar tray icon |
| `start-tracker.vbs` | Silent launcher (double-click) |
| `install-startup.ps1` | Add/remove run-at-login shortcut |
