"""Clip-OS bijwerken vanuit de webapp (hetzelfde als update.bat): git pull + onderdelen bijwerken."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from datetime import datetime

from . import werk

STAAT: dict = {"status": "rust", "log": [], "gestart": None, "klaar": None}
_slot = threading.Lock()


def _git(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=werk.ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def versie() -> dict:
    """Huidige versie, en of bijwerken via git mogelijk is (niet bij de zip-versie)."""
    if not shutil.which("git"):
        return {"kan_bijwerken": False, "reden": "Git is niet gevonden op deze computer."}
    if _git("rev-parse", "--is-inside-work-tree").returncode != 0:
        return {"kan_bijwerken": False, "reden": "Dit is de zip-versie. Stap eenmalig over (zie README: Updates)."}
    info = _git("log", "-1", "--format=%h|%cI|%s").stdout.strip().split("|", 2)
    return {"kan_bijwerken": True, "commit": info[0], "datum": info[1][:16].replace("T", " ") if len(info) > 1 else "",
            "omschrijving": info[2] if len(info) > 2 else ""}


def _log(regel: str) -> None:
    STAAT["log"].append(regel.rstrip())


def _voer_uit() -> None:
    try:
        _log(f"▶ {datetime.now():%H:%M:%S} Nieuwste versie ophalen…")
        voor = _git("rev-parse", "HEAD").stdout.strip()
        pull = _git("pull", "--ff-only", timeout=300)
        for r in (pull.stdout + pull.stderr).splitlines()[-15:]:
            _log(r)
        if pull.returncode != 0:
            raise RuntimeError("Ophalen lukte niet. Stuur een screenshot van dit logboek naar Claude.")
        na = _git("rev-parse", "HEAD").stdout.strip()
        if voor == na:
            _log("✅ Je hebt al de nieuwste versie.")
            STAAT["status"] = "actueel"
            return
        _log("▶ Onderdelen bijwerken (pip)…")
        pip = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q", "--disable-pip-version-check"],
                             cwd=werk.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        for r in (pip.stdout + pip.stderr).splitlines()[-10:]:
            _log(r)
        if pip.returncode != 0:
            raise RuntimeError("Onderdelen bijwerken lukte niet. Stuur een screenshot van dit logboek naar Claude.")
        _log("✅ Bijgewerkt! Sluit het zwarte venster van Clip-OS en open Clip-OS opnieuw.")
        STAAT["status"] = "herstarten"
    except Exception as e:
        _log(f"❌ {e}")
        STAAT["status"] = "fout"
    finally:
        STAAT["klaar"] = datetime.now().isoformat(timespec="seconds")


def start() -> dict:
    with _slot:
        if STAAT["status"] == "bezig":
            return STAAT
        if not versie().get("kan_bijwerken"):
            raise ValueError(versie().get("reden", "Bijwerken kan niet."))
        STAAT.update(status="bezig", log=[], gestart=datetime.now().isoformat(timespec="seconds"), klaar=None)
    threading.Thread(target=_voer_uit, daemon=True).start()
    return STAAT
