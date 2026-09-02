"""Claude Usage Tracker — a small cross-platform system-tray app.

Tray icon shows the Claude subscription session (5-hour) usage as a live bar.
Right-click -> Show details (or the default double/left action) opens an
Account & Usage window styled like Claude Code's /usage panel.

Portability note: the details window runs as its OWN process (see
details_window.run_standalone). pystray needs the main thread on macOS, and Tk
also wants the main thread, so sharing one process is fragile. Spawning the
window separately sidesteps that entirely and behaves the same on Windows,
macOS and Linux.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading

import pystray
from pystray import Menu, MenuItem

import credentials
import account
import profiles
import usage_client
from icon import make_icon

# Poll cadence. 5 minutes stays well within the endpoint's rate limits.
POLL_SECONDS = 300
ERROR_RETRY_SECONDS = 60

APP_NAME = "Claude Usage"
_HERE = os.path.dirname(os.path.abspath(__file__))
_WINDOW_SCRIPT = os.path.join(_HERE, "details_window.py")

# Detach the window process cleanly per platform (and hide any console on Win).
if sys.platform == "win32":
    _SPAWN_KWARGS = {
        "creationflags": getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    }
else:
    _SPAWN_KWARGS = {"start_new_session": True}


class TrayApp:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._results: list[tuple[profiles.Profile, account.Account,
                                  usage_client.Usage | None, str]] = []
        self._status = "Starting…"
        self._active_key = profiles.load_active_key()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._win_proc: subprocess.Popen | None = None

        self.icon = pystray.Icon(
            APP_NAME,
            icon=make_icon(None, error=True),
            title=f"{APP_NAME}: starting…",
            menu=self._build_menu(),
        )

    # ---- menu -----------------------------------------------------------
    def _build_menu(self) -> Menu:
        with self._lock:
            results, status = self._results, self._status
        items: list = [MenuItem(self._header_text(results, status), None, enabled=False),
                       Menu.SEPARATOR]
        if results:
            for profile, acct, usage, error in results:
                name = acct.email or profile.config_dir.name
                items.append(MenuItem(name, None, enabled=False))
                if usage:
                    for limit in usage.limits:
                        text = f"  {limit.label}: {limit.percent:.0f}%"
                        if limit.resets_in_text:
                            text += f"  ({limit.resets_in_text})"
                        items.append(MenuItem(text, None, enabled=False))
                else:
                    items.append(MenuItem(f"  {error}", None, enabled=False))
        else:
            items.append(MenuItem(status, None, enabled=False))
        items += [
            Menu.SEPARATOR,
            MenuItem("Active account", Menu(*[
                self._profile_menu_item(profile, acct)
                for profile, acct, _, _ in results
            ])) if results else MenuItem("Active account", None, enabled=False),
            MenuItem("Show details…", self._on_show, default=True),
            MenuItem("Refresh now", self._on_refresh_now),
            MenuItem("Quit", self._on_quit),
        ]
        return Menu(*items)

    @staticmethod
    def _header_text(results, status) -> str:
        session_values = [usage.primary_percent for _, _, usage, _ in results
                          if usage and usage.primary_percent is not None]
        if session_values:
            return "Sessions: " + " / ".join(f"{value:.0f}%" for value in session_values)
        return status

    # ---- actions --------------------------------------------------------
    def _on_show(self, icon, item) -> None:
        # Don't spawn a second window if one is already open.
        if self._win_proc is not None and self._win_proc.poll() is None:
            return
        try:
            self._win_proc = subprocess.Popen(
                [sys.executable, _WINDOW_SCRIPT], cwd=_HERE, **_SPAWN_KWARGS
            )
        except Exception:
            pass

    def _on_refresh_now(self, icon, item) -> None:
        self._wake.set()

    def _is_active(self, profile: profiles.Profile) -> bool:
        if self._active_key:
            return profile.key == self._active_key
        # Before the first selection, the normal .claude profile is active.
        return profile.config_dir.name == ".claude"

    def _on_select_profile(self, profile: profiles.Profile) -> None:
        self._active_key = profile.key
        profiles.save_active(profile)
        with self._lock:
            results = self._results
        self._set_results(results)

    def _profile_menu_item(self, profile: profiles.Profile, acct: account.Account) -> MenuItem:
        """Build a two-argument pystray callback for one profile selector."""
        def select(_icon, _item) -> None:
            self._on_select_profile(profile)

        return MenuItem(
            acct.email or profile.config_dir.name,
            select,
            checked=lambda _item: self._is_active(profile),
            radio=True,
        )

    def _on_quit(self, icon, item) -> None:
        self._stop.set()
        self._wake.set()
        icon.stop()

    # ---- state ----------------------------------------------------------
    def _set_results(self, results) -> None:
        with self._lock:
            self._results = results
        active = next(((profile, usage) for profile, _, usage, _ in results
                       if usage and self._is_active(profile)), None)
        primary = active[1] if active else next((usage for _, _, usage, _ in results if usage), None)
        pct = primary.primary_percent if primary else None
        self.icon.icon = make_icon(pct)
        parts = [APP_NAME]
        if pct is not None:
            parts.append(f"- Session {pct:.0f}%")
        s = primary.session if primary else None
        if s and s.resets_in_text:
            parts.append(f"({s.resets_in_text})")
        self.icon.title = " ".join(parts)
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    def _set_error(self, message: str, *, signed_out: bool = False) -> None:
        with self._lock:
            self._results = []
            self._status = message
        self.icon.icon = make_icon(None, error=True)
        prefix = "Not signed in" if signed_out else "Error"
        self.icon.title = f"{APP_NAME}: {prefix} - {message}"
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    # ---- polling loop ---------------------------------------------------
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            delay = POLL_SECONDS
            try:
                results = []
                for profile in profiles.discover():
                    acct = account.load(profile.config_dir)
                    try:
                        usage = usage_client.fetch(profile.config_dir)
                        error = ""
                    except (credentials.CredentialsError, usage_client.UsageError) as e:
                        usage, error = None, str(e)
                    results.append((profile, acct, usage, error))
                if not results:
                    raise credentials.CredentialsError("No Claude profiles found.")
                self._set_results(results)
            except credentials.CredentialsError as e:
                self._set_error(str(e), signed_out=True)
                delay = ERROR_RETRY_SECONDS
            except usage_client.UsageError as e:
                self._set_error(str(e))
                delay = ERROR_RETRY_SECONDS
            except Exception as e:
                self._set_error(f"Unexpected: {e}")
                delay = ERROR_RETRY_SECONDS
            self._wake.wait(timeout=delay)
            self._wake.clear()

    # ---- run ------------------------------------------------------------
    def run(self) -> None:
        def setup(icon):
            icon.visible = True
            threading.Thread(target=self._poll_loop, daemon=True).start()

        self.icon.run(setup=setup)


def main() -> int:
    TrayApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
