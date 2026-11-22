#!/usr/bin/env bash
# Full-screen browser for a line-side station. Started from the desktop autostart (see setup-pi.sh).
# Relaunches the browser if it crashes or an operator manages to close it.
set -u
CONF=/etc/eol-kiosk.env
[ -r "$CONF" ] && . "$CONF"
URL="${KIOSK_URL:-https://ops.leanwatts.com}"
PROFILE="${KIOSK_PROFILE:-$HOME/.config/eol-kiosk-browser}"   # persistent: keeps the LeanWatts login

BROWSER=$(command -v chromium || command -v chromium-browser) || { echo "chromium not installed" >&2; exit 1; }

# Wait (up to 60 s) for the network so the first page load does not show an error page.
for _ in $(seq 60); do
  getent hosts "$(echo "$URL" | sed -E 's#^[a-z]+://([^/:]+).*#\1#')" >/dev/null && break
  sleep 1
done

while true; do
  # Clear the "Chromium didn't shut down correctly" flag left by a power cut.
  sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"[^"]*"/"exit_type":"Normal"/' \
    "$PROFILE/Default/Preferences" 2>/dev/null || true
  "$BROWSER" --kiosk "$URL" \
    --user-data-dir="$PROFILE" \
    --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
    --disable-features=Translate --password-store=basic \
    --check-for-update-interval=31536000 \
    --overscroll-history-navigation=0 --disable-pinch
  sleep 2
done
