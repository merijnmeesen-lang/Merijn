"""Transcriptie met faster-whisper: lokaal, gratis, met tijd per woord."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import werk


SAMPLERATE = 16000


def laad_audio(bron: Path):
    """Geluid uit de video halen met ffmpeg (16 kHz mono, float32), zoals faster-whisper het wil.

    Bewust niet via faster-whisper zelf: dat gebruikt PyAV, en nieuwe PyAV-versies (bijv. bij de
    nieuwste Python op Windows) passen niet meer bij faster-whisper ('metadata_errors'-fout)."""
    import numpy as np

    cmd = [werk.ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(bron),
           "-vn", "-ac", "1", "-ar", str(SAMPLERATE), "-f", "f32le", "-"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        raise RuntimeError("Geluid uit de video halen mislukt: " + res.stderr.decode("utf-8", "replace")[-300:])
    return np.frombuffer(res.stdout, dtype=np.float32)


def threads() -> int:
    """Aantal rekenkernen voor het spraakmodel. Standaard gebruikt faster-whisper er maar 4."""
    n = os.cpu_count() or 4
    return max(2, n // 2) if n >= 8 else n  # bij hyperthreading: één per echte kern is het snelst


def snel_aan() -> bool:
    try:
        return bool(werk.lees_json(werk.ROOT / "config.json").get("snel_uitschrijven", True))
    except (OSError, ValueError):
        return True


def _verzamel(segmenten, info) -> dict:
    data = {"taal": info.language, "duur": info.duration, "segmenten": []}
    laatst = -1
    for seg in segmenten:
        data["segmenten"].append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "tekst": seg.text.strip(),
            "woorden": [
                {"start": round(w.start, 2), "end": round(w.end, 2), "woord": w.word.strip()}
                for w in (seg.words or [])
                if w.word.strip()
            ],
        })
        pct = int(seg.end / max(info.duration, 1) * 100) // 5 * 5
        if pct > laatst:
            print(f"⏱ {pct}% uitgeschreven ({werk.tijd(seg.end)} van {werk.tijd(info.duration)})", flush=True)
            laatst = pct
    data["segmenten"].sort(key=lambda s: s["start"])
    return data


def transcribeer(job_dir: Path, model: str = "small", taal: str | None = None, snel: bool | None = None) -> Path:
    """Spraak → tekst met tijd per woord.

    Snel (standaard): meerdere stukken audio tegelijk door het model (faster-whisper 'batched') en één zoekpad
    (beam 1). Ongeveer 3x sneller dan de oude manier, met nagenoeg dezelfde tekst. Lukt dat niet, dan valt
    Clip-OS vanzelf terug op de oude manier. Uit te zetten in Instellingen (Snel uitschrijven)."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # onschuldige Windows-waarschuwing
    from faster_whisper import WhisperModel

    bron = job_dir / "bron.mp4"
    print("Geluid uit de video halen…", flush=True)
    audio = laad_audio(bron)
    print(f"Spraakmodel '{model}' laden (eerste keer: eenmalige gratis download)…", flush=True)
    wm = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads())
    opties = {"language": taal, "word_timestamps": True, "vad_filter": True}
    data = None
    if snel_aan() if snel is None else snel:
        try:
            from faster_whisper import BatchedInferencePipeline

            print(f"Snel uitschrijven: meerdere stukken tegelijk, {threads()} rekenkernen…", flush=True)
            data = _verzamel(*BatchedInferencePipeline(model=wm).transcribe(audio, batch_size=8, beam_size=1, **opties))
        except Exception as e:  # oudere faster-whisper of te weinig geheugen: gewoon de normale manier
            print(f"Snelle modus lukte niet ({type(e).__name__}: {e}); verder op de normale manier…", flush=True)
            data = None
    if data is None:
        data = _verzamel(*wm.transcribe(audio, **opties))
    werk.schrijf_json(job_dir / "transcript.json", data)
    schrijf_leesbaar(job_dir, data)
    return job_dir / "transcript.txt"


def schrijf_leesbaar(job_dir: Path, data: dict) -> None:
    """Compacte versie voor de Hook-jager: één regel per zin met start/eind in seconden."""
    regels = [f"# taal={data['taal']} duur={data['duur']:.0f}s  (formaat: [start-eind] tekst)"]
    for s in data["segmenten"]:
        regels.append(f"[{s['start']:.1f}-{s['end']:.1f}] {s['tekst']}")
    (job_dir / "transcript.txt").write_text("\n".join(regels) + "\n", encoding="utf-8")


def woorden_in(data: dict, start: float, end: float) -> list[dict]:
    return [w for s in data["segmenten"] for w in s["woorden"] if w["end"] > start and w["start"] < end]
