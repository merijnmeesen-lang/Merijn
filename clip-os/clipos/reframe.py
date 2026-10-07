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
        yunet = cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), 0.55)

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


KLEIN = (64, 36)  # mini-beeldjes voor het vinden van camerawissels


def knippen_uit_beelden(beelden, fps: float, duur: float, min_verschil: float = 8.0, factor: float = 5.0) -> list[float]:
    """Camerawissels vinden in mini-beeldjes (elk frame, 64x36): een knip is een sprong die veel groter is dan
    het gewone verschil tussen frames in de seconde eromheen. Werkt ook als twee camerahoeken op elkaar lijken
    (donkere studio), waar de vaste drempel van ffmpeg's scènedetectie knippen mist."""
    import numpy as np

    if len(beelden) < 3 or not fps:
        return []
    d = np.abs(np.diff(beelden.astype(np.int16), axis=0)).mean(axis=(1, 2, 3))
    venster = max(2, int(round(fps)))
    uit: list[float] = []
    for i, x in enumerate(d):
        if x < min_verschil or x < d[max(0, i - 2): i + 3].max():
            continue  # te klein, of niet de piek
        buren = np.concatenate([d[max(0, i - venster): max(0, i - 1)], d[i + 2: i + 2 + venster]])
        basis = float(np.median(buren)) if len(buren) else 0.0
        if x >= factor * max(basis, 1.0):
            t = (i + 1) / fps
            if 0.2 < t < duur - 0.1 and (not uit or t - uit[-1] > 0.4):  # flits/overgang telt als één
                uit.append(round(t, 3))
    return uit


def _mini(raw: bytes):
    import numpy as np

    b, h = KLEIN
    n = len(raw) // (b * h * 3)
    return np.frombuffer(raw[: n * b * h * 3], np.uint8).reshape(n, h, b, 3)


def shot_grenzen(bron: Path, start: float, end: float) -> list[float]:
    """Tijden (t.o.v. clipstart) waarop de camera wisselt naar een ander shot."""
    import subprocess

    from . import werk

    fps = werk.video_info(bron)["fps"] or 30.0
    cmd = [werk.ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
           "-i", str(bron), "-an", "-vf", f"scale={KLEIN[0]}:{KLEIN[1]}:flags=area,format=rgb24", "-f", "rawvideo", "-"]
    res = subprocess.run(cmd, capture_output=True)
    return knippen_uit_beelden(_mini(res.stdout), fps, end - start)


def analyseer(bron: Path, start: float, end: float, breedte: int | None = None, hoogte: int | None = None,
              fps: float | None = None, per_seconde: int = 4) -> tuple[list[float], list[tuple]]:
    """Eén keer door de clip heen: camerawissels én gezichten tegelijk.

    ffmpeg decodeert de clip één keer. Elk frame gaat als mini-beeldje naar de knip-detectie (exacte tijden),
    en `per_seconde` beelden per seconde (960 breed) gaan naar de gezichtsdetector. Veel sneller dan voor elke
    meting apart naar een tijdstip in de video springen. Geeft (knippen, posities)."""
    import os
    import subprocess
    import tempfile

    import numpy as np

    from . import werk

    if not (breedte and hoogte and fps):
        info = werk.video_info(bron)
        breedte, hoogte, fps = info["breedte"], info["hoogte"], info["fps"] or 30.0
    bb = min(960, breedte - breedte % 2)
    bh = max(2, int(round(hoogte * bb / breedte / 2)) * 2)
    graaf = (f"[0:v]split=2[s][f];[s]scale={KLEIN[0]}:{KLEIN[1]}:flags=area,format=rgb24[sv];"
             f"[f]fps={per_seconde},scale={bb}:{bh}[fv]")
    fd, mini_pad = tempfile.mkstemp(suffix=".rgb")
    os.close(fd)
    cmd = [werk.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
           "-i", str(bron), "-an", "-filter_complex", graaf,
           "-map", "[sv]", "-f", "rawvideo", mini_pad, "-map", "[fv]", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    detect = _detector()
    posities: list[tuple] = []
    grootte = bb * bh * 3
    try:
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log, stdin=subprocess.DEVNULL)
            k = 0
            while True:
                buf = proc.stdout.read(grootte)
                if len(buf) < grootte:
                    break
                posities.append(_meting(k / per_seconde, np.frombuffer(buf, np.uint8).reshape(bh, bb, 3), detect))
                k += 1
            proc.stdout.close()
            proc.wait()
        with open(mini_pad, "rb") as f:
            knippen = knippen_uit_beelden(_mini(f.read()), fps, end - start)
    finally:
        try:
            os.unlink(mini_pad)
        except OSError:
            pass
    return knippen, posities


def _meting(t: float, beeld, detect) -> tuple:
    kh, kb = beeld.shape[:2]
    gezichten = sorted(detect(beeld), key=lambda g: -(g[2] * g[3]))[:2]
    lijst = [{"cx": (x + b / 2) / kb, "cy": (y + gh / 2) / kh, "onder": min(1.0, (y + gh * kin) / kh), "grootte": gh / kh}
             for x, y, b, gh, kin in gezichten]
    if lijst:
        return (round(t, 3), lijst[0]["cx"], lijst[0]["onder"], lijst)
    return (round(t, 3), None, None, [])


def gezicht_posities(bron: Path, start: float, end: float, stap: float = 0.5, knippen: list[float] | None = None) -> list[tuple]:
    """Per meting: (tijd t.o.v. clipstart, x-midden grootste gezicht, onderkant grootste gezicht incl. kin, gezichten).

    Alles als fracties 0..1 van het bronbeeld (None als er geen gezicht is). `gezichten` bevat de twee grootste
    gezichten als dicts {cx, cy, onder, grootte} (grootte = gezichtshoogte), voor de split-screen-beslissing."""
    import cv2

    detect = _detector()
    cap = cv2.VideoCapture(str(bron))
    uit = []
    tijden, t = [], 0.0
    while t < end - start:
        tijden.append(round(t, 3))
        t += stap
    tijden = sorted(set(tijden) | {round(k + 0.15, 3) for k in (knippen or []) if k + 0.15 < end - start})
    for t in tijden:
        t = start + t
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        w = frame.shape[1]
        schaal = 960 / w if w > 960 else 1.0  # 960 breed: ook kleinere gezichten verderop in beeld
        klein = cv2.resize(frame, None, fx=schaal, fy=schaal) if schaal != 1.0 else frame
        uit.append(_meting(t - start, klein, detect))
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


def split_crop(persoon: dict, bron_b: int, bron_h: int, ch: int | None = None) -> tuple[int, int, int, int]:
    """Uitsnede (b, h, x, y) in pixels rond één persoon, in de verhouding 9:8 (één helft van 1080x1920)."""
    ch = ch or min(bron_h, max(int(bron_h * 0.45), int(persoon["grootte"] * bron_h * 3.0)))
    cb = int(ch * 9 / 8)
    if cb > bron_b:
        cb = bron_b
        ch = int(cb * 8 / 9)
    cb, ch = cb - cb % 2, ch - ch % 2
    x = int(persoon["cx"] * bron_b - cb / 2)
    y = int(persoon["cy"] * bron_h - ch * 0.5)  # gezicht in het midden: ruimte boven het hoofd (hook) en voor de schouders
    return cb, ch, max(0, min(bron_b - cb, x)), max(0, min(bron_h - ch, y))


def _volg_shot(shot, begin: float, drempel: float, venster: int, min_gezicht: float) -> list[tuple[float, float | None]]:
    """Uitsnede-posities binnen één camerashot. Geen (of bijna geen) gezicht: [(begin, None)]."""
    gevonden = [p[1] for p in shot if p[1] is not None]
    if len(gevonden) < max(1, min_gezicht * len(shot)):
        return [(begin, None)]
    xs, laatste = [], None
    for p in shot:
        laatste = p[1] if p[1] is not None else laatste
        xs.append(laatste)
    xs = [gevonden[0] if x is None else x for x in xs]
    half = venster // 2
    glad = [median(xs[max(0, i - half): i + half + 1]) for i in range(len(xs))]
    huidig = glad[0]
    uit = [(begin, huidig)]
    for i in range(1, len(glad)):
        volgende = glad[i + 1] if i + 1 < len(glad) else glad[i]
        if abs(glad[i] - huidig) > drempel and abs(volgende - huidig) > drempel:
            huidig = glad[i]
            uit.append((shot[i][0], huidig))
    return uit


def _shots(posities, duur: float, knippen):
    grenzen = [0.0] + sorted(k for k in (knippen or []) if 0 < k < duur)
    for nr, begin in enumerate(grenzen):
        eind = grenzen[nr + 1] if nr + 1 < len(grenzen) else float("inf")
        yield begin, [p for p in posities if begin <= p[0] < eind]


def _samenvoegen(segmenten, drempel: float):
    samen = [segmenten[0]]
    for t, x in segmenten[1:]:
        vorige = samen[-1][1]
        if x is not None and vorige is not None and abs(x - vorige) <= drempel / 2:
            continue
        if x is None and vorige is None:
            continue
        samen.append((t, x))
    return samen


def crop_segmenten(posities, duur: float, drempel: float = 0.08, venster: int = 5,
                   knippen: list[float] | None = None, min_gezicht: float = 0.25) -> list[tuple[float, float | None]]:
    """Zet ruwe gezichtsposities om in rustige stukken [(vanaf_tijd, x_fractie of None)].

    - per camerashot apart (`knippen`): een positie wordt nooit meegenomen naar een ander shot, anders
      blijft de uitsnede na een camerawissel hangen op de plek van het vorige gezicht (bijv. een achterhoofd);
    - een shot waarin (bijna) geen gezicht te zien is, krijgt x = None: dan toont de render het hele beeld
      met wazige balken in plaats van een gok;
    - binnen een shot: ontbrekende metingen erven de vorige positie, een mediaanfilter haalt uitschieters weg
      en de uitsnede verspringt pas als het gezicht minstens `drempel` verschuift en dat zo blijft.
    """
    if not posities:
        return [(0.0, 0.5)]
    segmenten: list[tuple[float, float | None]] = []
    for begin, shot in _shots(posities, duur, knippen):
        if shot:
            segmenten += _volg_shot(shot, begin, drempel, venster, min_gezicht)
        elif segmenten:  # shot zonder metingen (heel kort): vorige positie aanhouden
            segmenten.append((begin, segmenten[-1][1]))
    if not segmenten:
        return [(0.0, 0.5)]
    return [(t, x) for t, x in _samenvoegen(segmenten, drempel) if t < duur]


def indeling(posities, duur: float, knippen: list[float] | None = None, split: bool = True,
             drempel: float = 0.08) -> list[dict]:
    """Beeldindeling per camerashot: [{"t", "soort": "volg"|"split"|"vol", ...}].

    - "split": twee mensen naast elkaar in dit shot (bijv. een breed shot) → boven elkaar in beeld;
    - "volg": één persoon → uitsnede volgt het gezicht ("x");
    - "vol": geen gezicht (bijv. over de schouder gefilmd) → het hele beeld met wazige balken."""
    if not posities:
        return [{"t": 0.0, "soort": "volg", "x": 0.5}]
    uit: list[dict] = []
    for begin, shot in _shots(posities, duur, knippen):
        if not shot:
            if uit:
                uit.append({**uit[-1], "t": begin})
            continue
        twee = split_analyse(shot) if split and len(shot) >= 2 else None
        if twee:
            uit.append({"t": begin, "soort": "split", **twee})
            continue
        for t, x in _volg_shot(shot, begin, drempel, 5, 0.25):
            uit.append({"t": t, "soort": "vol", "x": None} if x is None else {"t": t, "soort": "volg", "x": x})
    if not uit:
        return [{"t": 0.0, "soort": "volg", "x": 0.5}]
    samen = [uit[0]]
    for seg in uit[1:]:
        vorige = samen[-1]
        if seg["soort"] == vorige["soort"] == "vol":
            continue
        if seg["soort"] == vorige["soort"] == "volg" and abs(seg["x"] - vorige["x"]) <= drempel / 2:
            continue
        samen.append(seg)
    return [seg for seg in samen if seg["t"] < duur]


def intervallen(lagen: list[dict], soort: str, duur: float) -> list[tuple[float, float]]:
    """Stukken (in clip-tijd) waarin de indeling `soort` geldt."""
    uit = []
    for i, seg in enumerate(lagen):
        if seg["soort"] == soort:
            eind = lagen[i + 1]["t"] if i + 1 < len(lagen) else duur
            if eind > seg["t"]:
                if uit and abs(uit[-1][1] - seg["t"]) < 1e-6:
                    uit[-1] = (uit[-1][0], eind)
                else:
                    uit.append((seg["t"], eind))
    return uit


def stap_expressie(paren: list[tuple[float, int]]) -> str:
    """ffmpeg-expressie die per tijdstip een vaste waarde geeft: [(vanaf_tijd, waarde)]."""
    expr = str(paren[-1][1])
    for i in range(len(paren) - 2, -1, -1):
        expr = f"if(lt(t\\,{paren[i + 1][0]:.3f})\\,{paren[i][1]}\\,{expr})"
    return expr


def geen_gezicht_intervallen(segmenten, duur: float) -> list[tuple[float, float]]:
    """Stukken (in clip-tijd) waarin geen gezicht is: daar het hele beeld met wazige balken."""
    uit = []
    for i, (t, x) in enumerate(segmenten):
        if x is None:
            eind = segmenten[i + 1][0] if i + 1 < len(segmenten) else duur
            if eind > t:
                uit.append((t, eind))
    return uit


HOOK_STANDAARD_Y = 340   # bovenkant van de hook (1080x1920) zonder bekend gezicht: net onder de knoppen van YouTube
HOOK_MAX_Y = 1030        # lager niet: daar beginnen de ondertitels (die eindigen boven de knoppen onderin)


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
    def px(frac: float | None) -> int:
        x = int(round((0.5 if frac is None else frac) * bron_breedte - crop_breedte / 2))
        return max(0, min(bron_breedte - crop_breedte, x))

    expr = str(px(segmenten[-1][1]))
    for i in range(len(segmenten) - 2, -1, -1):
        grens = segmenten[i + 1][0]
        expr = f"if(lt(t\\,{grens:.2f})\\,{px(segmenten[i][1])}\\,{expr})"
    return expr
