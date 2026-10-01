"""Trendonderzoek (uitvoerend deel): recente podcasts/interviews op YouTube vinden die snel stijgen.

Gratis: gebruikt alleen yt-dlp. Het bedenken van de zoekonderwerpen gebeurt door de
agent clip-trendonderzoeker (Claude, via het Pro-abonnement).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from . import inbox, werk

MAP = werk.DATA / "trends"
RAPPORT = MAP / "rapport.json"
# YouTube-filter "uploaddatum" in de zoek-URL
PERIODE = {"dag": "EgIIAg%3D%3D", "week": "EgIIAw%3D%3D", "maand": "EgIIBA%3D%3D"}
TOESTEMMING = ("campagne", "onbekend")


# ---------- pure functies (getest) ----------

def normaliseer(info: dict, vandaag: date | None = None) -> dict:
    vandaag = vandaag or date.today()
    views = int(info.get("view_count") or 0)
    geupload = info.get("upload_date") or ""
    dagen = None
    if re.fullmatch(r"\d{8}", geupload):
        d = date(int(geupload[:4]), int(geupload[4:6]), int(geupload[6:]))
        dagen = max((vandaag - d).days, 0)
        geupload = d.isoformat()
    per_dag = round(views / max(dagen if dagen is not None else 7, 0.5))
    return {
        "titel": info.get("title") or "",
        "url": info.get("webpage_url") or (f"https://www.youtube.com/watch?v={info['id']}" if info.get("id") else ""),
        "kanaal": info.get("channel") or info.get("uploader") or "",
        "kanaal_url": info.get("uploader_url") or info.get("channel_url") or "",
        "kanaal_id": info.get("channel_id") or "",
        "views": views,
        "geupload": geupload,
        "dagen_oud": dagen,
        "per_dag": per_dag,
        "duur_min": round((info.get("duration") or 0) / 60),
    }


def _sleutels(url: str) -> set[str]:
    url = (url or "").lower().rstrip("/")
    url = re.sub(r"/(videos|streams|featured|shorts)$", "", url)
    uit = set()
    if m := re.search(r"/@([\w.\-]+)", url):
        uit.add("@" + m.group(1))
    if m := re.search(r"/channel/(uc[\w\-]+)", url):
        uit.add(m.group(1))
    return uit


def campagne_voor(video: dict, briefs: list[tuple[str, dict]]) -> str:
    """Naam van de campagne-brief waarvan dit kanaal een bron is, anders ''."""
    video_sleutels = _sleutels(video.get("kanaal_url", "")) | ({video["kanaal_id"].lower()} if video.get("kanaal_id") else set())
    for naam, brief in briefs:
        for bron in brief.get("bron_kanalen", []):
            if video_sleutels & _sleutels(bron):
                return naam
        if video.get("url") and video["url"] in brief.get("bron_links", []):
            return naam
    return ""


def valideer_rapport(r: dict) -> list[str]:
    fouten = []
    if not isinstance(r.get("videos"), list) or not r["videos"]:
        fouten.append("'videos' moet een niet-lege lijst zijn")
        return fouten
    briefnamen = {p.stem for p in werk.BRIEFS.glob("*.json")}
    for i, v in enumerate(r["videos"], 1):
        if not re.fullmatch(r"https://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{6,}\S*", str(v.get("url", ""))):
            fouten.append(f"video {i}: ongeldige YouTube-link")
        if v.get("toestemming") not in TOESTEMMING:
            fouten.append(f"video {i}: 'toestemming' moet 'campagne' of 'onbekend' zijn")
        if v.get("toestemming") == "campagne" and v.get("campagne") not in briefnamen:
            fouten.append(f"video {i}: campagne '{v.get('campagne')}' bestaat niet in briefs/")
        if not v.get("titel") or not v.get("waarom"):
            fouten.append(f"video {i}: 'titel' en 'waarom' zijn verplicht")
    return fouten


# ---------- YouTube (yt-dlp) ----------

def _details(urls: list[str]) -> list[dict]:
    import yt_dlp

    uit = []
    with yt_dlp.YoutubeDL(werk.ytdlp_opties(skip_download=True)) as ydl:
        for url in urls:
            try:
                uit.append(normaliseer(ydl.extract_info(url, download=False)))
            except Exception as e:  # één kapotte video mag de rest niet tegenhouden
                print(f"⚠️  overgeslagen: {url} ({e})")
    return uit


def _plat(url: str, aantal: int) -> list[dict]:
    import yt_dlp

    with yt_dlp.YoutubeDL(werk.ytdlp_opties(extract_flat="in_playlist", playlistend=aantal)) as ydl:
        info = ydl.extract_info(url, download=False)
    return [e for e in (info.get("entries") or []) if e]


def _url(e: dict) -> str:
    return e.get("url") if str(e.get("url", "")).startswith("http") else f"https://www.youtube.com/watch?v={e.get('id')}"


def zoek(query: str, periode: str = "week", maximum: int = 8, min_minuten: int = 10) -> list[dict]:
    """Zoek lange video's (podcasts/interviews) uit de gekozen periode, meeste views eerst."""
    zoek_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp={PERIODE[periode]}"
    kandidaten = [e for e in _plat(zoek_url, 40) if (e.get("duration") or 0) >= min_minuten * 60]
    kandidaten.sort(key=lambda e: -(e.get("view_count") or 0))
    return _details([_url(e) for e in kandidaten[:maximum]])


def kanaal(url: str, maximum: int = 8, min_minuten: int = 10) -> list[dict]:
    """De nieuwste lange video's van één kanaal (bijv. een campagnebron)."""
    lijst = url.rstrip("/")
    if "youtube.com/@" in lijst and not lijst.endswith(("/videos", "/streams")):
        lijst += "/videos"
    kandidaten = [e for e in _plat(lijst, 20) if (e.get("duration") or 0) >= min_minuten * 60][:maximum]
    return _details([_url(e) for e in kandidaten])


def verrijk(videos: list[dict]) -> list[dict]:
    from .productie import actieve_briefs

    briefs = actieve_briefs()
    for v in videos:
        v["campagne"] = campagne_voor(v, briefs)
        v["toestemming"] = "campagne" if v["campagne"] else "onbekend"
    return sorted(videos, key=lambda v: -v["per_dag"])


# ---------- rapport ----------

def lees_rapport() -> dict | None:
    if not RAPPORT.exists():
        return None
    try:
        return werk.lees_json(RAPPORT)
    except (json.JSONDecodeError, OSError):
        return None


def rond_af() -> dict:
    r = lees_rapport()
    if r is None:
        raise SystemExit(f"{RAPPORT} bestaat niet of is geen geldige JSON (de trendonderzoeker moet dit schrijven).")
    fouten = valideer_rapport(r)
    if fouten:
        raise SystemExit("rapport.json klopt niet:\n  " + "\n  ".join(fouten))
    r.setdefault("gemaakt", inbox.nu())
    werk.schrijf_json(RAPPORT, r)
    archief = MAP / "archief"
    archief.mkdir(parents=True, exist_ok=True)
    werk.schrijf_json(archief / f"{datetime.now():%Y%m%d-%H%M}.json", r)
    met = sum(v["toestemming"] == "campagne" for v in r["videos"])
    top = r["videos"][0]
    per_dag = f"{int(top.get('per_dag') or 0):,}".replace(",", ".")
    inbox.melding(
        f"🔥 Marktonderzoek klaar: {len(r['videos'])} trending video's gevonden, waarvan {met} uit je campagnes (mag je clippen). "
        f"Topper: '{top['titel'][:70]}' ({per_dag} views/dag). Bekijk ze bij Trends.",
        soort="trends",
    )
    return r
