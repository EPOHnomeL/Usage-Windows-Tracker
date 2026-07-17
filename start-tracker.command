#!/usr/bin/env bash
# Double-click in Finder (or run in a terminal) to start the tray app on macOS.
cd "$(dirname "$0")"
# Launch detached so closing the Terminal window doesn't stop the tracker.
nohup ./.venv/bin/python tray_app.py >/dev/null 2>&1 &
echo "Claude Usage Tracker started. Look in the menu bar."
