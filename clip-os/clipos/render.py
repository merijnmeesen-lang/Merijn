"""Editor (uitvoerend deel): stiltes eruit, 9:16 per shot (gezicht volgen of split-screen), zooms, ondertitels,
hook, pop-up tekst, geluidseffecten en geluid."""

from __future__ import annotations

from pathlib import Path

from . import effecten, reframe, tempo, werk
from .ondertitels import NAAD_HOOK_Y, NAAD_ONDERTITEL, maak_ass
from .transcriptie import woorden_in


def even(n: float) -> int:
    n = int(round(n))
    return n - (n % 2)


def bepaal_grenzen(clip: dict, transcript: dict, bron_duur: float) -> tuple[float, float]:
    """Laat de clip op woordgrenzen beginnen en eindigen (geen afgekapte woorden)."""
    start, end = float(clip["start"]), float(clip["end"])
    woorden = woorden_in(transcript, start, end)
    if woorden:
        start = min(start, woorden[0]["start"]) - 0.08
        end = max(end, woorden[-1]["end"]) + 0.3
    return max(0.0, start), min(bron_duur, end)


PRESET = "faster"    # ±2x sneller dan "medium", maar bewaart fijne details (kleding, haar) beter dan "veryfast"
CRF = "19"           # iets hogere kwaliteit: YouTube comprimeert de video daarna zelf nog een keer
ZOOM_LICHT = 1.07    # lichte zoom na een knip
ZOOM_STERK = 1.10    # zoom op de sterkste zin
POP_NIET_VOOR = 3.2   # geen pop-up tekst zolang de hook in beeld staat


def VOL_BEELD(invoer: str, uitvoer: str, p: str = "") -> list[str]:
    """Het hele (liggende) beeld in het midden, met een wazige, iets donkere versie als achtergrond.
    De waas wordt op een klein beeld berekend en daarna opgeschaald: zelfde effect, veel sneller."""
    return [f"{invoer}split=2[{p}va][{p}vf]",
            f"[{p}va]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=8:2,eq=brightness=-0.08,"
            f"scale=1080:1920:flags=bilinear[{p}bg]",
            f"[{p}vf]scale=1080:1920:force_original_aspect_ratio=decrease[{p}fg]",
            f"[{p}bg][{p}fg]overlay=(W-w)/2:(H-h)/2,setsar=1{uitvoer}"]


def zoom_uitsnede(b: int, h: int, x: int, y: int, factor: float, W: int, H: int) -> tuple[int, int, int, int]:
    """Een kleinere uitsnede uit het origineel voor een zoom: zelfde midden, iets meer ruimte onder dan boven
    (gezichten zitten bovenin). Zo wordt er maar één keer vergroot, in plaats van een al vergroot beeld nog eens."""
    zb, zh = even(b / factor), even(h / factor)
    zx = x + (b - zb) // 2
    zy = y + int((h - zh) * 0.3)
    return zb, zh, max(0, min(W - zb, zx)), max(0, min(H - zh, zy))


def VOLG_BEELD(invoer: str, uitvoer: str, lagen: list[dict], W: int, H: int, factor: float = 1.0) -> list[str]:
    """Uitsnede (9:16) die per stuk het gezicht volgt; met factor > 1 ingezoomd (rechtstreeks uit het origineel)."""
    crop_w = even(H * 9 / 16)
    paren, x, maat = [], 0.5, None
    for seg in lagen:
        if seg["soort"] == "volg":
            x = seg["x"]
        basis_x = max(0, min(W - crop_w, int(round(x * W - crop_w / 2))))
        zb, zh, zx, zy = zoom_uitsnede(crop_w, H, basis_x, 0, factor, W, H)
        maat = (zb, zh, zy)
        paren.append((seg["t"], zx))
    zb, zh, zy = maat
    return [f"{invoer}crop={zb}:{zh}:{reframe.stap_expressie(paren)}:{zy},scale=1080:1920:flags=lanczos,setsar=1{uitvoer}"]


def SPLIT_BEELD(invoer: str, uitvoer: str, lagen: list[dict], W: int, H: int, p: str = "", factor: float = 1.0) -> list[str]:
    """Twee mensen boven elkaar (elk 1080x960); per breed shot een eigen uitsnede, met dezelfde maat."""
    splits = [seg for seg in lagen if seg["soort"] == "split"]
    ch = max(reframe.split_crop(splits[0][kant], W, H)[1] for kant in ("links", "rechts"))
    paren: dict = {"links": [], "rechts": []}
    vorige: dict = {}
    maat = None
    for seg in lagen:
        for kant in ("links", "rechts"):
            if seg["soort"] == "split":
                vorige[kant] = reframe.split_crop(seg[kant], W, H, ch=ch)
            cb, ch_, x, y = vorige.get(kant) or reframe.split_crop(splits[0][kant], W, H, ch=ch)
            zb, zh, zx, zy = zoom_uitsnede(cb, ch_, x, y, factor, W, H)
            maat = (zb, zh)
            paren[kant].append((seg["t"], zx, zy))
    zb, zh = maat

    def crop(kant: str) -> str:
        xs = reframe.stap_expressie([(t, x) for t, x, _ in paren[kant]])
        ys = reframe.stap_expressie([(t, y) for t, _, y in paren[kant]])
        return f"crop={zb}:{zh}:{xs}:{ys},scale=1080:960:flags=lanczos,setsar=1"
    return [f"{invoer}split=2[{p}s1][{p}s2]", f"[{p}s1]{crop('links')}[{p}boven]", f"[{p}s2]{crop('rechts')}[{p}onder]",
            f"[{p}boven][{p}onder]vstack=inputs=2{uitvoer}"]


def samenstelling(ingangen: list[str], uitvoer: str, soorten: list[str], lagen: list[dict], iv: dict,
                  W: int, H: int, factor: float, p: str) -> list[str]:
    """Eén compleet 9:16-beeld: de eerste indeling als basis, de andere eroverheen op de momenten dat ze gelden."""
    maak = {"volg": lambda i, o: VOLG_BEELD(i, o, lagen, W, H, factor),
            "split": lambda i, o: SPLIT_BEELD(i, o, lagen, W, H, p=f"{p}sp", factor=factor),
            "vol": lambda i, o: VOL_BEELD(i, o, p=f"{p}vl")}
    if len(soorten) == 1:
        return maak[soorten[0]](ingangen[0], uitvoer)
    graaf = maak[soorten[0]](ingangen[0], f"[{p}lg0]")
    for i, soort in enumerate(soorten[1:], start=1):
        graaf += maak[soort](ingangen[i], f"[{p}lb{i}]")
        uit = uitvoer if i == len(soorten) - 1 else f"[{p}lg{i}]"
        graaf.append(f"[{p}lg{i - 1}][{p}lb{i}]overlay=0:0:enable={tempo.tijd_expressie(iv[soort])}{uit}")
    return graaf


def lagen_naar_cliptijd(lagen: list[dict], start: float, stukken) -> list[dict]:
    """Indeling-tijden (t.o.v. het begin in de bron) omrekenen naar de ingekorte clip."""
    uit: list[dict] = []
    for seg in lagen:
        t = round(tempo.remap(start + seg["t"], stukken), 3)
        if uit and t <= uit[-1]["t"] + 1e-6:
            uit[-1] = {**seg, "t": uit[-1]["t"]}  # stuk valt helemaal in een weggeknipte pauze
        else:
            uit.append({**seg, "t": t})
    uit[0]["t"] = 0.0
    return uit


def overlapt(a: tuple[float, float], lijst: list[tuple[float, float]]) -> bool:
    return any(a[0] < b[1] and b[0] < a[1] for b in lijst)


def render_clip(job_dir: Path, clip: dict, modus: str = "auto", montage: dict | None = None) -> Path:
    """Maak één clip: knippen (stiltes eruit), 9:16 (per shot: gezicht volgen / twee mensen boven elkaar /
    wazige balken), zooms, ondertitels met hook en pop-up tekst, geluidseffecten, en geluid op YouTube-niveau."""
    montage = {**werk.montage_instellingen(), **(montage or {})}
    bron = (job_dir / "bron.mp4").resolve()
    info = werk.video_info(bron)
    transcript = werk.lees_json(job_dir / "transcript.json")
    start, end = bepaal_grenzen(clip, transcript, info["duur"] or float(clip["end"]))
    if end - start < 3:
        raise ValueError(f"Clip {clip['id']} is te kort ({end - start:.1f}s)")

    clip_dir = job_dir / "clips" / clip["id"]
    clip_dir.mkdir(parents=True, exist_ok=True)
    woorden = woorden_in(transcript, start, end)

    # 1. tempo: welke stukken blijven staan
    if montage["stiltes_eruit"] and woorden:
        stukken = tempo.bewaar_segmenten(woorden, start, end, max_stilte=float(montage["max_stilte"]))
    else:
        stukken = [(start, end)]
    geknipt = len(stukken) > 1 or stukken[0] != (start, end)
    duur = tempo.nieuwe_duur(stukken)

    # 2. beeldindeling, per camerashot
    W, H = info["breedte"], info["hoogte"]
    breed = W / max(H, 1) > 9 / 16 + 0.01
    hook_top, onder_pos, lagen, posities, knippen_bron = reframe.HOOK_STANDAARD_Y, None, [], [], []
    if breed and modus in ("auto", "volg", "split"):
        knippen_bron, posities = reframe.analyseer(bron, start, end, W, H, info["fps"] or 30.0)
        gevonden = sum(1 for p in posities if p[1] is not None) / max(len(posities), 1)
        ruw = reframe.indeling(posities, end - start, knippen_bron,
                               split=(montage["split_screen"] or modus == "split") and modus != "volg")
        soorten = {seg["soort"] for seg in ruw}
        if soorten <= {"vol"} or (gevonden < 0.3 and "split" not in soorten and modus != "volg"):
            modus = "vol"
        else:
            lagen = lagen_naar_cliptijd(ruw, start, stukken)
            modus = "split" if soorten == {"split"} else "mix" if "split" in soorten else "volg"
    else:
        modus = "vol"
    split_iv = reframe.intervallen(lagen, "split", duur) if lagen else []
    vol_iv = reframe.intervallen(lagen, "vol", duur) if lagen else []
    eerste = lagen[0]["soort"] if lagen else "vol"
    if eerste == "split":
        hook_top = NAAD_HOOK_Y  # op de naad tussen de twee sprekers (bovenin zitten de knoppen van YouTube)
    elif eerste == "volg":
        hook_top = reframe.hook_y(posities)
    if modus == "split":
        onder_pos = NAAD_ONDERTITEL

    # 3. pop-up tekst bij sterke getallen of woorden (door Claude gekozen, anders automatisch)
    popups = []
    if montage.get("popup_tekst", True):
        volg_y = min(1100, reframe.hook_y(posities, hook_duur=end - start) + 70) if posities else 1000
        for pop in effecten.popup_lijst(clip.get("kernwoorden"), woorden, start, end):
            t = tempo.remap(pop["t"], stukken)
            if POP_NIET_VOOR <= t <= duur - 0.6:
                soort = next((seg["soort"] for seg in reversed(lagen) if seg["t"] <= t), eerste)
                popups.append((round(t, 3), pop["tekst"], {"split": 1170, "vol": 470}.get(soort, volg_y)))

    # 4. ondertitels en hook (tijden in de ingekorte clip)
    woorden_nieuw = tempo.remap_woorden(woorden, stukken)
    (clip_dir / "subs.ass").write_text(
        maak_ass(woorden_nieuw, 0.0, duur, clip.get("hook", ""), hook_y=hook_top, onder_pos=onder_pos,
                 hook_onderkant=eerste == "split",
                 split_intervallen=split_iv if modus == "mix" else None, popups=popups), encoding="utf-8")

    # 5. filtergraaf: beeld
    graaf, v, a = [], "[0:v]", "[0:a]" if info["audio"] else None
    if geknipt:
        sel = tempo.select_expressie(stukken, start)
        graaf.append(f"[0:v]select={sel},setpts=N/FRAME_RATE/TB[vk]")
        v = "[vk]"
        if a:
            graaf.append(f"[0:a]aselect={sel},asetpts=N/SR/TB[ak]")
            a = "[ak]"
    punch, sterk = ([], [])
    if montage["zoom"] and modus != "vol":
        punch, sterk = tempo.zoom_intervallen(stukken, clip.get("nadruk") or [], duur)
        punch = [z for z in punch if not overlapt(z, vol_iv)]
        sterk = [z for z in sterk if not overlapt(z, vol_iv)]
    if modus == "vol":
        graaf += VOL_BEELD(v, "[vb]")
    else:
        # basisbeeld + per zoomniveau een ingezoomde versie, elk rechtstreeks uit het origineel gesneden
        soorten = [s_ for s_ in ("volg", "split", "vol") if any(seg["soort"] == s_ for seg in lagen)]
        zoom_soorten = [s_ for s_ in soorten if s_ != "vol"]
        zooms = [(naam, factor, iv_) for naam, factor, iv_ in (("p", ZOOM_LICHT, punch), ("n", ZOOM_STERK, sterk)) if iv_]
        iv = {"split": split_iv, "vol": vol_iv}
        aantal = len(soorten) + len(zooms) * len(zoom_soorten)
        ingangen = [f"[in{i}]" for i in range(aantal)] if aantal > 1 else [v]
        if aantal > 1:
            graaf.append(f"{v}split={aantal}" + "".join(ingangen))
        uit = "[vb]" if not zooms else "[vz0]"
        graaf += samenstelling(ingangen[:len(soorten)], uit, soorten, lagen, iv, W, H, 1.0, "b")
        rest = ingangen[len(soorten):]
        for k, (naam, factor, intervallen) in enumerate(zooms):
            graaf += samenstelling(rest[:len(zoom_soorten)], f"[{naam}z]", zoom_soorten, lagen, iv, W, H, factor, naam)
            rest = rest[len(zoom_soorten):]
            volgende = "[vb]" if k == len(zooms) - 1 else f"[vz{k + 1}]"
            graaf.append(f"[vz{k}][{naam}z]overlay=0:0:enable={tempo.tijd_expressie(intervallen)}{volgende}")
    v = "[vb]"
    graaf.append(f"{v}ass=subs.ass[vuit]")

    # 7. geluid: geluidseffecten onder de spraak, daarna op YouTube-volume
    extra_inputs, geluiden = [], {}
    if a:
        if montage.get("geluidseffecten", True) and modus != "vol":
            boem = effecten.momenten([t for t, _, _ in popups] + [z[0] for z in sterk], duur, effecten.MIN_AFSTAND["boem"])
            wissels = [seg["t"] for seg in lagen[1:]] + [z[0] for z in punch]
            whoosh = effecten.momenten([t for t in wissels if all(abs(t - b) > 0.6 for b in boem)], duur,
                                       effecten.MIN_AFSTAND["whoosh"])
            geluiden = {"whoosh": whoosh, "boem": boem}
            filters, extra_inputs, a = effecten.audio_graaf(a, geluiden, eerste_input=1)
            graaf += filters
        graaf.append(f"{a}loudnorm=I=-14:TP=-1.5:LRA=11[auit]")

    cmd = [werk.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(bron),
           *[x for pad in extra_inputs for x in ("-i", str(pad))],
           "-filter_complex", ";".join(graaf), "-map", "[vuit]", *(["-map", "[auit]"] if a else []),
           "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-tune", "film", "-pix_fmt", "yuv420p",
           *(["-c:a", "aac", "-b:a", "160k", "-ar", "48000"] if a else []),
           "-movflags", "+faststart", "video.mp4"]
    werk.draai(cmd, cwd=clip_dir)
    werk.schrijf_json(clip_dir / "render.json", {
        "start": round(start, 2), "end": round(end, 2), "duur": round(duur, 2), "bron_duur": round(end - start, 2),
        "ingekort": round(end - start - duur, 1), "knippen": len(stukken) - 1, "modus": modus,
        "indeling": [{k: (round(x, 3) if isinstance(x, float) else x) for k, x in seg.items() if k in ("t", "soort", "x")}
                     for seg in lagen],
        "camerawissels": len(knippen_bron), "hook_y": hook_top,
        "shots_zonder_gezicht": len(vol_iv), "split_stukken": len(split_iv),
        "zooms": len(punch) + len(sterk), "popups": [[t, tekst] for t, tekst, _ in popups],
        "geluidseffecten": sum(len(x) for x in geluiden.values()),
    })
    return clip_dir / "video.mp4"


def frames(video: Path, doel: Path) -> list[Path]:
    """Drie stilstaande beelden (begin/midden/eind) voor de visuele controle."""
    duur = werk.video_info(video)["duur"]
    uit = []
    for naam, t in (("begin", 0.8), ("midden", duur / 2), ("eind", max(duur - 1.0, 0))):
        pad = doel / f"frame_{naam}.jpg"
        werk.draai([werk.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
                    "-frames:v", "1", "-vf", "scale=540:960", str(pad)])
        uit.append(pad)
    return uit
