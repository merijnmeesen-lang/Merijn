"""Tempo: stiltes en stopwoorden uit een clip knippen, en bepalen waar ingezoomd wordt.

Alles werkt met de tijd per woord uit het transcript. Tijden zijn absolute seconden in de bronvideo,
tenzij er 'nieuw' bij staat: dan is het de tijd in de ingekorte clip.
"""

from __future__ import annotations

import re

STOPWOORDEN = {"uh", "um", "uhm", "umm", "uhh", "er", "erm", "ah", "ahh", "eh", "ehm", "hmm", "hm", "mm", "mhm"}


def is_stopwoord(woord: str) -> bool:
    return re.sub(r"[^\w]", "", woord.lower()) in STOPWOORDEN


def bewaar_segmenten(woorden: list[dict], start: float, end: float, max_stilte: float = 0.4,
                     voor: float = 0.12, na: float = 0.15) -> list[tuple[float, float]]:
    """Welke stukken van [start, end] blijven staan.

    Woorden met minder dan `max_stilte` pauze ertussen vormen één stuk. Langere pauzes en stopwoorden
    (uh, um, …) vallen weg; rond elk stuk blijft een kleine marge zodat woorden niet worden afgekapt."""
    spraak = [w for w in woorden if not is_stopwoord(w["woord"]) and w["end"] > start and w["start"] < end]
    if not spraak:
        return [(start, end)]
    # 1. woorden met een korte pauze ertussen horen bij elkaar
    stukken: list[list[float]] = []
    for w in spraak:
        if stukken and w["start"] - stukken[-1][1] <= max_stilte:
            stukken[-1][1] = max(stukken[-1][1], w["end"])
        else:
            stukken.append([w["start"], w["end"]])
    # 2. marge eromheen (niet buiten de clip), en stukken die daardoor overlappen samenvoegen
    uit: list[list[float]] = []
    for a, b in stukken:
        a, b = max(start, a - voor), min(end, b + na)
        if uit and a <= uit[-1][1]:
            uit[-1][1] = max(uit[-1][1], b)
        else:
            uit.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in uit]


def nieuwe_duur(segmenten: list[tuple[float, float]]) -> float:
    return sum(b - a for a, b in segmenten)


def remap(t: float, segmenten: list[tuple[float, float]]) -> float:
    """Bron-tijd -> tijd in de ingekorte clip. Een tijd in een weggeknipt stuk valt op de volgende knip."""
    verstreken = 0.0
    for a, b in segmenten:
        if t < a:
            return verstreken
        if t <= b:
            return verstreken + (t - a)
        verstreken += b - a
    return verstreken


def remap_woorden(woorden: list[dict], segmenten: list[tuple[float, float]]) -> list[dict]:
    """Woorden (zonder stopwoorden) met tijden in de ingekorte clip, voor de ondertitels."""
    return [{**w, "start": remap(w["start"], segmenten), "end": remap(w["end"], segmenten)}
            for w in woorden if not is_stopwoord(w["woord"])]


def select_expressie(segmenten: list[tuple[float, float]], clip_start: float) -> str:
    """ffmpeg select/aselect-expressie (tijd t.o.v. clipstart) die alleen de bewaarde stukken doorlaat."""
    return "+".join(f"between(t\\,{a - clip_start:.3f}\\,{b - clip_start:.3f})" for a, b in segmenten)


def knippen(segmenten: list[tuple[float, float]]) -> list[float]:
    """Tijdstippen in de ingekorte clip waar een knip zit."""
    uit, t = [], 0.0
    for a, b in segmenten[:-1]:
        t += b - a
        uit.append(round(t, 3))
    return uit


def zoom_intervallen(segmenten: list[tuple[float, float]], nadruk: list[float], duur_nieuw: float,
                     nadruk_duur: float = 1.4) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """(punch-in-stukken, nadruk-stukken) in de ingekorte clip.

    - Punch-in: na elke tweede knip een lichte zoom, tot de volgende knip. Dat verbergt de sprong
      en houdt het beeld levendig (zoals bij professioneel gemonteerde podcastclips).
    - Nadruk: een sterkere zoom op de sterkste zinnen die de Hook-jager aanwees (bron-tijden)."""
    grenzen = [0.0] + knippen(segmenten) + [duur_nieuw]
    punch = [(grenzen[i], grenzen[i + 1]) for i in range(1, len(grenzen) - 1, 2) if grenzen[i + 1] - grenzen[i] >= 0.4]
    sterk = []
    for t in sorted(nadruk or []):
        if segmenten[0][0] <= t <= segmenten[-1][1]:
            a = remap(t, segmenten)
            sterk.append((round(a, 3), round(min(duur_nieuw, a + nadruk_duur), 3)))
    return punch[:40], sterk[:5]


def tijd_expressie(intervallen: list[tuple[float, float]]) -> str:
    """ffmpeg 'enable'-expressie: waar in de clip een zoom actief is."""
    return "+".join(f"between(t\\,{a:.3f}\\,{b:.3f})" for a, b in intervallen)
