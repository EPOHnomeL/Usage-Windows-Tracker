#!/usr/bin/env bash
# Start the tray app on Linux.
cd "$(dirname "$0")"
# Launch detached so closing the terminal doesn't stop the tracker.
nohup ./.venv/bin/python tray_app.py >/dev/null 2>&1 &
echo "Claude Usage Tracker started. Look in the system tray."
