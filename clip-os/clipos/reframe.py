"""Gezichtsvolging voor 9:16: bepaalt per stukje clip waar het beeld wordt bijgesneden."""

from __future__ import annotations

from pathlib import Path
from statistics import median


def gezicht_posities(bron: Path, start: float, end: float, stap: float = 0.5) -> list[tuple[float, float | None]]:
    """(tijd t.o.v. clipstart, x-midden van het grootste gezicht als fractie 0..1 of None)."""
    import cv2

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(bron))
    uit = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        schaal = 480 / w if w > 480 else 1.0
        klein = cv2.resize(frame, None, fx=schaal, fy=schaal) if schaal != 1.0 else frame
        grijs = cv2.cvtColor(klein, cv2.COLOR_BGR2GRAY)
        gezichten = cascade.detectMultiScale(grijs, scaleFactor=1.1, minNeighbors=6, minSize=(24, 24))
        if len(gezichten):
            x, _, gw, _ = max(gezichten, key=lambda g: g[2] * g[3])
            uit.append((t - start, (x + gw / 2) / klein.shape[1]))
        else:
            uit.append((t - start, None))
        t += stap
    cap.release()
    return uit


def crop_segmenten(posities, duur: float, drempel: float = 0.08, venster: int = 5) -> list[tuple[float, float]]:
    """Zet ruwe gezichtsposities om in rustige stukken [(vanaf_tijd, x_fractie)].

    - ontbrekende metingen erven de vorige positie (of het midden);
    - een mediaanfilter haalt uitschieters weg;
    - de camera verspringt pas als het gezicht minstens `drempel` verschuift
      en dat twee metingen achter elkaar zo blijft (geen trillend beeld).
    """
    if not posities:
        return [(0.0, 0.5)]
    xs, laatste = [], None
    for _, x in posities:
        laatste = x if x is not None else laatste
        xs.append(laatste)
    eerste = next((x for x in xs if x is not None), 0.5)
    xs = [eerste if x is None else x for x in xs]
    half = venster // 2
    glad = [median(xs[max(0, i - half): i + half + 1]) for i in range(len(xs))]

    segmenten = [(0.0, glad[0])]
    huidig = glad[0]
    for i in range(1, len(glad)):
        volgende = glad[i + 1] if i + 1 < len(glad) else glad[i]
        if abs(glad[i] - huidig) > drempel and abs(volgende - huidig) > drempel:
            huidig = glad[i]
            segmenten.append((posities[i][0], huidig))
    return [(t, x) for t, x in segmenten if t < duur]


def crop_x_expressie(segmenten, bron_breedte: int, crop_breedte: int) -> str:
    """ffmpeg-expressie voor de x-positie van de crop (stukjes met vaste positie)."""
    def px(frac: float) -> int:
        x = int(round(frac * bron_breedte - crop_breedte / 2))
        return max(0, min(bron_breedte - crop_breedte, x))

    expr = str(px(segmenten[-1][1]))
    for i in range(len(segmenten) - 2, -1, -1):
        grens = segmenten[i + 1][0]
        expr = f"if(lt(t\\,{grens:.2f})\\,{px(segmenten[i][1])}\\,{expr})"
    return expr
