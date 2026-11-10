#!/bin/sh
# One-line installer for the OBC40 apps. Run it as the desktop user (not root), e.g. in a terminal on the
# display:
#
#   wget -qO- https://raw.githubusercontent.com/dariotronic/obc40-home/main/get.sh | sh
#   wget -qO- https://raw.githubusercontent.com/dariotronic/obc40-home/main/get.sh | sh -s -- --with-desk-player
#
# Options: --with-desk-player  also install obc40-desk-player (the Spotify remote)
#          --with-home         also install obc40-home (the launcher)
#          --no-autostart      do not start obc40-home at every login
#          --desktop-icon      put a "Musica" icon on the desktop (obc40-desk-player)
#          --autostart         start obc40-desk-player at every login
#
# It downloads the latest release of each app from GitHub, verifies its SHA-256 checksum, runs its
# install.sh and starts the app. Missing system packages are installed with `su` after asking.
set -e
OWNER=dariotronic
MAIN=obc40-home                      # the repository this copy of get.sh comes from

APPS="$MAIN"
HOME_OPTS=""
DP_OPTS=""
for a in "$@"; do
  case "$a" in
    --with-desk-player) APPS="$APPS obc40-desk-player" ;;
    --with-home) APPS="obc40-home $APPS" ;;
    --no-autostart) HOME_OPTS="$HOME_OPTS --no-autostart" ;;
    --desktop-icon|--autostart) DP_OPTS="$DP_OPTS $a" ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done
APPS=$(echo "$APPS" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ')

if [ "$(id -u)" = 0 ]; then
  echo "Run this as the desktop user, not as root: the apps are installed in your home directory." >&2
  exit 1
fi

# --- system packages
need=""
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null \
  || need="$need py3-gobject3 gtk+3.0"
case " $APPS " in *" obc40-home "*)
  python3 -c 'import gi; gi.require_version("Wnck", "3.0"); from gi.repository import Wnck' 2>/dev/null \
    || need="$need libwnck3" ;;
esac
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
for repo in $APPS; do
  base="https://github.com/$OWNER/$repo/releases/latest/download"
  echo "== $repo: downloading the latest release"
  wget -q -O "$TMP/$repo.tar.gz" "$base/$repo.tar.gz"
  wget -q -O "$TMP/$repo.tar.gz.sha256" "$base/$repo.tar.gz.sha256"
  expected=$(cut -d' ' -f1 "$TMP/$repo.tar.gz.sha256" | tr -d '\r')
  actual=$(sha256sum "$TMP/$repo.tar.gz" | cut -d' ' -f1)
  [ "$expected" = "$actual" ] || { echo "$repo: checksum mismatch, nothing installed" >&2; exit 1; }
  tar xzf "$TMP/$repo.tar.gz" -C "$TMP"
  case "$repo" in
    obc40-home) sh "$TMP/$repo/install.sh" $HOME_OPTS ;;
    obc40-desk-player) sh "$TMP/$repo/install.sh" $DP_OPTS ;;
  esac
done

# --- start the apps now, if a graphical session is running
if [ -z "$DISPLAY" ]; then
  P=$(pgrep -u "$(id -un)" -x xfce4-session | head -1 || true)
  if [ -n "$P" ]; then
    eval "export $(tr '\0' '\n' < /proc/$P/environ | grep -E '^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=' \
      | sed 's/=\(.*\)/="\1"/' | tr '\n' ' ')"
  fi
fi
if [ -n "$DISPLAY" ]; then
  for repo in $APPS; do
    # already running (reinstall): close it so the new version starts
    case "$repo" in
      obc40-home) pkill -f "^python3 .*/obc-home\$" 2>/dev/null || true ;;
      obc40-desk-player) pkill -f "^python3 .*/desk-player\$" 2>/dev/null || true ;;
    esac
  done
  sleep 1
  for repo in $APPS; do
    case "$repo" in
      obc40-home)
        pgrep -f "^python3 .*/obc40-home/obc-fitwin" >/dev/null || (setsid "$HOME/.local/bin/obc-fitwin" >/dev/null 2>&1 </dev/null &)
        (setsid "$HOME/.local/bin/obc-home" >/dev/null 2>&1 </dev/null &) ;;
      obc40-desk-player)
        (setsid "$HOME/.local/bin/desk-player" >/dev/null 2>&1 </dev/null &) ;;
    esac
  done
  echo "== done: the apps are starting on the display"
else
  echo "== done: no graphical session found, the apps will be available at the next login"
fi
case " $APPS " in *" obc40-desk-player "*)
  echo "To connect Spotify: https://github.com/$OWNER/obc40-desk-player#connect-your-spotify-account-once" ;;
esac
