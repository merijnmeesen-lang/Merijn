"""Effecten in de stijl van grote podcastclips: geluidseffecten op de knippen en grote pop-up tekst bij sterke getallen.

Alles gratis: de geluiden maakt Clip-OS zelf met ffmpeg (geen samples van anderen, dus geen rechtenproblemen).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import werk

GELUIDEN = {
    # zachte "whoosh": roze ruis die aanzwelt en wegsterft
    "whoosh": "anoisesrc=d=0.42:c=pink:r=48000:a=0.5,highpass=f=350,lowpass=f=5500,"
              "afade=t=in:d=0.24:curve=qsin,afade=t=out:st=0.24:d=0.18:curve=qsin",
    # lage "boem": dalende toon met korte aanzet
    "boem": "aevalsrc='0.9*sin(2*PI*(70-40*t)*t)*exp(-7*t)':d=0.6:s=48000,lowpass=f=260,afade=t=in:d=0.005",
}
VOLUME = {"whoosh": 0.9, "boem": 0.28}  # ±12 dB onder normale spraak: hoorbaar, niet storend
MIN_AFSTAND = {"whoosh": 2.0, "boem": 3.0}


def geluid(naam: str) -> Path:
    """Pad naar het geluidseffect; wordt de eerste keer gemaakt (data/geluid/)."""
    pad = werk.DATA / "geluid" / f"{naam}.wav"
    if not pad.exists():
        pad.parent.mkdir(parents=True, exist_ok=True)
        tmp = pad.with_suffix(".tmp.wav")
        werk.draai([werk.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", GELUIDEN[naam],
                    "-ac", "2", "-ar", "48000", str(tmp)])
        tmp.replace(pad)
    return pad


def momenten(tijden: list[float], duur: float, min_afstand: float, begin: float = 0.3) -> list[float]:
    """Sorteren, dubbele en te dicht opeenvolgende momenten weghalen."""
    uit: list[float] = []
    for t in sorted(tijden):
        if begin <= t <= duur - 0.4 and (not uit or t - uit[-1] >= min_afstand):
            uit.append(round(t, 3))
    return uit


def audio_graaf(spraak: str, geluiden: dict[str, list[float]], eerste_input: int) -> tuple[list[str], list[Path], str]:
    """Filters die de geluidseffecten onder de spraak mengen.

    geluiden: {"whoosh": [tijden], "boem": [tijden]} (in clip-tijd). Geeft (filters, extra_inputs, uitvoer-label)."""
    filters, inputs, labels = [], [], []
    for naam, tijden in geluiden.items():
        if not tijden:
            continue
        idx = eerste_input + len(inputs)
        inputs.append(geluid(naam))
        delen = [f"[{naam}{i}]" for i in range(len(tijden))]
        filters.append(f"[{idx}:a]volume={VOLUME[naam]},asplit={len(tijden)}{''.join(delen)}" if len(tijden) > 1
                       else f"[{idx}:a]volume={VOLUME[naam]}{delen[0]}")
        for i, t in enumerate(tijden):
            ms = int(t * 1000)
            filters.append(f"{delen[i]}adelay={ms}|{ms}[{naam}d{i}]")
            labels.append(f"[{naam}d{i}]")
    if not labels:
        return [], [], spraak
    filters.append(f"{spraak}{''.join(labels)}amix=inputs={len(labels) + 1}:duration=first:normalize=0:dropout_transition=0[amix]")
    return filters, inputs, "[amix]"


# ---------- pop-up tekst ----------

GROOTTE = {"thousand": "THOUSAND", "million": "MILLION", "billion": "BILLION", "trillion": "TRILLION",
           "duizend": "DUIZEND", "miljoen": "MILJOEN", "miljard": "MILJARD", "procent": "PROCENT", "percent": "PERCENT",
           "k": "K", "m": "M", "bn": "BN"}
GETAL = re.compile(r"^[\$€£]?\d[\d.,]*(%|k|m|bn)?$", re.I)


def _schoon(woord: str) -> str:
    return re.sub(r"[^\w$€£%.,]", "", woord).strip(".,")


def automatische_popups(woorden: list[dict], maximum: int = 2) -> list[dict]:
    """Sterke getallen uit wat er gezegd wordt ("$3 billion", "90%", "10.000 euro"), als er geen door Claude gekozen zijn.

    woorden: met bron-tijden. Geeft [{"t", "tekst"}] in bron-tijd."""
    kandidaten = []
    for i, w in enumerate(woorden):
        kaal = _schoon(w["woord"])
        if not GETAL.match(kaal) or not any(c.isdigit() for c in kaal):
            continue
        volgende = _schoon(woorden[i + 1]["woord"]).lower() if i + 1 < len(woorden) else ""
        tekst, gewicht = kaal.upper(), 0
        if volgende in GROOTTE:
            tekst += " " + GROOTTE[volgende]
            gewicht = 3
        elif volgende in ("euro", "dollar", "dollars", "pounds", "euros"):
            tekst += " " + volgende.upper()
            gewicht = 2
        if kaal[0] in "$€£" or kaal.endswith("%"):
            gewicht += 2
        cijfers = re.sub(r"\D", "", kaal)
        if len(cijfers) >= 3:
            gewicht += 1
        if gewicht >= 2:  # losse getallen ("2 kinderen") niet
            kandidaten.append((gewicht, w["start"], tekst))
    gekozen: list[tuple] = []
    for gewicht, t, tekst in sorted(kandidaten, key=lambda k: (-k[0], k[1])):
        if len(gekozen) < maximum and all(abs(t - g[1]) >= 4 for g in gekozen):
            gekozen.append((gewicht, t, tekst))
    return [{"t": t, "tekst": tekst} for _, t, tekst in sorted(gekozen, key=lambda g: g[1])]


def popup_lijst(kernwoorden: list | None, woorden: list[dict], start: float, end: float, maximum: int = 3) -> list[dict]:
    """Kernwoorden van Claude (binnen de clip), anders automatisch gevonden getallen."""
    eigen = [{"t": float(k["t"]), "tekst": str(k["tekst"]).strip()[:28]} for k in (kernwoorden or [])
             if isinstance(k, dict) and isinstance(k.get("t"), (int, float)) and str(k.get("tekst", "")).strip()
             and start <= float(k["t"]) <= end]
    return eigen[:maximum] if eigen else automatische_popups(woorden)
