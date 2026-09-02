# CONTEXT

The project's ubiquitous language. When code, issues, or docs name a domain
concept, use the term as defined here rather than a synonym.

## What this project is

A small, cross-platform (Windows-first) **system-tray app** that shows your
personal Claude subscription usage as a live percentage gauge next to the clock.
It is a **read-only monitor** of your own account: it reads the OAuth token
Claude Code already stores, polls Anthropic's usage endpoint, and redraws a tray
icon. It never logs in separately and never sends your token anywhere except
Anthropic's own hosts.

## Glossary

### Usage domain

- **Limit** — one rate-limit bucket returned by the usage endpoint, with a
  `kind`, a `percent` (0–100), an optional `resets_at`, and a human `label`.
  Modelled by the `Limit` dataclass in `usage_client.py`.
- **Limit kind** — the category of a limit. Canonical values: `session`,
  `weekly_all`, `weekly_scoped`. Do not invent new kind strings; add to
  `_LABELS` if the endpoint introduces one.
- **Session (5-hour) limit** — the `session`-kind limit. This is the **primary
  limit**: the single number drawn on the tray icon and shown in the tooltip
  header. Same figure claude.ai and `/usage` call "Session (5-hour)".
- **Primary percent** — the percentage shown on the tray icon. Defined as the
  session limit's percent, falling back to the first available limit if there is
  no session limit. See `Usage.primary_percent`.
- **Weekly (all models)** — the `weekly_all`-kind limit; the seven-day cap
  spanning every model.
- **Weekly (per-model) / scoped limit** — a `weekly_scoped`-kind limit tied to a
  specific model (e.g. "Weekly (Opus)"). Its label is derived from the model's
  `display_name` in the response `scope`.
- **Usage** — the whole snapshot: the list of Limits from one fetch. Modelled by
  the `Usage` dataclass.
- **Reset countdown** — the human "resets in Xd Yh / Yh Zm / Zm" text derived
  from a limit's `resets_at`. See `Limit.resets_in_text`.
- **Legacy (flat) shape** — the older/deprecated response format keyed by
  `five_hour` / `seven_day` / `seven_day_opus` / `seven_day_sonnet` with a
  `utilization` field, as opposed to the current `limits: [...]` list. The client
  falls back to it when `limits` is absent.

### Account domain

- **Account** — locally-cached account info (display name, email, organization,
  plan, auth method, extra-usage flag) read from each profile's
  `CLAUDE_CONFIG_DIR/.claude.json` under
  `oauthAccount`. Read-only, no network call. Modelled by the `Account`
  dataclass in `account.py`.
- **Plan** — the friendly subscription tier label (Claude Pro / Claude Max /
  Claude team / Claude enterprise), derived from `organizationType`
  (falling back to `seatTier`).
- **Extra usage** — the "extra usage enabled" account flag
  (`hasExtraUsageEnabled`).

### Credentials domain

- **Credentials** — the OAuth `access_token`, `refresh_token`, and
  `expires_at_ms` read from local storage. Modelled by the `Credentials`
  dataclass in `credentials.py`.
- **Credential store** — where the token lives, per platform: the JSON file
  `CLAUDE_CONFIG_DIR/.credentials.json` on Windows/Linux; the login **Keychain** on
  macOS (read via the `security` CLI, never written back to).
- **Refresh** — exchanging the refresh token for a new access token at the
  refresh URL, done automatically when the token is expired (or after a 401).
  On non-macOS platforms the new token is persisted back to the credentials
  file; on macOS it is used in-memory only.
- **Expiry skew** — the buffer (5 minutes) before the real expiry at which a
  token is treated as expired, so refreshes happen slightly early.
- **Signed out / Not signed in** — the state where no usable credentials exist
  (missing file, no access token). Surfaced as `CredentialsError` and shown as a
  grey dash icon.

### UI / app domain

- **Tray icon** — the rendered gauge: a rounded frame with a bottom-up coloured
  fill and the percentage number overlaid. Drawn by `make_icon` in `icon.py`.
- **Icon colour band** — the fill colour by percent: green (<50), amber (50–74),
  orange (75–89), red (≥90). See `_bar_color`.
- **Error / unknown state** — a muted frame with a dim dash instead of a fill,
  drawn when usage is unknown (not signed in, network/API error).
- **Details window** — the "Account & Usage" popup (tkinter) styled like Claude
  Code's `/usage`, launched on double-click or "Show details…". Runs as its
  **own process** (`details_window.run_standalone`) to avoid main-thread
  conflicts between pystray and Tk.
- **Poll loop** — the background thread that fetches Usage every `POLL_SECONDS`
  (300s) and redraws, retrying after `ERROR_RETRY_SECONDS` (60s) on failure.
- **Refresh now / wake** — a user-triggered immediate poll, implemented by
  setting the `_wake` event so the poll loop stops waiting.

## Invariants & constraints

- **Read-only.** The app never mutates account state on Anthropic's side; the
  only local write is persisting a refreshed token to the credentials file
  (never on macOS).
- **Anthropic hosts only.** The token is sent only to `api.anthropic.com` and
  `platform.claude.com` — the same hosts Claude Code uses.
- **Gentle polling.** Default cadence is 5 minutes to stay well within rate
  limits; a 429 is transient and retried, never worked around by polling faster.
- **User-Agent must read `claude-code/<version>`** or the undocumented usage
  endpoint throttles hard. The version is detected from the installed CLI, with
  a fallback constant.
- The `/api/oauth/usage` endpoint is **undocumented** and may change; the client
  tolerates both the current list shape and the legacy flat shape.

## External dependencies

- **Anthropic usage endpoint** — `GET https://api.anthropic.com/api/oauth/usage`.
- **OAuth token refresh** — `POST https://platform.claude.com/v1/oauth/token`.
- **Claude Code** — supplies the stored credentials and the account cache; the
  app is a passive reader of both.
- **Python libraries** — `requests` (HTTP), `pystray` + `Pillow` (tray icon),
  `tkinter` (details window).
