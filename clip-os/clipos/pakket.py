"""Pakket: zet de klare video met alle teksten en een plaats-checklist in output/."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import werk


def youtube_titel(titel: str) -> str:
    return titel if "#shorts" in titel.lower() or len(titel) > 90 else f"{titel} #Shorts"


def beschrijving_met_tags(voorstel: dict) -> str:
    tags = " ".join(voorstel.get("hashtags", []))
    return (voorstel.get("beschrijving", "").strip() + ("\n\n" + tags if tags else "")).strip()


def maak_pakket(job_dir: Path, voorstel: dict, brief: dict, controle: list[tuple[bool, str]]) -> Path:
    job = job_dir.name
    doel = werk.OUTPUT / job / f"{voorstel['clip_id']}-{werk.slug(voorstel.get('titel', 'clip'))}"
    doel.mkdir(parents=True, exist_ok=True)
    shutil.copy2(job_dir / "clips" / voorstel["clip_id"] / "video.mp4", doel / "video.mp4")

    bron_info = {}
    if (job_dir / "bron_info.json").exists():
        bron_info = werk.lees_json(job_dir / "bron_info.json")
    render = werk.lees_json(job_dir / "clips" / voorstel["clip_id"] / "render.json")
    platform = brief.get("platform") or "clip-platform (bijv. ClipArmy)"

    regels = [
        f"# {voorstel.get('titel', '')}",
        "",
        "## 1. YouTube Shorts",
        "**Titel** (kopiëren):",
        "```", youtube_titel(voorstel.get("titel", "")), "```",
        "**Beschrijving** (kopiëren):",
        "```", beschrijving_met_tags(voorstel), "```",
        "Stappen:",
        "- [ ] YouTube-app of Studio → Maken → Short uploaden → kies `video.mp4`",
        "- [ ] Titel en beschrijving plakken",
        "- [ ] 'Gewijzigde of synthetische content': **Nee** (echte beelden; alleen ondertitels toegevoegd)",
        "- [ ] Publiceren en de link kopiëren",
        "",
        f"## 2. {platform}",
        f"Campagne: **{brief.get('naam')}**" + (f" · {brief['cpm']}" if brief.get("cpm") else ""),
        "- [ ] Log in, open de campagne en dien de YouTube-link in",
    ]
    if brief.get("indienen"):
        regels.append(f"- [ ] Let op: {brief['indienen']}")
    if brief.get("verplichte_hashtags"):
        regels.append("- [ ] Verplichte hashtags staan erin: " + " ".join(brief["verplichte_hashtags"]))
    regels += [
        "- [ ] In het dashboard op **Geplaatst** klikken (en later de views invullen)",
        "",
        "## Controle",
        *[("✅ " if ok else "❌ ") + t for ok, t in controle],
        "",
        "## Bron",
        f"- {bron_info.get('titel', '?')} — {bron_info.get('kanaal', '?')}",
        f"- {bron_info.get('url', '')}",
        f"- Fragment {werk.tijd(render['start'])} – {werk.tijd(render['end'])} ({render['duur']:.0f}s, modus: {render['modus']})",
    ]
    (doel / "PLAATSEN.md").write_text("\n".join(regels) + "\n", encoding="utf-8")
    return doel
