# Source it in an SSH shell on the board (". dev/env.sh") to talk to the running graphical session.
P=$(pgrep -u "$(id -un)" -x xfce4-session | head -1)
eval "export $(tr '\0' '\n' < /proc/$P/environ | grep -E '^(DBUS_SESSION_BUS_ADDRESS|DISPLAY|XAUTHORITY|LD_PRELOAD|LANG)=' | sed 's/=\(.*\)/="\1"/' | tr '\n' ' ')"
