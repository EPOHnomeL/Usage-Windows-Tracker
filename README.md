# Claude Usage Tracker (Windows / macOS / Linux)

A tiny system-tray / menu-bar app that shows your **Claude subscription session
usage** as a live percentage bar — the same "Session (5-hour)" number that
Claude Code's `/usage` command and claude.ai show. Hover for the exact figure
and reset time; **click Show details for a full Account & Usage window**.

![tray icon examples](_preview/icon_78.png)
![details window](_preview/window.png)

One Python codebase runs on all three platforms; only the credential source and
the launchers differ per OS (details below).

## Details window

Right-click the tray icon → **Show details…** (also the default click action) to
open an Account & Usage panel styled like Claude Code's `/usage`:

- **Account** — auth method, email, organization, and plan (read locally from
  `~/.claude.json`, no network call).
- **Usage** — every limit (Session 5-hour, Weekly all-models, Weekly per-model)
  with a coloured progress bar and a reset countdown.
- **Multiple accounts** — discovers `%USERPROFILE%\.claude` and sibling
  `%USERPROFILE%\.claude-*` profiles, showing each account separately in the
  details window and tray menu. The tray icon remains the default profile's
  session gauge.
- **Refresh now** button; the window also auto-refreshes every 60s while open.

The window runs as its own process, which keeps the tray icon rock-solid across
all three platforms (pystray and tkinter both want the main thread — separating
them avoids that conflict, notably on macOS).

> Not (yet) included: the "What's contributing to your limits usage?" breakdown
> from `/usage`. That's analytics Claude Code computes from your local session
> logs using its own heuristics; reproducing it faithfully is separate work.
> Ask if you'd like an approximate version added.

## How it works

- Reads your existing Claude sign-in token (see per-OS locations below) — the
  token Claude Code already stores, so **no separate login needed**.
- Every 5 minutes it calls Anthropic's usage endpoint
  (`GET https://api.anthropic.com/api/oauth/usage`) and redraws the icon.
- Refreshes the access token automatically when it expires.
- The colour shifts green → amber → orange → red as you approach your limit.

Your token is only ever sent to Anthropic's own hosts (`api.anthropic.com` /
`platform.claude.com`) — the same ones Claude Code uses. Nothing is stored or
sent anywhere else.

**Credential source per OS:**

| OS | Where the token is read from |
|----|------------------------------|
| Windows | `%USERPROFILE%\.claude\.credentials.json` |
| Linux | `~/.claude/.credentials.json` |
| macOS | login **Keychain** item `Claude Code-credentials` (via `security`) |

On macOS the app never writes to the Keychain — if a token needs refreshing it
does so in memory for that run, leaving Claude Code's Keychain item untouched.

To monitor an explicit set of profile directories instead of automatic
discovery, set `CLAUDE_USAGE_CONFIG_DIRS` before launching. Separate Windows
paths with semicolons:

```powershell
$env:CLAUDE_USAGE_CONFIG_DIRS = 'C:\Users\lemon\.claude;C:\Users\lemon\.claude-jvorster63'
```

## ⚠️ Please read: terms-of-service note

As of early 2026, Anthropic restricts these OAuth tokens to the official Claude
Code CLI and claude.ai, and using them from a third-party tool is technically
against the consumer Terms of Service. This app is a personal, **read-only**
monitor of *your own* account and polls infrequently (default every 5 min) to
stay gentle — but be aware:

- The `/api/oauth/usage` endpoint is **undocumented** and could change or break.
- There is a real (if small) risk that using tokens outside official clients
  could flag your account.

Use at your own discretion. Raise `POLL_SECONDS` in `tray_app.py` to be even
more conservative.

## Common requirements

- Python 3.9+
- Signed in to Claude Code with a **Pro/Max subscription** login (not an API
  key). If `claude` works in your terminal, you're set.
- Tkinter (for the details window) — bundled with Python on Windows/macOS;
  on Linux install `python3-tk`.

---

## Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- **Run:** double-click `start-tracker.vbs` (no console window). Or
  `.\.venv\Scripts\python.exe tray_app.py` from a terminal.
- **Start at login:** `powershell -ExecutionPolicy Bypass -File install-startup.ps1`
  (undo with `-Remove`).

## macOS

```bash
chmod +x setup-macos.sh && ./setup-macos.sh
```

This creates the venv and installs `requirements.txt` +
`requirements-macos.txt` (PyObjC, which pystray's menu-bar backend needs).

- **Run:** `./start-tracker.command` (or double-click it in Finder). The icon
  appears in the **menu bar**.
- **Start at login:** `./install-startup-macos.sh` (installs a LaunchAgent;
  undo with `--remove`).
- The first Keychain read may show a macOS prompt to allow access — click
  *Always Allow*.
- If Python is from Homebrew and the window won't open, install Tk:
  `brew install python-tk`.

## Linux

Install the system libraries the tray backend needs, then set up:

```bash
# Debian/Ubuntu
sudo apt install python3-tk python3-gi gir1.2-ayatanaappindicator3-0.1
# Fedora
# sudo dnf install python3-tkinter python3-gobject libappindicator-gtk3

chmod +x setup-linux.sh && ./setup-linux.sh
```

`setup-linux.sh` creates the venv with `--system-site-packages` so it can use
the distro's PyGObject (`python3-gi`), which the AppIndicator tray backend uses.

- **Run:** `./start-tracker.sh`. The icon appears in the system tray.
- **Start at login:** `./install-startup-linux.sh` (adds an XDG autostart entry;
  undo with `--remove`).
- **GNOME (esp. Wayland):** tray icons require the **AppIndicator / KStatusNotifierItem**
  shell extension. Install it from GNOME Extensions if you don't see the icon.
- You can force a backend with `PYSTRAY_BACKEND=appindicator` (or `gtk` / `xorg`).

---

## The tray menu (right-click)

- **Session / Weekly limits** — every limit with its % and reset countdown.
- **Show details…** — open the Account & Usage window (also the default click).
- **Refresh now** — poll immediately.
- **Quit** — exit the app.

## Troubleshooting

- **Grey dash icon / "Not signed in"** — run `claude` in a terminal, sign in
  with your subscription, then *Refresh now*. On macOS, allow Keychain access
  when prompted.
- **Icon too small to read** — the OS shrinks tray icons; hover for the exact
  percentage and reset time in the tooltip.
- **"Rate limited (429)"** — transient; it retries automatically. Don't lower
  `POLL_SECONDS`.
- **Linux: no icon appears** — you're likely missing the AppIndicator system
  package or (on GNOME) the shell extension. See the Linux section.

## Files

| File | Purpose |
|------|---------|
| `tray_app.py` | Tray app: icon, menu, spawns the details window, polling loop |
| `usage_client.py` | Calls the usage endpoint, normalises limits |
| `credentials.py` | Reads the local token (file or macOS Keychain), refreshes it |
| `account.py` | Reads account info (email/org/plan) from each profile's `.claude.json` |
| `profiles.py` | Discovers Claude Code profile directories for multi-account monitoring |
| `details_window.py` | The Account & Usage popup window (tkinter), runs standalone |
| `icon.py` | Draws the percentage-bar tray icon (cross-platform fonts) |
| `requirements*.txt` | Base + `-macos` / `-linux` extras |
| `start-tracker.*` | Launchers: `.vbs` (Win), `.command` (mac), `.sh` (Linux) |
| `setup-*.sh` | One-time venv + dependency setup for mac/linux |
| `install-startup.*` | Add/remove run-at-login (per OS) |
