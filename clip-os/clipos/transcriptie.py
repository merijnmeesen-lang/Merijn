"""Transcriptie met faster-whisper: lokaal, gratis, met tijd per woord."""

from __future__ import annotations

from pathlib import Path

from . import werk


def transcribeer(job_dir: Path, model: str = "small", taal: str | None = None) -> Path:
    from faster_whisper import WhisperModel

    bron = job_dir / "bron.mp4"
    print(f"Spraakmodel '{model}' laden (eerste keer: eenmalige gratis download)…")
    wm = WhisperModel(model, device="cpu", compute_type="int8")
    segmenten, info = wm.transcribe(str(bron), language=taal, word_timestamps=True, vad_filter=True)

    data = {"taal": info.language, "duur": info.duration, "segmenten": []}
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
        print(f"  {werk.tijd(seg.end)} / {werk.tijd(info.duration)}", end="\r")
    print()
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
