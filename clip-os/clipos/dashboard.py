"""Clip-OS in je browser: de werkomgeving op http://127.0.0.1:<poort>.

- Alleen bereikbaar vanaf je eigen computer (127.0.0.1).
- Elke actie vereist een geheime sleutel die alleen deze pagina kent, zodat
  andere websites in je browser niets kunnen starten of wijzigen.
- Na 'Akkoord' maakt een achtergrondproces de video (ffmpeg, gratis).
- Claude-taken (/video, /dagelijks, /campagne) draaien op je Pro-login.
"""

from __future__ import annotations

import json
import queue
import re
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import bijwerken, claude_taken, inbox, kostenwacht, opslag, productie, views, werk

WEB = Path(__file__).parent / "web"
SLEUTEL = secrets.token_urlsafe(24)
WACHTRIJ: "queue.Queue[str]" = queue.Queue()
STATISCH = {"/app.css": ("app.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "application/javascript; charset=utf-8")}
WHISPER_MODELLEN = ["tiny", "base", "small", "medium", "large-v3"]


def werker() -> None:
    while True:
        vid = WACHTRIJ.get()
        try:
            productie.maak(vid)
        finally:
            WACHTRIJ.task_done()


# ---------- campagnes en instellingen ----------

def _tekstlijst(waarde, naam: str) -> list[str]:
    if isinstance(waarde, str):
        waarde = [x.strip() for x in re.split(r"[\n,]", waarde)]
    if not isinstance(waarde, list):
        raise ValueError(f"'{naam}' moet een lijst zijn")
    return [str(x).strip() for x in waarde if str(x).strip()][:50]


def valideer_brief(b: dict) -> dict:
    def geheel(naam, lo, hi, standaard):
        try:
            n = int(b.get(naam, standaard))
        except (TypeError, ValueError):
            raise ValueError(f"'{naam}' moet een getal zijn")
        if not lo <= n <= hi:
            raise ValueError(f"'{naam}' moet tussen {lo} en {hi} liggen")
        return n

    uit = {
        "naam": str(b.get("naam", "")).strip()[:120],
        "actief": bool(b.get("actief", True)),
        "platform": str(b.get("platform", "")).strip()[:60],
        "cpm": str(b.get("cpm", "")).strip()[:120],
        "taal": str(b.get("taal", "")).strip().lower()[:5],
        "min_seconden": geheel("min_seconden", 5, 170, 15),
        "max_seconden": geheel("max_seconden", 10, 180, 60),
        "verplichte_hashtags": _tekstlijst(b.get("verplichte_hashtags", []), "verplichte_hashtags"),
        "verplichte_tekst": _tekstlijst(b.get("verplichte_tekst", []), "verplichte_tekst"),
        "verboden": _tekstlijst(b.get("verboden", []), "verboden"),
        "bron_kanalen": _tekstlijst(b.get("bron_kanalen", []), "bron_kanalen"),
        "bron_links": _tekstlijst(b.get("bron_links", []), "bron_links"),
        "indienen": str(b.get("indienen", "")).strip()[:500],
        "notities": str(b.get("notities", "")).strip()[:2000],
    }
    if not uit["naam"]:
        raise ValueError("Geef de campagne een naam")
    if not re.fullmatch(r"[a-z]{2,3}", uit["taal"]):
        raise ValueError("Kies een taal (bijv. en of nl)")
    if uit["min_seconden"] >= uit["max_seconden"]:
        raise ValueError("Minimale lengte moet kleiner zijn dan de maximale")
    for url in uit["bron_kanalen"] + uit["bron_links"]:
        if not re.fullmatch(r"https?://\S+", url):
            raise ValueError(f"Geen geldige link: {url}")
    return uit


def briefs_lijst() -> list[dict]:
    uit = []
    for pad in sorted(werk.BRIEFS.glob("*.json")):
        try:
            b = werk.lees_json(pad)
        except (json.JSONDecodeError, OSError):
            continue
        links = b.get("bron_kanalen", []) + b.get("bron_links", [])
        uit.append({
            **b, "bestand": pad.stem, "voorbeeld": pad.stem.startswith("voorbeeld"),
            "geblokkeerde_bronnen": [u for u in links if not kostenwacht.host_toegestaan(urlparse(u).hostname or "")],
        })
    return uit


def valideer_config(nieuw: dict) -> dict:
    cfg = productie.config()
    try:
        cfg["max_ideeen_per_bron"] = max(1, min(12, int(nieuw.get("max_ideeen_per_bron", cfg["max_ideeen_per_bron"]))))
    except (TypeError, ValueError):
        raise ValueError("Max ideeën moet een getal zijn")
    model = nieuw.get("whisper_model", cfg["whisper_model"])
    if model not in WHISPER_MODELLEN:
        raise ValueError("Onbekend spraakmodel")
    cfg["whisper_model"] = model
    talen = {}
    for code, t in (nieuw.get("talen") or cfg.get("talen", {})).items():
        if not re.fullmatch(r"[a-z]{2,3}", code):
            raise ValueError(f"Ongeldige taalcode: {code}")
        try:
            maximum = max(0, min(5, int(t.get("max_nieuwe_bronnen_per_dag", 1))))
        except (TypeError, ValueError):
            raise ValueError("Max per dag moet een getal zijn")
        talen[code] = {
            "label": str(t.get("label", code)).strip()[:40] or code,
            "account": str(t.get("account", "")).strip()[:120],
            "max_nieuwe_bronnen_per_dag": maximum,
        }
    cfg["talen"] = talen
    m = {**werk.MONTAGE_STANDAARD, **(cfg.get("montage") or {}), **(nieuw.get("montage") or {})}
    try:
        max_stilte = round(max(0.2, min(1.5, float(m["max_stilte"]))), 2)
    except (TypeError, ValueError):
        raise ValueError("Max. stilte moet een getal zijn (bijv. 0.4)")
    cfg["montage"] = {"stiltes_eruit": bool(m["stiltes_eruit"]), "max_stilte": max_stilte,
                      "zoom": bool(m["zoom"]), "split_screen": bool(m["split_screen"])}
    o = {**werk.OPSLAG_STANDAARD, **(cfg.get("opslag") or {}), **(nieuw.get("opslag") or {})}
    try:
        cfg["opslag"] = {"automatisch": bool(o["automatisch"]),
                         "geplaatst_dagen": max(0, min(60, int(float(o["geplaatst_dagen"])))),
                         "bron_dagen": max(1, min(90, int(float(o["bron_dagen"]))))}
    except (TypeError, ValueError):
        raise ValueError("Het aantal dagen bij Opslag moet een getal zijn")
    return cfg


def kostenwacht_status() -> dict:
    return {
        "sleutels": kostenwacht.controleer_sleutels(),
        "code": kostenwacht.scan_code(),
        "toegestaan": kostenwacht.toegestane_sites(),
        "zwarte_lijst": kostenwacht.ZWARTE_LIJST,
        "claude_gevonden": bool(claude_taken.claude_pad()),
    }


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "Clip-OS"

    def log_message(self, *_):
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _stuur(self, code: int, body: bytes, soort: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", soort)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._stuur(code, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return self._json({"fout": "alleen via 127.0.0.1"}, 403)
        url = urlparse(self.path)
        pad = url.path
        if pad in ("/", "/index.html"):
            html = (WEB / "index.html").read_text(encoding="utf-8").replace("__CLIPOS_SLEUTEL__", SLEUTEL)
            return self._stuur(200, html.encode(), "text/html; charset=utf-8",
                               {"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://i.ytimg.com; media-src 'self'"})
        if pad in STATISCH:
            bestand, soort = STATISCH[pad]
            return self._stuur(200, (WEB / bestand).read_bytes(), soort)
        if pad == "/api/staat":
            cfg_talen = productie.config().get("talen", {})
            return self._json({
                "meldingen": inbox.meldingen(8), "voorstellen": inbox.alle(), "telling": inbox.telling(),
                "talen": {k: v.get("label", k) for k, v in cfg_talen.items()},
                "accounts": {k: v.get("account", "") for k, v in cfg_talen.items()},
                "taken": claude_taken.alle(),
                "kostenwacht_ok": not (kostenwacht.controleer_sleutels() or kostenwacht.scan_code()),
            })
        if pad == "/api/briefs":
            return self._json(briefs_lijst())
        if pad == "/api/config":
            return self._json({**productie.config(), "montage": werk.montage_instellingen(), "opslag": werk.opslag_instellingen(),
                               "whisper_modellen": WHISPER_MODELLEN})
        if pad == "/api/opslag":
            return self._json(opslag.overzicht())
        if pad == "/api/jobs/open":
            return self._json(productie.open_jobs())
        if pad == "/api/views/staat":
            return self._json(views.STAAT)
        if pad == "/api/systeem":
            return self._json({"versie": bijwerken.versie(), "update": bijwerken.STAAT})
        if pad == "/api/kostenwacht":
            return self._json(kostenwacht_status())
        if pad == "/api/trends":
            from . import trends
            return self._json({"rapport": trends.lees_rapport()})
        if pad == "/api/lessenboek":
            return self._json({"tekst": (werk.ROOT / "lessenboek.md").read_text(encoding="utf-8")})
        if pad.startswith("/video/"):
            return self._video(pad[len("/video/"):], "download" in parse_qs(url.query))
        return self._json({"fout": "niet gevonden"}, 404)

    def _video(self, vid: str, download: bool) -> None:
        try:
            v = inbox.lees(vid)
            pad = (werk.ROOT / v["map"] / "video.mp4").resolve()
            pad.relative_to(werk.OUTPUT.resolve())
        except Exception:
            return self._json({"fout": "video niet gevonden"}, 404)
        grootte = pad.stat().st_size
        start, eind = 0, grootte - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and not download:
            if m.group(1):
                start = int(m.group(1))
                eind = min(int(m.group(2)), grootte - 1) if m.group(2) else eind
            elif m.group(2):
                start = max(0, grootte - int(m.group(2)))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{eind}/{grootte}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(eind - start + 1))
        if download:
            naam = f"{v.get('taal') or 'clip'}-{werk.slug(v.get('titel', 'clip'))}.mp4"
            self.send_header("Content-Disposition", f'attachment; filename="{naam}"')
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
        if not self._host_ok() or not secrets.compare_digest(self.headers.get("X-ClipOS-Sleutel", ""), SLEUTEL):
            return self._json({"fout": "Geen toegang. Herlaad de pagina."}, 403)
        lengte = min(int(self.headers.get("Content-Length") or 0), 200_000)
        try:
            body = json.loads(self.rfile.read(lengte) or b"{}") if lengte else {}
        except json.JSONDecodeError:
            return self._json({"fout": "ongeldige gegevens"}, 400)
        try:
            return self._post(urlparse(self.path).path, body)
        except ValueError as e:
            return self._json({"fout": str(e)}, 400)
        except (OSError, KeyError) as e:
            return self._json({"fout": f"Niet gevonden: {e}"}, 404)

    def _post(self, pad: str, body: dict):
        if m := re.fullmatch(r"/api/claude/(video|dagelijks|campagne|trends|afmaken)", pad):
            return self._json({"ok": True, "taak": claude_taken.nieuw(m.group(1), body)})
        if m := re.fullmatch(r"/api/claude/stop/([0-9a-f]{12})", pad):
            return self._json({"ok": True, "taak": claude_taken.stop(m.group(1))})
        if m := re.fullmatch(r"/api/briefs/([a-z0-9-]{2,60})", pad):
            brief = valideer_brief(body)
            werk.schrijf_json(werk.BRIEFS / f"{m.group(1)}.json", brief)
            return self._json({"ok": True, "brief": brief})
        if pad == "/api/views/ophalen":
            return self._json({"ok": True, "staat": views.start()})
        if pad == "/api/opslag/opruimen":
            return self._json({"ok": True, "uitslag": opslag.ruim_op(), "opslag": opslag.overzicht()})
        if pad == "/api/systeem/bijwerken":
            return self._json({"ok": True, "update": bijwerken.start()})
        if pad == "/api/config":
            cfg = valideer_config(body)
            werk.schrijf_json(werk.ROOT / "config.json", cfg)
            return self._json({"ok": True, "config": cfg})
        if m := re.fullmatch(r"/api/(akkoord|afwijzen|geplaatst|views|opnieuw|terug|link)/([^/]+)", pad):
            return self._voorstel(m.group(1), m.group(2), body)
        return self._json({"fout": "onbekende actie"}, 404)

    def _voorstel(self, actie: str, vid: str, body: dict):
        v = inbox.lees(vid)
        if actie == "akkoord" and v["status"] in ("idee", "afgewezen"):
            wijzig = {k: str(body[k]).strip()[:200] for k in ("hook", "titel") if body.get(k)}
            inbox.zet(vid, status="akkoord", **wijzig)
            WACHTRIJ.put(vid)
        elif actie == "opnieuw" and v["status"] in ("fout", "klaar"):
            inbox.zet(vid, status="akkoord")
            WACHTRIJ.put(vid)
        elif actie == "afwijzen" and v["status"] == "idee":
            inbox.zet(vid, status="afgewezen", afwijsreden=str(body.get("reden", ""))[:300])
        elif actie == "terug" and v["status"] == "afgewezen":
            inbox.zet(vid, status="idee")
        elif actie == "link" and v["status"] == "geplaatst":
            link = str(body.get("link", "")).strip()
            if link and not views.geldige_link(link):
                raise ValueError("Plak de link van je YouTube Short of TikTok (https://…)")
            inbox.zet(vid, link=link)
        elif actie == "geplaatst" and v["status"] == "klaar":
            link = str(body.get("link", "")).strip()[:500]
            if link and not views.geldige_link(link):
                raise ValueError("Dat lijkt geen link van een YouTube Short of TikTok. Laat het leeg of plak de juiste link.")
            inbox.zet(vid, status="geplaatst", link=link, geplaatst_op=inbox.nu())
        elif actie == "views" and v["status"] == "geplaatst":
            try:
                views = int(str(body.get("views", "")).replace(".", "").replace(",", "").strip())
            except ValueError:
                raise ValueError("Views moet een getal zijn")
            inbox.zet(vid, views=views, views_op=inbox.nu())
        else:
            return self._json({"fout": f"'{actie}' kan niet bij status '{v['status']}'"}, 409)
        return self._json({"ok": True, "voorstel": inbox.lees(vid)})


def start(poort: int, browser: bool = True) -> None:
    for v in inbox.alle():  # onderbroken videowerk weer oppakken
        if v.get("status") in ("akkoord", "bezig"):
            WACHTRIJ.put(v["id"])
    claude_taken.herstel()
    threading.Thread(target=werker, daemon=True).start()
    opslag.start_achtergrond()  # oude videobestanden opruimen (als dat aan staat), daarna elke 6 uur
    threading.Thread(target=claude_taken.werker, daemon=True).start()
    url = f"http://127.0.0.1:{poort}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", poort), Handler)
    except OSError:
        print(f"Clip-OS draait al op {url}")
        if browser:
            webbrowser.open(url)
        return
    print(f"🎬 Clip-OS draait op {url}   (open in Chrome · stoppen: Ctrl+C)")
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGestopt.")
