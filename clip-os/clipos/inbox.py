"""Inbox: ideeën, video's en meldingen. Elk voorstel is één JSON-bestand (veilig bij gelijktijdig schrijven)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import werk

INBOX = werk.DATA / "inbox"
MELDINGEN = werk.DATA / "meldingen.jsonl"

STATUSSEN = ["idee", "akkoord", "bezig", "klaar", "geplaatst", "afgewezen", "fout"]


def nu() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _pad(vid: str) -> Path:
    if "/" in vid or "\\" in vid or ".." in vid:
        raise ValueError("ongeldig voorstel-id")
    return INBOX / f"{vid}.json"


def _schrijf(pad: Path, data: dict) -> None:
    pad.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=pad.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, pad)


def voeg_toe(voorstel: dict) -> bool:
    """Nieuw idee toevoegen. Bestaat het al, dan wordt het niet overschreven."""
    pad = _pad(voorstel["id"])
    if pad.exists():
        return False
    _schrijf(pad, {**voorstel, "status": "idee", "gemaakt": nu(), "historie": [[nu(), "idee"]]})
    return True


def lees(vid: str) -> dict:
    return werk.lees_json(_pad(vid))


def zet(vid: str, **velden) -> dict:
    data = lees(vid)
    if "status" in velden and velden["status"] != data.get("status"):
        data.setdefault("historie", []).append([nu(), velden["status"]])
    data.update(velden)
    _schrijf(_pad(vid), data)
    return data


def alle() -> list[dict]:
    if not INBOX.exists():
        return []
    uit = []
    for p in sorted(INBOX.glob("*.json")):
        try:
            uit.append(werk.lees_json(p))
        except (json.JSONDecodeError, OSError):
            continue
    return uit


def telling() -> dict:
    t = {s: 0 for s in STATUSSEN}
    for v in alle():
        t[v.get("status", "idee")] = t.get(v.get("status", "idee"), 0) + 1
    return t


def melding(tekst: str, soort: str = "dagrapport") -> None:
    MELDINGEN.parent.mkdir(parents=True, exist_ok=True)
    with MELDINGEN.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"tijd": nu(), "soort": soort, "tekst": tekst}, ensure_ascii=False) + "\n")


def meldingen(n: int = 10) -> list[dict]:
    if not MELDINGEN.exists():
        return []
    regels = MELDINGEN.read_text(encoding="utf-8").splitlines()
    return [json.loads(r) for r in regels[-n:] if r.strip()][::-1]


def systeem_melding(titel: str, tekst: str) -> None:
    """Gratis bureaublad-melding (best effort; mislukt stil als het OS het niet ondersteunt)."""
    try:
        if sys.platform == "darwin":
            script = f'display notification {json.dumps(tekst)} with title {json.dumps(titel)}'
            subprocess.run(["osascript", "-e", script], timeout=10, capture_output=True)
        elif sys.platform.startswith("win"):
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$t.GetElementsByTagName('text')[0].AppendChild($t.CreateTextNode({json.dumps(titel)})) > $null;"
                f"$t.GetElementsByTagName('text')[1].AppendChild($t.CreateTextNode({json.dumps(tekst)})) > $null;"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Clip-OS').Show([Windows.UI.Notifications.ToastNotification]::new($t))"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15, capture_output=True)
        else:
            subprocess.run(["notify-send", titel, tekst], timeout=10, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        pass
