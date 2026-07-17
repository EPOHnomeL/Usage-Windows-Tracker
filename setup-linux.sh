#!/usr/bin/env bash
# One-time setup on Linux: create the venv and install dependencies.
#
# The tray icon needs system libraries too. On Debian/Ubuntu:
#   sudo apt install python3-tk python3-gi gir1.2-ayatanaappindicator3-0.1
# On Fedora:
#   sudo dnf install python3-tkinter python3-gobject libappindicator-gtk3
# GNOME/Wayland users also need the "AppIndicator and KStatusNotifierItem"
# shell extension for the icon to appear.
set -euo pipefail
cd "$(dirname "$0")"

# --system-site-packages so the venv can see distro-provided PyGObject (gi),
# which pystray's AppIndicator backend needs.
python3 -m venv --system-site-packages .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
# XOrg fallback backend; ignore failure if build deps are missing.
./.venv/bin/python -m pip install -r requirements-linux.txt || \
  echo "(note: python-xlib fallback not installed; AppIndicator backend will be used)"

chmod +x start-tracker.sh install-startup-linux.sh 2>/dev/null || true

echo
echo "Setup complete."
echo "Start it:        ./start-tracker.sh"
echo "Start at login:  ./install-startup-linux.sh"
