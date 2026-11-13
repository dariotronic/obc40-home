"""Icone e nomi dei siti web per i riquadri della home: cerca l'icona più grande dichiarata dalla pagina
(apple-touch-icon, <link rel="icon" sizes=...>), altrimenti /favicon.ico, e la salva in PNG nella cache;
il nome viene da og:site_name, application-name o dal titolo della pagina."""
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


def cached_name(url):
    """Nome del sito salvato in cache, o None."""
    try:
        with open(cache_path(url)[:-4] + ".name", encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def _title_name(title, url):
    """Dal titolo della pagina ("Notizie - Il Sito") tiene la parte che somiglia all'indirizzo."""
    parts = [p.strip() for p in re.split(r"\s[|\-–—·:]\s|:\s", title) if p.strip()]
    if not parts:
        return None
    host = re.sub(r"[^a-z0-9]", "", site_name(url).rsplit(".", 1)[0].lower())
    for p in parts:
        key = re.sub(r"[^a-z0-9]", "", p.lower())
        if key and (key in host or host in key):
            return p
    return parts[0] if len(parts[0]) <= 30 else None


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.icons = []      # (dimensione stimata, href)
        self.names = {}      # og:site_name / application-name / apple-mobile-web-app-title
        self.title = ""
        self._in_title = False

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title" and not self.title:
            self._in_title = True
            return
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:site_name", "application-name", "apple-mobile-web-app-title") and a.get("content"):
                self.names.setdefault(key, a["content"].strip())
            return
        if tag != "link":
            return
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
    """Scarica icona e nome del sito e li salva nella cache. Restituisce il percorso del PNG o None."""
    candidates = []
    base = url
    try:
        html, base = _get(url, 600_000)
        p = _Links()
        p.feed(html.decode("utf-8", errors="replace"))
        candidates = sorted(p.icons, key=lambda c: -c[0])
        name = (p.names.get("og:site_name") or p.names.get("application-name")
                or p.names.get("apple-mobile-web-app-title") or _title_name(" ".join(p.title.split()), url))
        if name:
            os.makedirs(CACHE, exist_ok=True)
            with open(cache_path(url)[:-4] + ".name", "w", encoding="utf-8") as f:
                f.write(name[:40] + "\n")
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
