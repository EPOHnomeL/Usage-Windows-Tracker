"""The 'Account & Usage' details window (tkinter), styled with Yknot branding.

Mirrors the layout of Claude Code's /usage panel: an Account section and a
Usage section with a coloured progress bar and reset countdown per limit, plus
the Yknot logo and a link to the company usage dashboard.

Tkinter is single-threaded: this window must only be created and updated from
the same (main) thread that owns the Tk root.
"""
from __future__ import annotations

import os
import tkinter as tk
import webbrowser
from datetime import datetime

import fonts
from account import Account
from icon import _bar_color
from usage_client import Usage

# ---- Yknot brand palette (light mode, matching y-knot.io) --------------
NAVY = "#2e3252"        # brand navy (logo cube + wordmark) — primary text
TEAL = "#3f9fb0"        # brand teal accent
TEAL_HOVER = "#33808e"
NAVY_HOVER = "#3c4168"
SAND = "#e0c0a0"        # rope highlight

BG = "#ffffff"          # white page background (matches the logo's white)
CARD = "#f2f4f7"        # subtle raised surfaces
TRACK = "#e4e8ee"       # progress-bar track
TEXT = NAVY             # primary text in brand navy
MUTED = "#6b7280"       # secondary text
HEADING = TEAL          # section headers in brand teal
BORDER = "#e2e6ec"

# Company usage dashboard linked from the window.
DASHBOARD_URL = "https://claude-ussage.vercel.app/"
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "Yknot_landscape_smooth_Logo.PNG")

# Register bundled Inter (y-knot.io's font) and pick the family names.
fonts.register()
FONT = fonts.UI_FAMILY          # body / labels
FONT_DISPLAY = fonts.DISPLAY_FAMILY  # title / logo wordmark feel


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


class DetailsWindow:
    def __init__(self, root: tk.Tk, *, on_refresh, on_close=None) -> None:
        self._root = root
        self._on_refresh = on_refresh
        self._on_close = on_close
        self._win: tk.Toplevel | None = None
        self._body: tk.Frame | None = None
        self._footer_label: tk.Label | None = None
        self._logo_img = None  # keep a ref or Tk garbage-collects the image
        self._last: tuple = ()  # cache so we can rerender on show

    # ---- branding -------------------------------------------------------
    def _load_logo(self, target_w: int = 200):
        """Return a Tk image of the Yknot logo on the light page background."""
        if self._logo_img is not None:
            return self._logo_img
        try:
            from PIL import Image, ImageColor, ImageTk
            logo = Image.open(_LOGO_PATH).convert("RGBA")
            scale = target_w / logo.width
            logo = logo.resize((target_w, max(1, round(logo.height * scale))),
                               Image.LANCZOS)
            # Composite onto the page colour so anti-aliased edges blend in.
            bg = Image.new("RGBA", logo.size, ImageColor.getrgb(BG) + (255,))
            bg.alpha_composite(logo)
            self._logo_img = ImageTk.PhotoImage(bg)
        except Exception:
            self._logo_img = None
        return self._logo_img

    # ---- lifecycle ------------------------------------------------------
    def _ensure(self) -> None:
        if self._win is not None:
            return
        win = tk.Toplevel(self._root)
        win.title("Account & Usage")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.hide)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass

        # Branded header: Yknot logo directly on the light background.
        logo = self._load_logo()
        if logo is not None:
            header = tk.Frame(win, bg=BG)
            header.pack(fill="x", padx=18, pady=(16, 6))
            tk.Label(header, image=logo, bg=BG).pack(side="left")

        # Title + teal accent rule
        top = tk.Frame(win, bg=BG)
        top.pack(fill="x", padx=18, pady=(6, 2))
        tk.Label(top, text="Account & Usage", bg=BG, fg=NAVY,
                 font=(FONT_DISPLAY, 15, "bold")).pack(side="left")
        tk.Frame(win, bg=TEAL, height=2).pack(fill="x", padx=18, pady=(5, 2))

        self._body = tk.Frame(win, bg=BG)
        self._body.pack(fill="both", expand=True, padx=18, pady=(4, 6))

        # Dashboard link (teal, opens the company usage tracker in a browser).
        link_row = tk.Frame(win, bg=BG)
        link_row.pack(fill="x", padx=18, pady=(0, 2))
        link = tk.Label(link_row, text="↗  Open Yknot usage dashboard",
                        bg=BG, fg=TEAL, font=(FONT, 9, "underline"),
                        cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: webbrowser.open(DASHBOARD_URL))
        link.bind("<Enter>", lambda _e: link.config(fg=TEAL_HOVER))
        link.bind("<Leave>", lambda _e: link.config(fg=TEAL))

        footer = tk.Frame(win, bg=BG)
        footer.pack(fill="x", padx=18, pady=(2, 14))
        self._footer_label = tk.Label(footer, text="", bg=BG, fg=MUTED,
                                      font=(FONT, 8))
        self._footer_label.pack(side="left")
        btn = tk.Label(footer, text="Refresh now", bg=NAVY, fg="white",
                       font=(FONT, 9, "bold"), padx=14, pady=6, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda _e: self._on_refresh())
        btn.bind("<Enter>", lambda _e: btn.config(bg=NAVY_HOVER))
        btn.bind("<Leave>", lambda _e: btn.config(bg=NAVY))

        self._win = win

    def show(self) -> None:
        self._ensure()
        assert self._win is not None
        if self._last:
            self._render(*self._last)
        self._win.deiconify()
        self._win.lift()
        self._win.focus_force()
        self._center()

    def hide(self) -> None:
        if self._win is not None:
            self._win.withdraw()
        if self._on_close:
            self._on_close()

    def _center(self) -> None:
        win = self._win
        if not win:
            return
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        # Anchor bottom-right, near the tray, with a margin for the taskbar.
        x = sw - w - 24
        y = sh - h - 64
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    # ---- rendering ------------------------------------------------------
    def update(self, usage: Usage | None, acct: Account, status: str,
               last_updated: datetime | None) -> None:
        """Cache latest data; rerender if the window is currently visible."""
        self._last = (usage, acct, status, last_updated)
        if self._win is not None and self._win.state() != "withdrawn":
            self._render(usage, acct, status, last_updated)

    def _render(self, usage, acct: Account, status, last_updated) -> None:
        body = self._body
        assert body is not None
        for child in body.winfo_children():
            child.destroy()

        self._section(body, "ACCOUNT")
        self._kv(body, "Auth method", acct.auth_method or "-")
        self._kv(body, "Email", acct.email or "-")
        self._kv(body, "Organization", acct.organization or "-")
        self._kv(body, "Plan", acct.plan or "-")

        self._section(body, "USAGE", pady_top=14)
        if usage and usage.limits:
            for limit in usage.limits:
                self._usage_row(body, limit.label, limit.percent,
                                limit.resets_in_text)
        else:
            tk.Label(body, text=status or "No usage data", bg=BG, fg=MUTED,
                     font=(FONT, 9), anchor="w", justify="left",
                     wraplength=320).pack(fill="x", pady=(6, 0))

        if self._footer_label is not None:
            if last_updated:
                self._footer_label.config(
                    text=f"Updated {last_updated.strftime('%H:%M:%S')}")
            else:
                self._footer_label.config(text="")

    def _section(self, parent, text, *, pady_top=2) -> None:
        tk.Label(parent, text=text, bg=BG, fg=HEADING,
                 font=(FONT, 8, "bold"), anchor="w").pack(
                     fill="x", pady=(pady_top, 4))

    def _kv(self, parent, key, value) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=key, bg=BG, fg=MUTED, font=(FONT, 9),
                 anchor="w").pack(side="left")
        tk.Label(row, text=value, bg=BG, fg=TEXT, font=(FONT, 9, "bold"),
                 anchor="e").pack(side="right")

    def _usage_row(self, parent, name, percent, resets_text) -> None:
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", pady=(8, 2))

        head = tk.Frame(wrap, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text=name, bg=BG, fg=TEXT, font=(FONT, 10),
                 anchor="w").pack(side="left")
        tk.Label(head, text=f"{percent:.0f}%", bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold"), anchor="e").pack(side="right")

        # Progress bar drawn on a canvas.
        bar_w, bar_h = 324, 7
        c = tk.Canvas(wrap, width=bar_w, height=bar_h, bg=BG,
                      highlightthickness=0)
        c.pack(fill="x", pady=(5, 0))
        c.create_rectangle(0, 0, bar_w, bar_h, fill=TRACK, outline="")
        fill_w = int(bar_w * max(0.0, min(100.0, percent)) / 100.0)
        if fill_w > 0:
            c.create_rectangle(0, 0, fill_w, bar_h,
                               fill=_hex(_bar_color(percent)), outline="")

        if resets_text:
            tk.Label(wrap, text=resets_text.capitalize(), bg=BG, fg=MUTED,
                     font=(FONT, 8), anchor="w").pack(fill="x", pady=(3, 0))


def run_standalone() -> None:
    """Run the window as its own process (how the tray opens it).

    Self-contained: fetches its own data, refreshes on demand and every 60s,
    and exits when the window is closed. Keeping this in a separate process
    avoids the pystray/tkinter main-thread conflict on macOS and Linux.
    """
    import account as account_mod
    import usage_client

    root = tk.Tk()
    root.withdraw()

    win = DetailsWindow(root, on_refresh=lambda: None, on_close=root.quit)

    def reload() -> None:
        try:
            usage = usage_client.fetch()
            status = ""
        except Exception as e:  # CredentialsError, UsageError, network, etc.
            usage, status = None, str(e)
        win.update(usage, account_mod.load(), status, datetime.now())

    # Wire the Refresh button to a real reload.
    win._on_refresh = reload

    reload()
    win.show()

    def tick() -> None:
        reload()
        root.after(60_000, tick)

    root.after(60_000, tick)
    root.mainloop()


if __name__ == "__main__":
    run_standalone()
