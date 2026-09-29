"""Dashboard (alleen op je eigen computer): meldingen lezen, ideeën goedkeuren, video's ophalen.

Na 'Akkoord' maakt een achtergrondproces de video meteen. Dat is gewone code
(ffmpeg), dus het kost geen Claude-gebruik en geen geld.
"""

from __future__ import annotations

import json
import queue
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import inbox, productie, werk

WACHTRIJ: "queue.Queue[str]" = queue.Queue()
HTML = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


def werker() -> None:
    while True:
        vid = WACHTRIJ.get()
        try:
            productie.maak(vid)
        finally:
            WACHTRIJ.task_done()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # stil
        pass

    def _json(self, data, code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/staat":
            cfg_talen = productie.config().get("talen", {})
            self._json({
                "meldingen": inbox.meldingen(5), "voorstellen": inbox.alle(), "telling": inbox.telling(),
                "talen": {k: v.get("label", k) for k, v in cfg_talen.items()},
                "accounts": {k: v.get("account", "") for k, v in cfg_talen.items()},
            })
        elif self.path.startswith("/video/"):
            self._video(self.path[len("/video/"):].split("?")[0])
        else:
            self._json({"fout": "niet gevonden"}, 404)

    def _video(self, vid: str) -> None:
        try:
            v = inbox.lees(vid)
            pad = (werk.ROOT / v["map"] / "video.mp4").resolve()
            pad.relative_to(werk.OUTPUT.resolve())
        except Exception:
            return self._json({"fout": "video niet gevonden"}, 404)
        grootte = pad.stat().st_size
        start, eind = 0, grootte - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m:
            if m.group(1):
                start = int(m.group(1))
                eind = int(m.group(2)) if m.group(2) else eind
            elif m.group(2):
                start = grootte - int(m.group(2))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{eind}/{grootte}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(eind - start + 1))
        self.end_headers()
        with pad.open("rb") as f:
            f.seek(start)
            over = eind - start + 1
            while over > 0:
                stuk = f.read(min(1 << 20, over))
                if not stuk:
                    break
                try:
                    self.wfile.write(stuk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                over -= len(stuk)

    def do_POST(self):
        m = re.fullmatch(r"/api/(akkoord|afwijzen|geplaatst|views|opnieuw|terug)/([^/]+)", self.path)
        if not m:
            return self._json({"fout": "onbekende actie"}, 404)
        actie, vid = m.groups()
        lengte = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(lengte) or b"{}") if lengte else {}
        try:
            v = inbox.lees(vid)
        except (OSError, ValueError):
            return self._json({"fout": "voorstel niet gevonden"}, 404)

        if actie == "akkoord" and v["status"] in ("idee", "afgewezen"):
            wijzig = {k: str(body[k]).strip() for k in ("hook", "titel") if body.get(k)}
            inbox.zet(vid, status="akkoord", **wijzig)
            WACHTRIJ.put(vid)
        elif actie == "opnieuw" and v["status"] in ("fout", "klaar"):
            inbox.zet(vid, status="akkoord")
            WACHTRIJ.put(vid)
        elif actie == "afwijzen" and v["status"] == "idee":
            inbox.zet(vid, status="afgewezen", afwijsreden=str(body.get("reden", ""))[:300])
        elif actie == "terug" and v["status"] == "afgewezen":
            inbox.zet(vid, status="idee")
        elif actie == "geplaatst" and v["status"] == "klaar":
            inbox.zet(vid, status="geplaatst", link=str(body.get("link", ""))[:500], geplaatst_op=inbox.nu())
        elif actie == "views" and v["status"] == "geplaatst":
            try:
                views = int(str(body.get("views", "")).replace(".", "").replace(",", ""))
            except ValueError:
                return self._json({"fout": "views moet een getal zijn"}, 400)
            inbox.zet(vid, views=views, views_op=inbox.nu())
        else:
            return self._json({"fout": f"'{actie}' kan niet bij status '{v['status']}'"}, 409)
        return self._json({"ok": True, "voorstel": inbox.lees(vid)})


def start(poort: int, browser: bool = True) -> None:
    for v in inbox.alle():  # onderbroken werk weer oppakken
        if v.get("status") in ("akkoord", "bezig"):
            WACHTRIJ.put(v["id"])
    threading.Thread(target=werker, daemon=True).start()
    url = f"http://127.0.0.1:{poort}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", poort), Handler)
    except OSError:
        print(f"Dashboard draait al op {url}")
        if browser:
            webbrowser.open(url)
        return
    print(f"Dashboard: {url}   (stoppen: Ctrl+C)")
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGestopt.")
