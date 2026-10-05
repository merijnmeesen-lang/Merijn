"""Ondertitels (ASS): grote woorden onderin met het gesproken woord gemarkeerd, plus de hook bovenin."""

from __future__ import annotations

import re

WIT = "&H00FFFFFF&"
GEEL = "&H0000E5FF&"

KOP = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Onder,Arial,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,520,1
Style: Hook,Arial,62,&H00000000,&H00000000,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,3,20,0,8,90,90,300,1
Style: Pop,Arial,118,&H0000E5FF,&H0000E5FF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,9,5,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_tijd(sec: float) -> str:
    sec = max(sec, 0.0)
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def schoon(tekst: str) -> str:
    return re.sub(r"[{}\\]", "", tekst).strip()


def groepeer(woorden: list[dict], max_woorden: int = 3, max_tekens: int = 18, max_gat: float = 0.6) -> list[list[dict]]:
    groepen: list[list[dict]] = []
    huidig: list[dict] = []
    for w in woorden:
        if huidig:
            vorige = huidig[-1]
            lengte = sum(len(x["woord"]) + 1 for x in huidig) + len(w["woord"])
            if (
                len(huidig) >= max_woorden
                or lengte > max_tekens
                or w["start"] - vorige["end"] > max_gat
                or vorige["woord"].rstrip().endswith((".", "?", "!"))
            ):
                groepen.append(huidig)
                huidig = []
        huidig.append(w)
    if huidig:
        groepen.append(huidig)
    return groepen


AANHANGSEL = re.compile(r"^([,.!?%:;)\]}…]|['’](s|t|re|ve|ll|d|m)\b)", re.I)


def plak_aanhangsels(woorden: list[dict]) -> list[dict]:
    """Whisper levert soms losse stukjes: '13' + ',000', 'it' + "'s", '50' + '%'. Die horen aan het vorige woord vast."""
    uit: list[dict] = []
    for w in woorden:
        if uit and AANHANGSEL.match(w["woord"]):
            uit[-1] = {**uit[-1], "woord": uit[-1]["woord"] + w["woord"], "end": max(uit[-1]["end"], w["end"])}
        else:
            uit.append(dict(w))
    return uit


POP_DUUR = 1.4


def maak_ass(woorden: list[dict], clip_start: float, duur: float, hook: str = "", hook_duur: float = 3.0,
             hook_y: int = 300, onder_pos: tuple[int, int] | None = None,
             split_intervallen: list[tuple[float, float]] | None = None,
             popups: list[tuple[float, str, int]] | None = None) -> str:
    """woorden: absolute tijden uit het transcript; ze worden omgerekend naar clip-tijd.

    split_intervallen: stukken (clip-tijd) met twee mensen boven elkaar; ondertitels staan dan op de naad (540, 960).
    popups: [(tijd, tekst, y)] grote tekst die even oppopt bij een sterk getal of woord."""
    rel = [
        {"start": max(0.0, w["start"] - clip_start), "end": min(duur, w["end"] - clip_start), "woord": schoon(w["woord"]).upper()}
        for w in plak_aanhangsels([w for w in woorden if schoon(w["woord"])])
    ]
    regels = [KOP]
    if hook:
        regels.append(f"Dialogue: 1,{ass_tijd(0)},{ass_tijd(min(hook_duur, duur))},Hook,,0,0,0,,"
                      f"{{\\an8\\pos(540,{int(hook_y)})}}{schoon(hook)}\n")

    for t, tekst, y in popups or []:
        if 0 <= t < duur and schoon(tekst):
            regels.append(f"Dialogue: 2,{ass_tijd(t)},{ass_tijd(min(duur, t + POP_DUUR))},Pop,,0,0,0,,"
                          f"{{\\an5\\pos(540,{int(y)})\\fscx40\\fscy40\\t(0,110,\\fscx114\\fscy114)"
                          f"\\t(110,200,\\fscx100\\fscy100)\\fad(0,160)}}{schoon(tekst).upper()}\n")

    vast = f"{{\\an5\\pos({onder_pos[0]},{onder_pos[1]})}}" if onder_pos else ""

    def plek(t: float) -> str:
        if any(a - 0.05 <= t < b for a, b in split_intervallen or []):
            return "{\\an5\\pos(540,960)}"
        return vast

    groepen = groepeer(rel)
    for gi, groep in enumerate(groepen):
        volgende_start = groepen[gi + 1][0]["start"] if gi + 1 < len(groepen) else duur
        for i, w in enumerate(groep):
            start = w["start"]
            if i + 1 < len(groep):
                eind = groep[i + 1]["start"]
            else:
                eind = min(w["end"] + 0.5, volgende_start)
            if eind <= start:
                continue
            delen = [
                (f"{{\\c{GEEL}}}{x['woord']}{{\\c{WIT}}}" if j == i else x["woord"])
                for j, x in enumerate(groep)
            ]
            regels.append(f"Dialogue: 0,{ass_tijd(start)},{ass_tijd(eind)},Onder,,0,0,0,,{plek(groep[0]['start'])}{' '.join(delen)}\n")
    return "".join(regels)
