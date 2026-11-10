#!/bin/sh
# obc40-home installer: installs the launcher for the current user (no root needed).
#
#   sh install.sh                  first install: app, menu entry, autostart of home + window fitter
#   sh install.sh --no-autostart   same, but nothing starts automatically at login
#   sh install.sh --update         used by the in-app updater: replaces the app files only
#
# Files: ~/.local/share/obc40-home/ (app), ~/.local/share/obc40-home.prev/ (previous version),
#        ~/.local/bin/obc-home and ~/.local/bin/obc-fitwin (wrappers).
set -e
NAME=obc40-home
SRC=$(cd "$(dirname "$0")" && pwd)
DEST="$HOME/.local/share/$NAME"
BIN="$HOME/.local/bin"
UPDATE=0
AUTOSTART=1
for a in "$@"; do
  case "$a" in
    --update) UPDATE=1 ;;
    --no-autostart) AUTOSTART=0 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done
[ "$SRC" != "$DEST" ] || { echo "run install.sh from the downloaded package, not from $DEST" >&2; exit 1; }

# --- requirements
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null || {
  echo "Missing Python GTK3. Install it as root and run again:  apk add py3-gobject3 gtk+3.0" >&2; exit 1; }
if ! python3 -c 'import gi; gi.require_version("Wnck", "3.0"); from gi.repository import Wnck' 2>/dev/null; then
  echo "note: libwnck3 not found, obc-fitwin (auto-maximise oversized windows) will not run (apk add libwnck3)"
fi

# --- app files: new copy, then swap (the previous version stays in $DEST.prev)
rm -rf "$DEST.new"
mkdir -p "$DEST.new"
cp -R "$SRC/." "$DEST.new/"
rm -rf "$DEST.new/.git" "$DEST.new/__pycache__"
chmod 755 "$DEST.new/obc-home" "$DEST.new/obc-fitwin"
if [ -d "$DEST" ]; then
  rm -rf "$DEST.prev"
  mv "$DEST" "$DEST.prev"
fi
mv "$DEST.new" "$DEST"
if [ "$UPDATE" = 1 ]; then
  touch "$DEST.updated"   # removed by the app once it has run fine for 20 s
else
  rm -f "$DEST.updated"
fi

# --- wrappers: faccessat-fix on kernels < 5.8, rollback if an update crashes at start
mkdir -p "$BIN"
cat > "$BIN/obc-home" <<'EOF'
#!/bin/sh
# obc40-home launcher (written by install.sh)
D="$HOME/.local/share/obc40-home"
K=$(uname -r); KMAJ=${K%%.*}; KMIN=${K#*.}; KMIN=${KMIN%%.*}
if [ "$KMAJ" -lt 5 ] || { [ "$KMAJ" -eq 5 ] && [ "$KMIN" -lt 8 ]; }; then
  export LD_PRELOAD="$D/faccessat-fix/faccessat-fix.so${LD_PRELOAD:+:$LD_PRELOAD}"
fi
start=$(date +%s)
python3 "$D/obc-home" "$@"
rc=$?
if [ "$rc" -ne 0 ] && [ -f "$D.updated" ] && [ -d "$D.prev" ] && [ $(( $(date +%s) - start )) -lt 20 ]; then
  echo "obc40-home: the update did not start, going back to the previous version" >&2
  cat "$D/VERSION" > "$D.rolledback" 2>/dev/null
  rm -rf "$D.failed"; mv "$D" "$D.failed" && mv "$D.prev" "$D"; rm -f "$D.updated"
  exec "$0" "$@"
fi
exit $rc
EOF
cat > "$BIN/obc-fitwin" <<'EOF'
#!/bin/sh
# obc40-home window fitter (written by install.sh)
exec python3 "$HOME/.local/share/obc40-home/obc-fitwin" "$@"
EOF
chmod 755 "$BIN/obc-home" "$BIN/obc-fitwin"

if [ "$UPDATE" = 0 ]; then
  mkdir -p "$HOME/.local/share/applications" "$HOME/.config/autostart"
  cat > "$HOME/.local/share/applications/obc-home.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Home
Comment=Schermata principale
Exec=$BIN/obc-home
Icon=go-home
Terminal=false
Categories=Utility;
EOF
  if [ "$AUTOSTART" = 1 ]; then
    cp "$HOME/.local/share/applications/obc-home.desktop" "$HOME/.config/autostart/obc-home.desktop"
    printf '[Desktop Entry]\nType=Application\nName=Adatta finestre\nExec=%s/obc-fitwin\nNoDisplay=true\n' "$BIN" \
      > "$HOME/.config/autostart/obc-fitwin.desktop"
  fi
fi

echo "obc40-home $(cat "$DEST/VERSION") installed in $DEST"
[ "$UPDATE" = 1 ] || echo "Start it with: $BIN/obc-home  (it also starts at the next login)"
