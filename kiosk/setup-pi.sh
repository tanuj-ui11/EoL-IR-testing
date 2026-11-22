#!/usr/bin/env bash
# One-time setup of a Raspberry Pi (Raspberry Pi OS with desktop, Bookworm or later) as a line-side kiosk.
#   sudo ./kiosk/setup-pi.sh                 # Option A: browser kiosk only (scanner types into the page)
#   sudo ./kiosk/setup-pi.sh --forwarder     # also install the background scan forwarder (Option B)
# Safe to run again. Run from a checkout of this repository. Reboot afterwards.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
REPO=$(cd "$(dirname "$0")/.." && pwd)
KIOSK_USER=${SUDO_USER:-pi}
HOME_DIR=$(getent passwd "$KIOSK_USER" | cut -d: -f6)
FORWARDER=0; [ "${1:-}" = "--forwarder" ] && FORWARDER=1

echo "== packages"
apt-get update -q
apt-get install -y -q python3-venv unclutter-xfixes 2>/dev/null || apt-get install -y -q python3-venv
command -v chromium >/dev/null || command -v chromium-browser >/dev/null || \
  apt-get install -y -q chromium || apt-get install -y -q chromium-browser

echo "== boot to desktop, auto-login $KIOSK_USER, no screen blanking"
if command -v raspi-config >/dev/null; then
  raspi-config nonint do_boot_behaviour B4
  raspi-config nonint do_blanking 1
fi

echo "== kiosk launcher"
install -m 0755 "$REPO/kiosk/kiosk.sh" /usr/local/bin/eol-kiosk
[ -f /etc/eol-kiosk.env ] || install -m 0644 "$REPO/kiosk/eol-kiosk.env.example" /etc/eol-kiosk.env
# labwc (current Pi OS default) and wayfire (early Bookworm) autostart; LXDE for X11 setups.
install -d -o "$KIOSK_USER" -g "$KIOSK_USER" "$HOME_DIR/.config/labwc" "$HOME_DIR/.config/lxsession/LXDE-pi"
AUTOSTART="$HOME_DIR/.config/labwc/autostart"
grep -qs eol-kiosk "$AUTOSTART" || echo "/usr/local/bin/eol-kiosk &" >> "$AUTOSTART"
LX="$HOME_DIR/.config/lxsession/LXDE-pi/autostart"
grep -qs eol-kiosk "$LX" || printf '@xset s off\n@xset -dpms\n@unclutter -idle 3\n@/usr/local/bin/eol-kiosk\n' >> "$LX"
WF="$HOME_DIR/.config/wayfire.ini"
if [ -f "$WF" ] && ! grep -qs eol-kiosk "$WF"; then
  grep -q '^\[autostart\]' "$WF" || printf '\n[autostart]\n' >> "$WF"
  sed -i '/^\[autostart\]/a kiosk = /usr/local/bin/eol-kiosk' "$WF"
fi
chown "$KIOSK_USER:$KIOSK_USER" "$AUTOSTART" "$LX"

echo "== station software in /opt/eol-station/venv"
python3 -m venv /opt/eol-station/venv
/opt/eol-station/venv/bin/pip install -q "$REPO"

if [ "$FORWARDER" -eq 1 ]; then
  echo "== scan forwarder service"
  [ -f /etc/scan-forwarder.env ] || install -m 0600 "$REPO/kiosk/scan-forwarder.env.example" /etc/scan-forwarder.env
  install -m 0644 "$REPO/kiosk/scan-forwarder.service" /etc/systemd/system/scan-forwarder.service
  systemctl daemon-reload
  systemctl enable scan-forwarder
  if grep -q REPLACE /etc/scan-forwarder.env; then
    echo "!! Edit /etc/scan-forwarder.env (scanner device, webhook URL, token), then: sudo systemctl start scan-forwarder"
  else
    systemctl restart scan-forwarder
  fi
fi

echo "Done. Set the page in /etc/eol-kiosk.env, then reboot."
