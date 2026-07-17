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
        self._usage: usage_client.Usage | None = None
        self._status = "Starting…"
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
            usage, status = self._usage, self._status
        items: list = [MenuItem(self._header_text(usage, status), None, enabled=False),
                       Menu.SEPARATOR]
        if usage:
            for l in usage.limits:
                text = f"{l.label}: {l.percent:.0f}%"
                if l.resets_in_text:
                    text += f"  ({l.resets_in_text})"
                items.append(MenuItem(text, None, enabled=False))
        else:
            items.append(MenuItem(status, None, enabled=False))
        items += [
            Menu.SEPARATOR,
            MenuItem("Show details…", self._on_show, default=True),
            MenuItem("Refresh now", self._on_refresh_now),
            MenuItem("Quit", self._on_quit),
        ]
        return Menu(*items)

    @staticmethod
    def _header_text(usage, status) -> str:
        if usage and usage.primary_percent is not None:
            return f"Session: {usage.primary_percent:.0f}%"
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

    def _on_quit(self, icon, item) -> None:
        self._stop.set()
        self._wake.set()
        icon.stop()

    # ---- state ----------------------------------------------------------
    def _set_usage(self, usage: usage_client.Usage) -> None:
        with self._lock:
            self._usage = usage
        pct = usage.primary_percent
        self.icon.icon = make_icon(pct)
        parts = [APP_NAME]
        if pct is not None:
            parts.append(f"- Session {pct:.0f}%")
        s = usage.session
        if s and s.resets_in_text:
            parts.append(f"({s.resets_in_text})")
        self.icon.title = " ".join(parts)
        self.icon.menu = self._build_menu()
        self.icon.update_menu()

    def _set_error(self, message: str, *, signed_out: bool = False) -> None:
        with self._lock:
            self._usage = None
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
                self._set_usage(usage_client.fetch())
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
