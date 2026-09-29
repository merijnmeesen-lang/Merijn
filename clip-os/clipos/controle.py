"""Controleur (automatisch deel): toetst elke video aan de techniek-eisen en de campagne-brief."""

from __future__ import annotations

from pathlib import Path

from . import werk


def controleer(video: Path, voorstel: dict, brief: dict) -> list[tuple[bool, str]]:
    uit: list[tuple[bool, str]] = []

    def check(ok: bool, tekst: str) -> None:
        uit.append((bool(ok), tekst))

    bestaat = video.exists() and video.stat().st_size > 50_000
    check(bestaat, "videobestand gemaakt")
    if bestaat:
        info = werk.video_info(video)
        check((info["breedte"], info["hoogte"]) == (1080, 1920), f"formaat 1080x1920 (is {info['breedte']}x{info['hoogte']})")
        check(info["audio"], "geluid aanwezig")
        lo, hi = brief.get("min_seconden", 15), brief.get("max_seconden", 60)
        check(lo - 0.5 <= info["duur"] <= hi + 0.5, f"lengte {info['duur']:.1f}s binnen {lo}-{hi}s")

    hook = voorstel.get("hook", "")
    titel = voorstel.get("titel", "")
    tekst = " ".join([titel, voorstel.get("beschrijving", ""), " ".join(voorstel.get("hashtags", []))])
    check(0 < len(hook) <= 90, "hook aanwezig en kort (≤90 tekens)")
    check(0 < len(titel) <= 100, "titel aanwezig (≤100 tekens, YouTube-limiet)")
    for tag in brief.get("verplichte_hashtags", []):
        check(tag.lower() in tekst.lower(), f"verplichte hashtag {tag}")
    for zin in brief.get("verplichte_tekst", []):
        check(zin.lower() in tekst.lower(), f"verplichte tekst '{zin}'")
    for woord in brief.get("verboden", []):
        check(woord.lower() not in (tekst + " " + hook).lower(), f"geen verboden woord '{woord}'")
    return uit


def geslaagd(resultaat: list[tuple[bool, str]]) -> bool:
    return all(ok for ok, _ in resultaat)
