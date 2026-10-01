"""Editor (uitvoerend deel): stiltes eruit, 9:16 (gezicht volgen of split-screen), zooms, ondertitels, hook en geluid."""

from __future__ import annotations

from pathlib import Path

from . import reframe, tempo, werk
from .ondertitels import maak_ass
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


def render_clip(job_dir: Path, clip: dict, modus: str = "auto", montage: dict | None = None) -> Path:
    """Maak één clip: knippen (stiltes eruit), 9:16 (gezicht volgen / split-screen / wazige balken),
    zooms, ondertitels met hook, en geluid op YouTube-niveau."""
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

    # 2. beeldindeling
    W, H = info["breedte"], info["hoogte"]
    breed = W / max(H, 1) > 9 / 16 + 0.01
    hook_top, onder_pos, crop_segmenten, split = reframe.HOOK_STANDAARD_Y, None, None, None
    if breed and modus in ("auto", "volg", "split"):
        posities = reframe.gezicht_posities(bron, start, end)
        gevonden = sum(1 for p in posities if p[1] is not None)
        split = reframe.split_analyse(posities) if (montage["split_screen"] or modus == "split") and modus != "volg" else None
        if split:
            modus, hook_top, onder_pos = "split", 40, (540, 960)
        elif modus == "volg" or gevonden >= 0.3 * max(len(posities), 1):
            ruw = reframe.crop_segmenten(posities, end - start)
            crop_segmenten = [(round(tempo.remap(start + t, stukken), 3), x) for t, x in ruw]
            hook_top = reframe.hook_y(posities)
            modus = "volg"
        else:
            modus = "vol"
    else:
        modus = "vol"

    # 3. ondertitels en hook (tijden in de ingekorte clip)
    woorden_nieuw = tempo.remap_woorden(woorden, stukken)
    (clip_dir / "subs.ass").write_text(
        maak_ass(woorden_nieuw, 0.0, duur, clip.get("hook", ""), hook_y=hook_top, onder_pos=onder_pos), encoding="utf-8")

    # 4. filtergraaf
    graaf, v, a = [], "[0:v]", "[0:a]" if info["audio"] else None
    if geknipt:
        sel = tempo.select_expressie(stukken, start)
        graaf.append(f"[0:v]select={sel},setpts=N/FRAME_RATE/TB[vk]")
        v = "[vk]"
        if a:
            graaf.append(f"[0:a]aselect={sel},asetpts=N/SR/TB[ak]")
            a = "[ak]"
    if modus == "volg":
        crop_w = even(H * 9 / 16)
        x = reframe.crop_x_expressie(crop_segmenten or [(0.0, 0.5)], W, crop_w)
        graaf.append(f"{v}crop={crop_w}:{H}:{x}:0,scale=1080:1920:flags=lanczos,setsar=1[vb]")
    elif modus == "split":
        cb1, ch1, x1, y1 = reframe.split_crop(split["links"], W, H)
        cb2, ch2, x2, y2 = reframe.split_crop(split["rechts"], W, H)
        graaf += [f"{v}split=2[s1][s2]",
                  f"[s1]crop={cb1}:{ch1}:{x1}:{y1},scale=1080:960:flags=lanczos,setsar=1[boven]",
                  f"[s2]crop={cb2}:{ch2}:{x2}:{y2},scale=1080:960:flags=lanczos,setsar=1[onder]",
                  "[boven][onder]vstack=inputs=2[vb]"]
    else:
        graaf += [f"{v}split=2[va][vf]",
                  "[va]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.08[bg]",
                  "[vf]scale=1080:1920:force_original_aspect_ratio=decrease[fg]",
                  "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[vb]"]
    v = "[vb]"

    # 5. zooms (alleen als het beeld gevuld is; bij wazige balken niet)
    punch, sterk = ([], [])
    if montage["zoom"] and modus in ("volg", "split"):
        punch, sterk = tempo.zoom_intervallen(stukken, clip.get("nadruk") or [], duur)
        for naam, intervallen, factor in (("p", punch, 1.07), ("n", sterk, 1.15)):
            if not intervallen:
                continue
            zb, zh = even(1080 * factor), even(1920 * factor)
            graaf += [f"{v}split=2[{naam}0][{naam}1]",
                      f"[{naam}1]scale={zb}:{zh}:flags=lanczos,crop=1080:1920:{(zb - 1080) // 2}:{int((zh - 1920) * 0.3)}[{naam}z]",
                      f"[{naam}0][{naam}z]overlay=0:0:enable={tempo.tijd_expressie(intervallen)}[{naam}v]"]
            v = f"[{naam}v]"
    graaf.append(f"{v}ass=subs.ass[vuit]")
    if a:
        graaf.append(f"{a}loudnorm=I=-14:TP=-1.5:LRA=11[auit]")

    cmd = [werk.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-i", str(bron), "-t", f"{end - start:.3f}",
           "-filter_complex", ";".join(graaf), "-map", "[vuit]", *(["-map", "[auit]"] if a else []),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           *(["-c:a", "aac", "-b:a", "160k", "-ar", "48000"] if a else []),
           "-movflags", "+faststart", "video.mp4"]
    werk.draai(cmd, cwd=clip_dir)
    werk.schrijf_json(clip_dir / "render.json", {
        "start": round(start, 2), "end": round(end, 2), "duur": round(duur, 2), "bron_duur": round(end - start, 2),
        "ingekort": round(end - start - duur, 1), "knippen": len(stukken) - 1, "modus": modus,
        "crop_segmenten": crop_segmenten, "split": split, "hook_y": hook_top,
        "zooms": len(punch) + len(sterk),
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
