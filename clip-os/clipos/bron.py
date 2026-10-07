"""Bron-agent (uitvoerend deel): video binnenhalen via link of lokaal bestand."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import werk


# Liefst 1440p: uit een liggende video wordt een staand stuk gesneden en soms ingezoomd. Met meer pixels in de bron
# hoeft er (bijna) niets opgerekt te worden, dus scherpere video's. AV1 slaan we over: dat is zwaar om te decoderen
# en niet elke ffmpeg kan het. Is er geen 1440p, dan gewoon de beste tot 1080p.
FORMAAT = ("bv*[height<=1440][vcodec!^=av01]+ba/b[height<=1440][vcodec!^=av01]"
           "/bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b")


def haal_binnen(bron: str, job_dir: Path) -> Path:
    doel = job_dir / "bron.mp4"
    lokaal = Path(bron).expanduser()
    if lokaal.exists():
        shutil.copy2(lokaal, doel)
        return doel

    import yt_dlp  # gratis; draait in dit proces, dus het netwerk-slot geldt ook hier

    opties = werk.ytdlp_opties(
        outtmpl=str(job_dir / "bron.%(ext)s"),
        format=FORMAAT,
        merge_output_format="mp4",
        ffmpeg_location=werk.ffmpeg(),
        noplaylist=True,
    )
    with yt_dlp.YoutubeDL(opties) as ydl:
        info = ydl.extract_info(bron, download=True)
    werk.schrijf_json(job_dir / "bron_info.json", {
        "titel": info.get("title"),
        "kanaal": info.get("channel") or info.get("uploader"),
        "url": info.get("webpage_url", bron),
        "duur": info.get("duration"),
    })
    if not doel.exists():
        kandidaten = [p for p in job_dir.glob("bron.*") if p.suffix != ".json"]
        if not kandidaten:
            raise SystemExit("Download mislukt: geen videobestand gevonden.")
        kandidaten[0].rename(doel)
    return doel
