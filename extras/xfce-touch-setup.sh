#!/bin/sh
# Optional: makes XFCE touch-friendly on the OBC40 1024x600 display (what the obc40-home author uses):
# dark theme, Papirus icons, Monospace 10 at 110 DPI, bigger panels with a "Home" launcher in the dock,
# dark gradient wallpaper, Italian keyboard, on-screen keyboard (onboard) docked at the bottom.
# Run it as the desktop user, inside or outside the graphical session (e.g. via SSH):
#     sh extras/xfce-touch-setup.sh
# It changes your XFCE settings: read it first. Recommended packages: papirus-icon-theme setxkbmap.
set -e
H=$HOME
U=$(id -un)

# attach to the running graphical session
PID=$(pgrep -u "$U" -x xfce4-session | head -1)
[ -n "$PID" ] || { echo "no running XFCE session for $U"; exit 1; }
eval "export $(tr '\0' '\n' < /proc/$PID/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|DISPLAY|XAUTHORITY)=' | sed 's/=\(.*\)/="\1"/' | tr '\n' ' ')"
X() { xfconf-query "$@"; }
XS() { ch=$1; p=$2; t=$3; v=$4; xfconf-query -c "$ch" -p "$p" -n -t "$t" -s "$v" 2>/dev/null || xfconf-query -c "$ch" -p "$p" -s "$v"; }

echo "== tema, icone, font"
if [ -d /usr/share/icons/Papirus-Dark ]; then XS xsettings /Net/IconThemeName string Papirus-Dark; fi
XS xsettings /Gtk/FontName string "Monospace 10"
XS xsettings /Xft/DPI int 110
XS xsettings /Xft/Antialias int 1
XS xsettings /Xft/HintStyle string hintslight
XS xsettings /Xft/RGBA string rgb
XS xfwm4 /general/theme string Default-hdpi
XS xfwm4 /general/title_font string "Monospace Bold 10"
XS xfce4-panel /panels/dark-mode bool true

echo "== tastiera italiana"
XS keyboard-layout /Default/XkbDisable bool false
XS keyboard-layout /Default/XkbLayout string it
XS keyboard-layout /Default/XkbVariant string ""

echo "== pannelli"
XS xfce4-panel /panels/panel-1/size uint 40
XS xfce4-panel /panels/panel-1/icon-size uint 24
XS xfce4-panel /panels/panel-2/size uint 64
XS xfce4-panel /panels/panel-2/icon-size uint 0
XS xfce4-panel /plugins/plugin-2/show-labels bool false
# lanciatore "Home" all'inizio del dock (una volta sola)
if ! grep -rqs "obc-home" $H/.config/xfce4/panel/launcher-*/ 2>/dev/null; then
  N=$(X -c xfce4-panel -l | sed -n 's|^/plugins/plugin-\([0-9]*\)$|\1|p' | sort -n | tail -1)
  N=$((N + 1))
  XS xfce4-panel /plugins/plugin-$N string launcher
  mkdir -p $H/.config/xfce4/panel/launcher-$N
  cp $H/.local/share/applications/obc-home.desktop $H/.config/xfce4/panel/launcher-$N/obc-home.desktop
  X -c xfce4-panel -p /plugins/plugin-$N/items -n -t string -s obc-home.desktop -a
  set -- $(X -c xfce4-panel -p /panels/panel-2/plugin-ids | grep -E '^[0-9]+$')
  ARGS="-t int -s $N"
  for id in "$@"; do ARGS="$ARGS -t int -s $id"; done
  X -c xfce4-panel -p /panels/panel-2/plugin-ids $ARGS -a
fi

# lanciatori del dock rimasti vuoti (Alpine non crea quelli predefiniti)
i=0
for id in $(X -c xfce4-panel -p /panels/panel-2/plugin-ids | grep -E '^[0-9]+$'); do
  [ "$(X -c xfce4-panel -p /plugins/plugin-$id 2>/dev/null)" = launcher ] || continue
  items=$(X -c xfce4-panel -p /plugins/plugin-$id/items 2>/dev/null | grep -c desktop || true)
  [ "$items" -gt 0 ] && continue
  i=$((i + 1))
  case $i in
    1) app=xfce4-terminal.desktop ;;
    2) app=thunar.desktop ;;
    3) app=xfce-settings-manager.desktop ;;
    4) app=nm-connection-editor.desktop ;;
    *) continue ;;
  esac
  mkdir -p $H/.config/xfce4/panel/launcher-$id
  cp /usr/share/applications/$app $H/.config/xfce4/panel/launcher-$id/
  X -c xfce4-panel -p /plugins/plugin-$id/items -n -t string -s $app -a 2>/dev/null || \
    X -c xfce4-panel -p /plugins/plugin-$id/items -t string -s $app -a
done

# tema scuro per tutte le app GTK3 (Adwaita, variante scura)
mkdir -p $H/.config/gtk-3.0
printf '[Settings]\ngtk-application-prefer-dark-theme=1\n' > $H/.config/gtk-3.0/settings.ini
XS xsettings /Net/ThemeName string Adwaita

echo "== sfondo"
for mon in $(xrandr --listmonitors | awk 'NR>1 {print $NF}'); do
  b=/backdrop/screen0/monitor$mon/workspace0
  XS xfce4-desktop $b/image-style int 0
  XS xfce4-desktop $b/color-style int 1
  X -c xfce4-desktop -p $b/rgba1 -n -t double -s 0.063 -t double -s 0.067 -t double -s 0.078 -t double -s 1 2>/dev/null || \
    X -c xfce4-desktop -p $b/rgba1 -t double -s 0.063 -t double -s 0.067 -t double -s 0.078 -t double -s 1
  X -c xfce4-desktop -p $b/rgba2 -n -t double -s 0.16 -t double -s 0.12 -t double -s 0.07 -t double -s 1 2>/dev/null || \
    X -c xfce4-desktop -p $b/rgba2 -t double -s 0.16 -t double -s 0.12 -t double -s 0.07 -t double -s 1
done
XS xfce4-desktop /desktop-icons/icon-size uint 56
XS xfce4-desktop /desktop-icons/file-icons/show-filesystem bool false

echo "== tastiera a schermo"
gsettings set org.onboard layout '/usr/share/onboard/layouts/Compact.onboard'
gsettings set org.onboard theme '/usr/share/onboard/themes/Nightshade.theme'
gsettings set org.onboard key-label-font 'Monospace'
gsettings set org.onboard start-minimized true
gsettings set org.onboard show-status-icon true
gsettings set org.onboard.auto-show enabled true
gsettings set org.onboard.window docking-enabled true
gsettings set org.onboard.window docking-edge 'bottom'
gsettings set org.onboard.window docking-shrink-workarea false
gsettings set org.onboard.window force-to-top true
gsettings set org.gnome.desktop.interface toolkit-accessibility true 2>/dev/null || true

echo "== riavvio componenti"
xfce4-panel -r || true
xfdesktop --reload || true
pkill -x onboard || true
sleep 1
(setsid onboard >/dev/null 2>&1 &)
echo "done"
