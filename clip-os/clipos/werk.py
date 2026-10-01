"""Gedeelde hulpfuncties: mappen, jobs, ffmpeg en video-info."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "jobs"
OUTPUT = ROOT / "output"
BRIEFS = ROOT / "briefs"
DATA = ROOT / "data"


PERSOONLIJK = {"config.json": "config.voorbeeld.json", "lessenboek.md": "lessenboek.voorbeeld.md"}


def standaardbestanden() -> None:
    """Je eigen instellingen staan niet in git (dan overschrijft een update ze nooit).
    Ontbreken ze, dan worden ze aangemaakt vanuit het voorbeeld."""
    for eigen, voorbeeld in PERSOONLIJK.items():
        if not (ROOT / eigen).exists() and (ROOT / voorbeeld).exists():
            shutil.copy2(ROOT / voorbeeld, ROOT / eigen)


MONTAGE_STANDAARD = {"stiltes_eruit": True, "max_stilte": 0.4, "zoom": True, "split_screen": True}


def montage_instellingen() -> dict:
    """Montage-opties uit config.json (Instellingen → Montage), met veilige standaardwaarden."""
    standaardbestanden()
    try:
        eigen = lees_json(ROOT / "config.json").get("montage") or {}
    except (OSError, ValueError):
        eigen = {}
    return {**MONTAGE_STANDAARD, **{k: eigen[k] for k in MONTAGE_STANDAARD if k in eigen}}


def systeemcertificaten() -> None:
    """Gebruik de certificaten van Windows/macOS in plaats van Pythons eigen lijst.

    Antivirus (bijv. Norton) of een school-/bedrijfsnetwerk controleert HTTPS met een eigen
    certificaat dat alleen in het systeem staat; zonder dit krijg je CERTIFICATE_VERIFY_FAILED.
    De beveiligingscontrole blijft gewoon aan (zo doet pip het ook)."""
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass


def ytdlp_opties(**extra) -> dict:
    """Standaardopties voor yt-dlp: stil, en de certificaten van het systeem gebruiken."""
    return {"quiet": True, "no_warnings": True, "compat_opts": ["no-certifi"], **extra}


def ffmpeg() -> str:
    """Systeem-ffmpeg als die er is, anders de gratis meegeleverde van imageio-ffmpeg."""
    pad = shutil.which("ffmpeg")
    if pad:
        return pad
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def draai(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Commando mislukt ({res.returncode}): {' '.join(cmd[:4])} …\n{res.stderr[-2000:]}")
    return res


def video_info(pad: Path) -> dict:
    """Breedte, hoogte, fps, duur en of er audio is (via ffmpeg -i, geen ffprobe nodig)."""
    res = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(pad)], capture_output=True, text=True)
    err = res.stderr
    info = {"breedte": 0, "hoogte": 0, "fps": 0.0, "duur": 0.0, "audio": " Audio:" in err}
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if m:
        info["duur"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        info["breedte"], info["hoogte"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?) fps", err)
    if m:
        info["fps"] = float(m.group(1))
    return info


def slug(tekst: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", tekst.lower()).strip("-")
    return s[:max_len].strip("-") or "clip"


def nieuwe_job_id(naam: str) -> str:
    return datetime.now().strftime("%Y%m%d-%H%M") + "-" + slug(naam, 30)


def job_map(job: str) -> Path:
    pad = JOBS / job
    if not pad.is_dir():
        bestaand = ", ".join(sorted(p.name for p in JOBS.glob("*") if p.is_dir())[-5:]) or "geen"
        raise SystemExit(f"Job '{job}' bestaat niet. Recente jobs: {bestaand}")
    return pad


def lees_json(pad: Path) -> dict:
    return json.loads(pad.read_text(encoding="utf-8"))


def schrijf_json(pad: Path, data) -> None:
    pad.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def lees_brief(naam: str | None) -> dict:
    """Campagne-brief laden; zonder brief gelden veilige standaardwaarden."""
    standaard = {
        "naam": "geen-campagne",
        "platform": "",
        "min_seconden": 15,
        "max_seconden": 60,
        "verplichte_hashtags": [],
        "verplichte_tekst": [],
        "verboden": [],
        "taal": None,
    }
    if not naam:
        return standaard
    pad = BRIEFS / (naam if naam.endswith(".json") else naam + ".json")
    if not pad.exists():
        raise SystemExit(f"Brief '{pad.name}' niet gevonden in {BRIEFS}")
    return {**standaard, **lees_json(pad)}


def tijd(sec: float) -> str:
    m, s = divmod(max(sec, 0), 60)
    return f"{int(m):02d}:{s:04.1f}"
