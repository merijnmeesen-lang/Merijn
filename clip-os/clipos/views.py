"""Views automatisch ophalen van geplaatste video's (YouTube Shorts, TikTok) via de link. Gratis: alleen yt-dlp."""

from __future__ import annotations

import re
import threading
from datetime import date, datetime

from . import inbox, werk

LINK = re.compile(r"https?://(www\.|m\.)?(youtube\.com/(shorts/|watch\?v=)|youtu\.be/|tiktok\.com/)\S+", re.I)
STAAT: dict = {"status": "rust", "bijgewerkt": 0, "fouten": [], "klaar": None}
_slot = threading.Lock()


def geldige_link(url: str) -> bool:
    return bool(LINK.fullmatch(str(url or "").strip()))


def haal_op(url: str, extractor=None) -> dict:
    """{'views', 'likes', 'reacties'} van één video. `extractor` is alleen voor tests."""
    if extractor is None:
        import yt_dlp

        with yt_dlp.YoutubeDL(werk.ytdlp_opties(skip_download=True)) as ydl:
            info = ydl.extract_info(url, download=False)
    else:
        info = extractor(url)
    return {"views": int(info.get("view_count") or 0), "likes": info.get("like_count"), "reacties": info.get("comment_count")}


def voeg_meting_toe(historie: list, views: int, dag: str | None = None) -> list:
    """Eén meting per dag: [[datum, views], …], de nieuwste meting van een dag vervangt de oude."""
    dag = dag or date.today().isoformat()
    historie = [m for m in (historie or []) if m[0] != dag]
    return (historie + [[dag, views]])[-90:]


def groei(historie: list) -> int | None:
    """Views erbij sinds de vorige meetdag."""
    if not historie or len(historie) < 2:
        return None
    return historie[-1][1] - historie[-2][1]


def werk_bij(extractor=None) -> dict:
    """Haal de views op van alle geplaatste video's met een link."""
    bijgewerkt, fouten = 0, []
    for v in inbox.alle():
        if v.get("status") != "geplaatst" or not geldige_link(v.get("link", "")):
            continue
        try:
            stats = haal_op(v["link"], extractor)
        except Exception as e:
            fouten.append(f"{v.get('titel', v['id'])[:50]}: {str(e)[:120]}")
            continue
        inbox.zet(v["id"], views=stats["views"], likes=stats["likes"], reacties=stats["reacties"], views_op=inbox.nu(),
                  views_auto=True, views_historie=voeg_meting_toe(v.get("views_historie"), stats["views"]))
        bijgewerkt += 1
    return {"bijgewerkt": bijgewerkt, "fouten": fouten}


def _achtergrond() -> None:
    try:
        uit = werk_bij()
        STAAT.update(status="klaar", bijgewerkt=uit["bijgewerkt"], fouten=uit["fouten"])
    except Exception as e:
        STAAT.update(status="fout", fouten=[str(e)[:200]])
    finally:
        STAAT["klaar"] = datetime.now().isoformat(timespec="seconds")


def start() -> dict:
    with _slot:
        if STAAT["status"] != "bezig":
            STAAT.update(status="bezig", bijgewerkt=0, fouten=[], klaar=None)
            threading.Thread(target=_achtergrond, daemon=True).start()
    return STAAT
