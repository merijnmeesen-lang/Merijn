"""Gezichtsvolging voor 9:16: bepaalt per stukje clip waar het beeld wordt bijgesneden."""

from __future__ import annotations

from pathlib import Path
from statistics import median


def gezicht_posities(bron: Path, start: float, end: float, stap: float = 0.5) -> list[tuple]:
    """(tijd t.o.v. clipstart, x-midden van het grootste gezicht, onderkant van het gezicht incl. kin)
    als fracties 0..1 van het bronbeeld, of None als er geen gezicht is."""
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
            x, y, gw, gh = max(gezichten, key=lambda g: g[2] * g[3])
            onder = min(1.0, (y + gh * 1.25) / klein.shape[0])  # +25%: de detector stopt rond de mond, kin en hals komen eronder
            uit.append((t - start, (x + gw / 2) / klein.shape[1], onder))
        else:
            uit.append((t - start, None, None))
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
    for p in posities:
        x = p[1]
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


HOOK_STANDAARD_Y = 300   # bovenkant van de hook (in een 1080x1920-beeld) als er geen gezicht bekend is
HOOK_MAX_Y = 1150        # lager niet: daar beginnen de ondertitels


def hook_y(posities, hook_duur: float = 3.0, hoogte: int = 1920) -> int:
    """Waar de hook moet staan zodat hij het gezicht niet bedekt: net onder het (laagste) gezicht
    in de eerste seconden. De crop gebruikt de volle hoogte, dus fractie × 1920 = positie in beeld."""
    onder = [p[2] for p in posities if len(p) > 2 and p[2] is not None and p[0] <= hook_duur]
    if not onder:
        return HOOK_STANDAARD_Y
    y = int(max(onder) * hoogte) + 40
    return max(HOOK_STANDAARD_Y, min(HOOK_MAX_Y, y))


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
