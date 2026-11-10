"""Strumento di test per il display: tocchi simulati (XTest) e screenshot.

uso: python3 uitool.py tap X Y [X Y ...]   (pausa di 0,6 s tra un tocco e l'altro)
     python3 uitool.py shot /tmp/s.jpg [larghezza]
Va lanciato con DISPLAY/XAUTHORITY della sessione (. dev/env.sh).
"""
import ctypes
import sys
import time


def tap(points):
    x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
    xt = ctypes.cdll.LoadLibrary("libXtst.so.6")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    d = x11.XOpenDisplay(None)
    if not d:
        raise SystemExit("display non disponibile")
    d = ctypes.c_void_p(d)
    for x, y in points:
        xt.XTestFakeMotionEvent(d, -1, int(x), int(y), 0)
        xt.XTestFakeButtonEvent(d, 1, 1, 0)
        x11.XFlush(d)
        time.sleep(0.08)
        xt.XTestFakeButtonEvent(d, 1, 0, 0)
        x11.XFlush(d)
        time.sleep(0.6)
    x11.XCloseDisplay(d)


def shot(path, width=None):
    import gi
    gi.require_version("Gdk", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import Gdk, GdkPixbuf
    w = Gdk.get_default_root_window()
    pb = Gdk.pixbuf_get_from_window(w, 0, 0, w.get_width(), w.get_height())
    if width and int(width) < pb.get_width():
        h = pb.get_height() * int(width) // pb.get_width()
        pb = pb.scale_simple(int(width), h, GdkPixbuf.InterpType.BILINEAR)
    pb.savev(path, "jpeg", ["quality"], ["80"])


if __name__ == "__main__":
    if sys.argv[1] == "tap":
        v = list(map(int, sys.argv[2:]))
        tap(list(zip(v[::2], v[1::2])))
    elif sys.argv[1] == "shot":
        shot(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
