#!/bin/sh
# Screenshot of the display into /tmp/shot.png (run on the board as the desktop user).
. "$(dirname "$0")/env.sh"
python3 -c '
import gi; gi.require_version("Gdk","3.0"); from gi.repository import Gdk
w=Gdk.get_default_root_window(); pb=Gdk.pixbuf_get_from_window(w,0,0,w.get_width(),w.get_height()); pb.savev("/tmp/shot.png","png",[],[])'
