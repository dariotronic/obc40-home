"""Icone dei siti web per i riquadri della home: cerca l'icona più grande dichiarata dalla pagina
(apple-touch-icon, <link rel="icon" sizes=...>), altrimenti /favicon.ico, e la salva in PNG nella cache."""
import base64
import hashlib
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

CACHE = os.path.expanduser("~/.cache/obc-home/icons")
UA = "Mozilla/5.0 (X11; Linux aarch64) obc-home"
SIZE = 128          # lato massimo dell'icona salvata


def normalize(url):
    """URL completo a partire da quello che scrive l'utente ("example.com" -> "https://example.com/")."""
    url = url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    p = urllib.parse.urlsplit(url)
    if not p.netloc or "." not in p.netloc and p.hostname != "localhost":
        return None
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, p.fragment))


def site_name(url):
    host = urllib.parse.urlsplit(url).hostname or url
    return host[4:] if host.startswith("www.") else host


def cache_path(url):
    key = hashlib.sha1((urllib.parse.urlsplit(url).netloc or url).encode()).hexdigest()[:16]
    return os.path.join(CACHE, key + ".png")


def cached(url):
    p = cache_path(url)
    return p if os.path.exists(p) else None


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.icons = []      # (dimensione stimata, href)

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = dict(attrs)
        rel = (a.get("rel") or "").lower().split()
        href = a.get("href")
        if not href or not any(r in ("icon", "apple-touch-icon", "apple-touch-icon-precomposed") for r in rel):
            return
        size = 0
        for s in (a.get("sizes") or "").lower().split():
            if s == "any":
                size = max(size, 512)
            elif "x" in s:
                try:
                    size = max(size, int(s.split("x")[0]))
                except ValueError:
                    pass
        if not size:
            size = 180 if "apple-touch-icon" in " ".join(rel) else 32
        if href.lower().split("?")[0].endswith(".svg") or (a.get("type") or "").endswith("svg+xml"):
            size = max(size, 256)
        self.icons.append((size, href))


def _get(url, limit):
    if url.startswith("data:"):
        head, _, data = url.partition(",")
        return (base64.b64decode(data) if ";base64" in head else urllib.parse.unquote_to_bytes(data)), url
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read(limit), r.geturl()


def _pixbuf(data):
    loader = GdkPixbuf.PixbufLoader()
    loader.write(data)
    loader.close()
    pb = loader.get_pixbuf()
    if pb is None or pb.get_width() < 16:
        return None
    if max(pb.get_width(), pb.get_height()) > SIZE:
        k = SIZE / max(pb.get_width(), pb.get_height())
        pb = pb.scale_simple(max(1, round(pb.get_width() * k)), max(1, round(pb.get_height() * k)),
                             GdkPixbuf.InterpType.HYPER)
    return pb


def fetch(url):
    """Scarica l'icona del sito e la salva nella cache. Restituisce il percorso del PNG o None."""
    candidates = []
    base = url
    try:
        html, base = _get(url, 600_000)
        p = _Links()
        p.feed(html.decode("utf-8", errors="replace"))
        candidates = sorted(p.icons, key=lambda c: -c[0])
    except Exception:
        pass
    urls = [urllib.parse.urljoin(base, h) for _, h in candidates]
    urls.append(urllib.parse.urljoin(base, "/favicon.ico"))
    for u in dict.fromkeys(urls):
        try:
            data, _ = _get(u, 2_000_000)
            pb = _pixbuf(data)
        except Exception:
            continue
        if pb is not None:
            os.makedirs(CACHE, exist_ok=True)
            path = cache_path(url)
            pb.savev(path + ".tmp", "png", [], [])
            os.replace(path + ".tmp", path)
            return path
    return None
