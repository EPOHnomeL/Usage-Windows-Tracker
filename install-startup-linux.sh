#!/usr/bin/env bash
# Install (or remove) an XDG autostart entry so the tracker starts at login.
#   ./install-startup-linux.sh          # install
#   ./install-startup-linux.sh --remove # uninstall
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP="$HOME/.config/autostart/claude-usage-tracker.desktop"

if [[ "${1:-}" == "--remove" ]]; then
  rm -f "$DESKTOP"
  echo "Removed autostart entry."
  exit 0
fi

mkdir -p "$HOME/.config/autostart"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Claude Usage Tracker
Comment=Shows Claude subscription usage in the system tray
Exec=$DIR/.venv/bin/python $DIR/tray_app.py
Path=$DIR
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Installed autostart entry: $DESKTOP"
echo "Remove with: ./install-startup-linux.sh --remove"
