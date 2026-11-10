#!/bin/sh
# One-line installer for obc40-home. Run it as the desktop user (not root), e.g. in a terminal on the display:
#
#   wget -qO- https://raw.githubusercontent.com/dariotronic/obc40-home/main/get.sh | sh
#
# Options (after `sh -s --`):  --no-autostart   do not start the launcher at every login
#
# It downloads the latest release from GitHub, verifies its SHA-256 checksum, runs its install.sh and
# starts the launcher. Missing system packages are installed with `su` after asking.
set -e
REPO=dariotronic/obc40-home
NAME=obc40-home
OPTS=""
for a in "$@"; do
  case "$a" in
    --no-autostart) OPTS="$OPTS $a" ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done

if [ "$(id -u)" = 0 ]; then
  echo "Run this as the desktop user, not as root: the launcher is installed in your home directory." >&2
  exit 1
fi

# --- system packages
need=""
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null \
  || need="$need py3-gobject3 gtk+3.0"
python3 -c 'import gi; gi.require_version("Wnck", "3.0"); from gi.repository import Wnck' 2>/dev/null \
  || need="$need libwnck3"
if [ -n "$need" ]; then
  echo "Missing system packages:$need"
  if (: </dev/tty) 2>/dev/null; then     # an interactive terminal is available
    printf "Install them now with su (asks for the root password)? [Y/n] "
    read -r ans </dev/tty || ans=n
    case "$ans" in n|N|no) echo "Install them with: su -c 'apk add$need'" >&2; exit 1 ;; esac
    su -c "apk add$need" </dev/tty
  else
    echo "Install them with: su -c 'apk add$need'  and run this again." >&2
    exit 1
  fi
fi

# --- download, verify, install
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
base="https://github.com/$REPO/releases/latest/download"
echo "== $NAME: downloading the latest release"
wget -q -O "$TMP/$NAME.tar.gz" "$base/$NAME.tar.gz"
wget -q -O "$TMP/$NAME.tar.gz.sha256" "$base/$NAME.tar.gz.sha256"
expected=$(cut -d' ' -f1 "$TMP/$NAME.tar.gz.sha256" | tr -d '\r')
actual=$(sha256sum "$TMP/$NAME.tar.gz" | cut -d' ' -f1)
[ "$expected" = "$actual" ] || { echo "$NAME: checksum mismatch, nothing installed" >&2; exit 1; }
tar xzf "$TMP/$NAME.tar.gz" -C "$TMP"
sh "$TMP/$NAME/install.sh" $OPTS

# --- start it now, if a graphical session is running (restart it if it was already open)
if [ -z "$DISPLAY" ]; then
  P=$(pgrep -u "$(id -un)" -x xfce4-session | head -1 || true)
  if [ -n "$P" ]; then
    eval "export $(tr '\0' '\n' < /proc/$P/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=' \
      | sed 's/=\(.*\)/="\1"/' | tr '\n' ' ')"
  fi
fi
if [ -n "$DISPLAY" ]; then
  pkill -f "^python3 .*/obc40-home/obc-home\$" 2>/dev/null || true
  sleep 1
  pgrep -f "^python3 .*/obc40-home/obc-fitwin" >/dev/null || (setsid "$HOME/.local/bin/obc-fitwin" >/dev/null 2>&1 </dev/null &)
  (setsid "$HOME/.local/bin/obc-home" >/dev/null 2>&1 </dev/null &)
  echo "== done: the launcher is starting on the display"
else
  echo "== done: no graphical session found, the launcher will start at the next login"
fi
