"""Gezichtsvolging voor 9:16: bepaalt per stukje clip waar het beeld wordt bijgesneden."""

from __future__ import annotations

from pathlib import Path
from statistics import median


MODEL = Path(__file__).parent / "modellen" / "face_detection_yunet_2023mar.onnx"


def _detector():
    """YuNet (nauwkeurig, ook bij schuin gezicht) als het model er is, anders de eenvoudige Haar-detector.
    Geeft een functie terug: beeld -> [(x, y, b, h, kin_factor)] in pixels."""
    import cv2

    if MODEL.exists() and hasattr(cv2, "FaceDetectorYN"):
        yunet = cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), 0.6)

        def detect(beeld):
            yunet.setInputSize((beeld.shape[1], beeld.shape[0]))
            _, gevonden = yunet.detect(beeld)
            return [(float(f[0]), float(f[1]), float(f[2]), float(f[3]), 1.12) for f in (gevonden if gevonden is not None else [])]
        return detect

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def detect_haar(beeld):
        grijs = cv2.cvtColor(beeld, cv2.COLOR_BGR2GRAY)
        return [(float(x), float(y), float(b), float(h), 1.25) for x, y, b, h in cascade.detectMultiScale(grijs, scaleFactor=1.1, minNeighbors=6, minSize=(24, 24))]
    return detect_haar


def gezicht_posities(bron: Path, start: float, end: float, stap: float = 0.5) -> list[tuple]:
    """Per meting: (tijd t.o.v. clipstart, x-midden grootste gezicht, onderkant grootste gezicht incl. kin, gezichten).

    Alles als fracties 0..1 van het bronbeeld (None als er geen gezicht is). `gezichten` bevat de twee grootste
    gezichten als dicts {cx, cy, onder, grootte} (grootte = gezichtshoogte), voor de split-screen-beslissing."""
    import cv2

    detect = _detector()
    cap = cv2.VideoCapture(str(bron))
    uit = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        schaal = 640 / w if w > 640 else 1.0
        klein = cv2.resize(frame, None, fx=schaal, fy=schaal) if schaal != 1.0 else frame
        kh, kb = klein.shape[:2]
        gezichten = sorted(detect(klein), key=lambda g: -(g[2] * g[3]))[:2]
        lijst = [{"cx": (x + b / 2) / kb, "cy": (y + gh / 2) / kh, "onder": min(1.0, (y + gh * kin) / kh), "grootte": gh / kh}
                 for x, y, b, gh, kin in gezichten]
        if lijst:
            uit.append((t - start, lijst[0]["cx"], lijst[0]["onder"], lijst))
        else:
            uit.append((t - start, None, None, []))
        t += stap
    cap.release()
    return uit


def split_analyse(posities, min_aandeel: float = 0.6) -> dict | None:
    """Twee mensen naast elkaar in beeld (bijv. een podcast met één camera)? Dan {links, rechts} met de
    gemiddelde positie en grootte van elk gezicht, anders None."""
    paren = []
    for p in posities:
        gezichten = p[3] if len(p) > 3 else []
        if len(gezichten) < 2:
            continue
        a, b = sorted(gezichten[:2], key=lambda g: g["cx"])
        if min(a["grootte"], b["grootte"]) / max(a["grootte"], b["grootte"]) >= 0.5 and b["cx"] - a["cx"] >= 0.25:
            paren.append((a, b))
    if not posities or len(paren) < min_aandeel * len(posities):
        return None

    def gemiddeld(kant: int) -> dict:
        return {k: median(paar[kant][k] for paar in paren) for k in ("cx", "cy", "onder", "grootte")}
    return {"links": gemiddeld(0), "rechts": gemiddeld(1)}


def split_crop(persoon: dict, bron_b: int, bron_h: int) -> tuple[int, int, int, int]:
    """Uitsnede (b, h, x, y) in pixels rond één persoon, in de verhouding 9:8 (één helft van 1080x1920)."""
    ch = min(bron_h, max(int(bron_h * 0.45), int(persoon["grootte"] * bron_h * 3.0)))
    cb = int(ch * 9 / 8)
    if cb > bron_b:
        cb = bron_b
        ch = int(cb * 8 / 9)
    cb, ch = cb - cb % 2, ch - ch % 2
    x = int(persoon["cx"] * bron_b - cb / 2)
    y = int(persoon["cy"] * bron_h - ch * 0.5)  # gezicht in het midden: ruimte boven het hoofd (hook) en voor de schouders
    return cb, ch, max(0, min(bron_b - cb, x)), max(0, min(bron_h - ch, y))


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
