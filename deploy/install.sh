#!/usr/bin/env bash
# Install adsb-scope as a boot-start kiosk service.
# Run from the repo root:  sudo bash deploy/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo bash deploy/install.sh" >&2
    exit 1
fi

# The user who owns the checkout (not root).
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo pi)}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> user:  $TARGET_USER"
echo "==> repo:  $REPO_DIR"

if [[ ! -d "/home/$TARGET_USER/adsb-scope" ]]; then
    echo "WARNING: expected the repo at /home/$TARGET_USER/adsb-scope" >&2
    echo "         the service file uses that path; edit it if yours differs" >&2
fi

# cage is required for the kiosk session
if ! command -v cage >/dev/null; then
    echo "==> installing cage"
    apt-get install -y cage
fi

# seat access for the display and input devices
echo "==> adding $TARGET_USER to video,input,render,tty"
usermod -aG video,input,render,tty "$TARGET_USER"

# the kernel DVB driver grabs the SDR on plug-in; readsb detaches it, but
# blacklisting removes the race entirely
if [[ ! -f /etc/modprobe.d/blacklist-rtl.conf ]]; then
    echo "==> blacklisting dvb_usb_rtl28xxu (kernel TV-tuner driver)"
    echo 'blacklist dvb_usb_rtl28xxu' > /etc/modprobe.d/blacklist-rtl.conf
fi

echo "==> installing systemd unit as adsb-scope@$TARGET_USER"
install -m 644 "$REPO_DIR/deploy/adsb-scope.service" \
    /etc/systemd/system/adsb-scope@.service
systemctl daemon-reload
systemctl enable "adsb-scope@$TARGET_USER.service"

cat <<MSG

Installed. Useful commands:

  sudo systemctl start   adsb-scope@$TARGET_USER     # start now
  sudo systemctl stop    adsb-scope@$TARGET_USER     # stop (frees the screen)
  sudo systemctl status  adsb-scope@$TARGET_USER     # state
  journalctl -u adsb-scope@$TARGET_USER -f           # live logs
  sudo systemctl disable adsb-scope@$TARGET_USER     # stop starting at boot

It will start automatically on the next boot.
MSG
