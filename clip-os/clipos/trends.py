"""Trendonderzoek (uitvoerend deel): recente podcasts/interviews op YouTube vinden die snel stijgen.

Gratis: gebruikt alleen yt-dlp. Het bedenken van de zoekonderwerpen gebeurt door
het commando /trends (Claude, via het Pro-abonnement).
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

PARALLEL = 6  # zoveel video's tegelijk opvragen (elke opvraag wacht vooral op YouTube, niet op je computer)


def _detail(url: str) -> dict | None:
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL(werk.ytdlp_opties(skip_download=True)) as ydl:
            return normaliseer(ydl.extract_info(url, download=False))
    except Exception as e:  # één kapotte video mag de rest niet tegenhouden
        print(f"⚠️  overgeslagen: {url} ({e})")
        return None


def _details(urls: list[str]) -> list[dict]:
    """Details van meerdere video's tegelijk ophalen (veel sneller dan één voor één)."""
    from concurrent.futures import ThreadPoolExecutor

    urls = list(dict.fromkeys(urls))
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        return [d for d in pool.map(_detail, urls) if d]


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


def zoek_meerdere(zoektermen: list[str], periode: str = "week", maximum: int = 8, min_minuten: int = 10,
                  kanalen: list[str] | None = None) -> list[dict]:
    """Meerdere zoektermen en kanalen tegelijk: alle zoekopdrachten parallel, daarna alle details parallel."""
    from concurrent.futures import ThreadPoolExecutor

    def kandidaten_zoek(q: str) -> list[dict]:
        zoek_url = f"https://www.youtube.com/results?search_query={quote_plus(q)}&sp={PERIODE[periode]}"
        try:
            lijst = [e for e in _plat(zoek_url, 40) if (e.get("duration") or 0) >= min_minuten * 60]
        except Exception as e:
            print(f"⚠️  zoeken mislukt: {q} ({e})")
            return []
        return sorted(lijst, key=lambda e: -(e.get("view_count") or 0))[:maximum]

    def kandidaten_kanaal(url: str) -> list[dict]:
        lijst = url.rstrip("/")
        if "youtube.com/@" in lijst and not lijst.endswith(("/videos", "/streams")):
            lijst += "/videos"
        try:
            return [e for e in _plat(lijst, 20) if (e.get("duration") or 0) >= min_minuten * 60][:maximum]
        except Exception as e:
            print(f"⚠️  kanaal niet te lezen: {url} ({e})")
            return []

    taken = [(kandidaten_zoek, q) for q in zoektermen] + [(kandidaten_kanaal, k) for k in kanalen or []]
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        groepen = list(pool.map(lambda t: t[0](t[1]), taken))
    return _details([_url(e) for groep in groepen for e in groep])


def kanaal(url: str, maximum: int = 8, min_minuten: int = 10) -> list[dict]:
    """De nieuwste lange video's van één kanaal (bijv. een campagnebron)."""
    lijst = url.rstrip("/")
    if "youtube.com/@" in lijst and not lijst.endswith(("/videos", "/streams")):
        lijst += "/videos"
    kandidaten = [e for e in _plat(lijst, 20) if (e.get("duration") or 0) >= min_minuten * 60][:maximum]
    return _details([_url(e) for e in kandidaten])


VERBORGEN = MAP / "verborgen.json"


def video_id(url: str) -> str:
    """YouTube-video-id uit een link (watch?v=, youtu.be/, shorts/), anders de link zelf."""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/)([\w-]{6,})", url or "")
    return m.group(1) if m else (url or "").strip().lower()


def verborgen() -> set[str]:
    try:
        return set(werk.lees_json(VERBORGEN)) if VERBORGEN.exists() else set()
    except (json.JSONDecodeError, OSError, TypeError):
        return set()


def verberg(url: str) -> int:
    """Een trendvideo die je niet goed vindt: uit het rapport, en bij volgend onderzoek niet meer voorstellen."""
    if not re.fullmatch(r"https?://\S{5,300}", url or ""):
        raise ValueError("Ongeldige link")
    lijst = verborgen() | {video_id(url)}
    MAP.mkdir(parents=True, exist_ok=True)
    werk.schrijf_json(VERBORGEN, sorted(lijst)[-1000:])
    return len(lijst)


def verrijk(videos: list[dict]) -> list[dict]:
    from .productie import actieve_briefs

    briefs = actieve_briefs()
    weg = verborgen()
    videos = [v for v in videos if video_id(v.get("url", "")) not in weg]  # door de eigenaar verwijderd
    for v in videos:
        v["campagne"] = campagne_voor(v, briefs)
        v["toestemming"] = "campagne" if v["campagne"] else "onbekend"
    return sorted(videos, key=lambda v: -v["per_dag"])


# ---------- rapport ----------

def lees_rapport() -> dict | None:
    if not RAPPORT.exists():
        return None
    try:
        r = werk.lees_json(RAPPORT)
    except (json.JSONDecodeError, OSError):
        return None
    weg = verborgen()
    r["videos"] = [v for v in r.get("videos") or [] if video_id(v.get("url", "")) not in weg]
    return r


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
