"""Editor (uitvoerend deel): knippen, 9:16 met gezichtsvolging, ondertitels, hook en geluidsnormalisatie."""

from __future__ import annotations

from pathlib import Path

from . import reframe, werk
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


def render_clip(job_dir: Path, clip: dict, modus: str = "auto") -> Path:
    bron = (job_dir / "bron.mp4").resolve()
    info = werk.video_info(bron)
    transcript = werk.lees_json(job_dir / "transcript.json")
    start, end = bepaal_grenzen(clip, transcript, info["duur"] or float(clip["end"]))
    duur = end - start
    if duur < 3:
        raise ValueError(f"Clip {clip['id']} is te kort ({duur:.1f}s)")

    clip_dir = job_dir / "clips" / clip["id"]
    clip_dir.mkdir(parents=True, exist_ok=True)
    woorden = woorden_in(transcript, start, end)
    (clip_dir / "subs.ass").write_text(maak_ass(woorden, start, duur, clip.get("hook", "")), encoding="utf-8")

    W, H = info["breedte"], info["hoogte"]
    breed = W / max(H, 1) > 9 / 16 + 0.01
    segmenten = None
    if breed and modus in ("auto", "volg"):
        posities = reframe.gezicht_posities(bron, start, end)
        gevonden = sum(1 for _, x in posities if x is not None)
        if modus == "volg" or gevonden >= 0.3 * max(len(posities), 1):
            segmenten = reframe.crop_segmenten(posities, duur)
            modus = "volg"
        else:
            modus = "vol"
    elif modus == "auto":
        modus = "vol"

    if modus == "volg" and breed:
        crop_w = even(H * 9 / 16)
        x = reframe.crop_x_expressie(segmenten or [(0.0, 0.5)], W, crop_w)
        filter_args = ["-vf", f"crop={crop_w}:{H}:{x}:0,scale=1080:1920:flags=lanczos,setsar=1,ass=subs.ass"]
    else:
        modus = "vol"
        graaf = (
            "[0:v]split=2[a][b];"
            "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.08[bg];"
            "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,ass=subs.ass[v]"
        )
        filter_args = ["-filter_complex", graaf, "-map", "[v]", "-map", "0:a?"]

    cmd = [
        werk.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(bron), "-t", f"{duur:.3f}",
        *filter_args,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-movflags", "+faststart", "video.mp4",
    ]
    werk.draai(cmd, cwd=clip_dir)
    werk.schrijf_json(clip_dir / "render.json", {
        "start": round(start, 2), "end": round(end, 2), "duur": round(duur, 2),
        "modus": modus, "crop_segmenten": segmenten,
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
