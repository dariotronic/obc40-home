"""Manual updates from GitHub Releases for the OBC40 apps (stdlib + GTK3 only).

The same file is shipped in every OBC40 repository (obc40-home, obc40-desk-player): keep the
copies identical.

Flow (always started by the user, never automatic):
  check()   -> asks the GitHub API for the latest release of the repo
  install() -> downloads <name>.tar.gz, verifies <name>.tar.gz.sha256, extracts it and runs
               its `install.sh --update` (which keeps the previous version as <dir>.prev)
  restart() -> relaunches the app through its wrapper in ~/.local/bin

The wrapper written by install.sh rolls back to <dir>.prev if the freshly updated app exits with an
error within 20 s (and leaves <dir>.rolledback, shown once by UpdateDialog.notify_rollback()); the
app calls confirm_started() once it has been running fine for 20 s.

For tests, OBC40_UPDATE_API=<url> replaces the GitHub API URL (a file:// JSON works too).
"""
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request

API = "https://api.github.com/repos/{repo}/releases/latest"
HEADERS = {"User-Agent": "obc40-updater", "Accept": "application/vnd.github+json"}


class UpdateError(Exception):
    pass


# ---------------------------------------------------------------- logic

def parse_version(v):
    """'v0.1.2' -> (0, 1, 2); unknown parts count as 0."""
    out = []
    for part in str(v).strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out + [0] * (3 - len(out)))


def read_version(app_dir):
    try:
        with open(os.path.join(app_dir, "VERSION")) as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise UpdateError("Non è ancora stata pubblicata nessuna versione.") from None
            if e.code == 403:
                raise UpdateError("GitHub ha rifiutato la richiesta (troppe richieste?): riprova più tardi.") from None
            raise UpdateError(f"Errore di GitHub ({e.code}).") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 2:
                raise UpdateError(f"Errore di rete: {getattr(e, 'reason', e)}. Controlla il Wi-Fi.") from None
            time.sleep(1 + attempt)


def check(repo, asset):
    """Latest release: dict(version, notes, url, sha_url, page)."""
    api = os.environ.get("OBC40_UPDATE_API") or API.format(repo=repo)
    try:
        data = json.loads(_get(api, timeout=20).decode())
    except ValueError:
        raise UpdateError("Risposta inattesa da GitHub.") from None
    assets = {a.get("name"): a.get("browser_download_url") for a in data.get("assets") or []}
    url, sha = assets.get(asset), assets.get(asset + ".sha256")
    if not url or not sha:
        raise UpdateError(f"L'ultima versione pubblicata non contiene il pacchetto {asset}.")
    return {"version": (data.get("tag_name") or "").lstrip("vV"), "notes": (data.get("body") or "").strip(),
            "url": url, "sha_url": sha, "page": data.get("html_url") or ""}


def is_newer(latest, current):
    return parse_version(latest) > parse_version(current)


def install(info, name):
    """Downloads, verifies and installs a release. Raises UpdateError on any problem."""
    data = _get(info["url"])
    expected = _get(info["sha_url"]).decode(errors="replace").split()[0].lower()
    if hashlib.sha256(data).hexdigest() != expected:
        raise UpdateError("Il file scaricato è danneggiato (checksum diverso).")
    tmp = tempfile.mkdtemp(prefix=f"{name}-update-")
    try:
        path = os.path.join(tmp, "pkg.tar.gz")
        with open(path, "wb") as f:
            f.write(data)
        with tarfile.open(path) as tar:
            for m in tar.getmembers():
                if m.name.startswith("/") or ".." in m.name.split("/"):
                    raise UpdateError("Il pacchetto contiene percorsi non sicuri: aggiornamento rifiutato.")
            tar.extractall(tmp, filter="data")
        src = os.path.join(tmp, name)
        if not os.path.isfile(os.path.join(src, "install.sh")):
            raise UpdateError("Nel pacchetto manca install.sh.")
        r = subprocess.run(["sh", "install.sh", "--update"], cwd=src, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise UpdateError("Installazione non riuscita: " + (r.stderr or r.stdout).strip()[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def marker_path(name):
    return os.path.expanduser(f"~/.local/share/{name}.updated")


def confirm_started(name):
    """Called by the app after it has been running fine: the update is kept."""
    try:
        os.remove(marker_path(name))
    except OSError:
        pass
    return False


def rollback_notice(name):
    """If the launcher had to restore the previous version, returns the version that failed (once)."""
    path = os.path.expanduser(f"~/.local/share/{name}.rolledback")
    try:
        with open(path) as f:
            failed = f.read().strip() or "?"
        os.remove(path)
        return failed
    except OSError:
        return None


def restart(wrapper, delay=1.0):
    """Relaunches the app (detached) through its wrapper; the caller must then quit."""
    subprocess.Popen(["sh", "-c", f'sleep {delay}; exec "{wrapper}"'], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


# ---------------------------------------------------------------- touch-friendly dialog (GTK3)

def _css(accent):
    return f"""
.upd-shade {{ background-color: rgba(0, 0, 0, 0.6); }}
.upd-card {{ background-color: #1b1d23; border-radius: 16px; padding: 20px; }}
.upd-title {{ font-size: 19px; font-weight: bold; color: #ffffff; }}
.upd-text {{ font-size: 15px; color: #c8ccd4; }}
.upd-small {{ font-size: 13px; color: #9aa0aa; }}
button.upd-btn {{ background-color: #23262d; background-image: none; border: none; border-radius: 12px;
                  box-shadow: none; color: #ffffff; padding: 10px 18px; font-size: 16px; }}
button.upd-btn.primary {{ background-color: {accent}; color: #101114; }}
""".encode()


class UpdateDialog:
    """In-window modal (an overlay, not a separate window: on XFCE a separate dialog would make the
    panels pop up over a fullscreen app). User-facing texts are Italian, like the rest of the UI."""

    _css_done = set()

    def __init__(self, overlay, name, repo, app_dir, wrapper, quit_cb, accent="#ffb547"):
        from gi.repository import Gdk, Gtk  # noqa: F401  (imported lazily: logic works without GTK)
        self.Gtk, self.GLib = Gtk, __import__("gi.repository.GLib", fromlist=["GLib"])
        self.overlay, self.name, self.repo = overlay, name, repo
        self.app_dir, self.wrapper, self.quit_cb = app_dir, wrapper, quit_cb
        if accent not in UpdateDialog._css_done:
            prov = Gtk.CssProvider()
            prov.load_from_data(_css(accent))
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)
            UpdateDialog._css_done.add(accent)
        self.shade = None

    # -- building blocks
    def _open(self):
        Gtk = self.Gtk
        self.close()
        self.shade = Gtk.EventBox()
        self.shade.get_style_context().add_class("upd-shade")
        card_ev = Gtk.EventBox(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        card_ev.connect("button-release-event", lambda *_: True)
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.card.get_style_context().add_class("upd-card")
        self.card.set_size_request(460, -1)
        card_ev.add(self.card)
        self.shade.add(card_ev)
        self.shade.connect("button-release-event", lambda *_: (self.close(), True)[1] if self.closable else True)
        self.overlay.add_overlay(self.shade)
        self.closable = True

    def close(self):
        if self.shade is not None:
            self.shade.destroy()
            self.shade = None

    def _label(self, text, cls, wrap=True):
        lab = self.Gtk.Label(label=text, xalign=0)
        lab.get_style_context().add_class(cls)
        lab.set_line_wrap(wrap)
        lab.set_max_width_chars(48)
        return lab

    def _buttons(self, *specs):
        Gtk = self.Gtk
        row = Gtk.Box(spacing=10, halign=Gtk.Align.END)
        for text, cb, primary in specs:
            b = Gtk.Button(label=text)
            b.get_style_context().add_class("upd-btn")
            if primary:
                b.get_style_context().add_class("primary")
            b.connect("clicked", lambda *_a, cb=cb: cb())
            row.pack_start(b, False, False, 0)
        self.card.pack_start(row, False, False, 4)

    def _busy(self, title):
        Gtk = self.Gtk
        self._open()
        self.closable = False
        row = Gtk.Box(spacing=14)
        sp = Gtk.Spinner()
        sp.start()
        sp.set_size_request(28, 28)
        row.pack_start(sp, False, False, 0)
        row.pack_start(self._label(title, "upd-title"), True, True, 0)
        self.card.pack_start(row, False, False, 0)
        self.shade.show_all()

    def _message(self, title, text=""):
        self._open()
        self.card.pack_start(self._label(title, "upd-title"), False, False, 0)
        if text:
            self.card.pack_start(self._label(text, "upd-text"), False, False, 0)
        self._buttons(("OK", self.close, True))
        self.shade.show_all()

    def _bg(self, fn, done, fail):
        GLib = self.GLib

        def work():
            try:
                res = fn()
            except Exception as e:  # noqa: BLE001
                GLib.idle_add(lambda err=e: fail(err) and False)
                return
            GLib.idle_add(lambda r=res: done(r) and False)
        threading.Thread(target=work, daemon=True).start()

    # -- flow
    def notify_rollback(self):
        """To call at startup: tells the user if a failed update was undone."""
        failed = rollback_notice(self.name)
        if failed:
            self._message("Aggiornamento annullato",
                          f"La versione {failed} non si è avviata: è stata ripristinata la versione "
                          f"{read_version(self.app_dir)}.")
        return False

    def start(self):
        current = read_version(self.app_dir)
        self._busy("Controllo aggiornamenti…")
        self._bg(lambda: check(self.repo, f"{self.name}.tar.gz"),
                 lambda info: self._checked(info, current),
                 lambda e: self._message("Impossibile controllare gli aggiornamenti", self._err(e)))

    @staticmethod
    def _err(e):
        return str(e) or e.__class__.__name__

    def _checked(self, info, current):
        if not is_newer(info["version"], current):
            self._message("Sei aggiornato", f"Versione installata: {current}")
            return
        Gtk = self.Gtk
        self._open()
        self.card.pack_start(self._label(f"Nuova versione {info['version']}", "upd-title"), False, False, 0)
        self.card.pack_start(self._label(f"Installata: {current}", "upd-small"), False, False, 0)
        if info["notes"]:
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_min_content_height(60)
            sw.set_max_content_height(220)
            sw.set_propagate_natural_height(True)
            sw.add(self._label(info["notes"], "upd-text"))
            self.card.pack_start(sw, False, False, 0)
        self._buttons(("Annulla", self.close, False), ("Aggiorna", lambda: self._install(info), True))
        self.shade.show_all()

    def _install(self, info):
        self._busy(f"Installo la versione {info['version']}…")
        self._bg(lambda: install(info, self.name), lambda _r: self._installed(info),
                 lambda e: self._message("Aggiornamento non riuscito", self._err(e)
                                         + "\nLa versione installata non è cambiata."))

    def _installed(self, info):
        self._busy(f"Aggiornato alla {info['version']}. Riavvio…")
        restart(self.wrapper)
        self.GLib.timeout_add(600, lambda: self.quit_cb() and False)
