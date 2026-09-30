"""Claude-taken vanuit Clip-OS starten: /video, /dagelijks en /campagne.

Draait `claude -p` op je eigen Pro-login (gratis). Er loopt één taak tegelijk,
met een leesbaar live-logboek en een stopknop. Harde kostenstop: betaalde
sleutels worden uit de omgeving van Claude gehaald, en de kostenwacht moet
groen zijn voordat een taak start.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime

from . import inbox, kostenwacht, werk

MAP = werk.DATA / "claude"
MAX_STAPPEN = "80"
_wachtrij: "queue.Queue[str]" = queue.Queue()
_huidig: dict = {"id": None, "proc": None}
_slot = threading.Lock()

NIET_VERTROUWD = (
    "Claude Code vertrouwt de Clip-OS-map nog niet, en mocht daarom niets doen. Eenmalig oplossen: "
    "open de map clip-os in Verkenner, klik met rechts op een lege plek > Openen in Terminal, typ claude, "
    "kies 'Yes, I trust this folder' en typ daarna /exit. Start de taak dan opnieuw."
)
TITELS = {"video": "Ideeën voor video", "dagelijks": "Dagelijkse run", "campagne": "Campagne toevoegen", "trends": "Marktonderzoek"}


def claude_pad() -> str | None:
    return shutil.which("claude")


def schone_omgeving() -> dict:
    """Omgeving voor Claude zonder betaalde sleutels (anders zou Claude Code per gebruik afrekenen)."""
    return {k: v for k, v in os.environ.items() if k not in kostenwacht.BETAALDE_SLEUTELS}


def _pad(tid: str):
    if not re.fullmatch(r"[0-9a-f]{12}", tid):
        raise ValueError("ongeldig taak-id")
    return MAP / f"{tid}.json"


def _schrijf(taak: dict) -> None:
    MAP.mkdir(parents=True, exist_ok=True)
    tmp = _pad(taak["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(taak, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _pad(taak["id"]))


def lees(tid: str) -> dict:
    return werk.lees_json(_pad(tid))


def zet(tid: str, **velden) -> dict:
    with _slot:
        taak = lees(tid)
        taak.update(velden)
        _schrijf(taak)
        return taak


def log_regels(tid: str, n: int = 60) -> list[str]:
    pad = MAP / f"{tid}.log"
    if not pad.exists():
        return []
    return pad.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]


def prompt_voor(soort: str, data: dict) -> str:
    if soort == "video":
        return f"/video {data['link']} {data.get('brief') or ''}".strip()
    if soort == "dagelijks":
        return "/dagelijks"
    if soort == "campagne":
        return "/campagne " + data["tekst"]
    if soort == "trends":
        return f"/trends {data['taal']} {data.get('onderwerp') or ''}".strip()
    raise ValueError("onbekende taak")


def valideer(soort: str, data: dict) -> dict:
    if soort == "video":
        link = str(data.get("link", "")).strip()
        if not re.fullmatch(r"https?://\S+", link):
            raise ValueError("Plak een volledige link (https://…)")
        brief = str(data.get("brief") or "").strip()
        if brief and not (re.fullmatch(r"[A-Za-z0-9_-]+", brief) and (werk.BRIEFS / f"{brief}.json").exists()):
            raise ValueError("Onbekende campagne")
        return {"link": link, "brief": brief}
    if soort == "campagne":
        tekst = str(data.get("tekst", "")).strip()
        if not 20 <= len(tekst) <= 20000:
            raise ValueError("Plak de campagnetekst (minimaal 20 tekens)")
        return {"tekst": tekst}
    if soort == "dagelijks":
        return {}
    if soort == "trends":
        taal = str(data.get("taal") or "beide").strip().lower()
        if taal not in ("en", "nl", "beide"):
            raise ValueError("Kies Engels, Nederlands of beide")
        onderwerp = " ".join(str(data.get("onderwerp") or "").split())
        if len(onderwerp) > 80 or not re.fullmatch(r"[\w\s,&'.€$%+\-]*", onderwerp):
            raise ValueError("Onderwerp mag maximaal 80 tekens zijn, zonder speciale tekens")
        return {"taal": taal, "onderwerp": onderwerp}
    raise ValueError("onbekende taak")


def nieuw(soort: str, data: dict) -> dict:
    data = valideer(soort, data)
    taak = {
        "id": uuid.uuid4().hex[:12], "soort": soort, "titel": TITELS[soort], "data": data,
        "status": "wacht", "gemaakt": inbox.nu(), "gestart": None, "klaar": None, "fout": None,
    }
    _schrijf(taak)
    _wachtrij.put(taak["id"])
    return taak


def alle(n: int = 15) -> list[dict]:
    if not MAP.exists():
        return []
    taken = []
    for p in MAP.glob("*.json"):
        try:
            taken.append(werk.lees_json(p))
        except (json.JSONDecodeError, OSError):
            continue
    taken.sort(key=lambda t: t.get("gemaakt", ""), reverse=True)
    uit = taken[:n]
    for t in uit:
        t["log"] = log_regels(t["id"]) if t["status"] in ("bezig", "klaar", "fout", "gestopt") else []
    return uit


def stop(tid: str) -> dict:
    taak = lees(tid)
    if taak["status"] == "wacht":
        return zet(tid, status="gestopt", klaar=inbox.nu())
    if taak["status"] == "bezig" and _huidig["id"] == tid and _huidig["proc"]:
        zet(tid, gestopt_door_jou=True)
        _huidig["proc"].terminate()
    return lees(tid)


def _kort(tekst: str, n: int = 160) -> str:
    tekst = " ".join(str(tekst).split())
    return tekst if len(tekst) <= n else tekst[: n - 1] + "…"


def _leesbaar(regel: str) -> list[str]:
    """Zet één regel stream-json van Claude om in leesbare logregels."""
    try:
        m = json.loads(regel)
    except json.JSONDecodeError:
        return [_kort(regel)] if regel.strip() else []
    inspring = "   ↳ " if m.get("parent_tool_use_id") else ""
    uit = []
    if m.get("type") == "assistant":
        for blok in (m.get("message") or {}).get("content", []):
            if blok.get("type") == "text" and blok.get("text", "").strip():
                uit.append(f"{inspring}💬 {_kort(blok['text'], 300)}")
            elif blok.get("type") == "tool_use":
                naam, inp = blok.get("name", "?"), blok.get("input") or {}
                if naam in ("Task", "Agent"):
                    uit.append(f"{inspring}🤖 Agent {inp.get('subagent_type', '')}: {_kort(inp.get('description', ''), 80)}")
                elif naam == "Bash":
                    uit.append(f"{inspring}⚙️  {_kort(inp.get('command', ''), 140)}")
                elif naam in ("Read", "Write", "Edit"):
                    uit.append(f"{inspring}📄 {naam} {_kort(inp.get('file_path', ''), 100)}")
                else:
                    uit.append(f"{inspring}🔧 {naam}")
    elif m.get("type") == "result":
        if m.get("is_error"):
            uit.append(f"❌ {_kort(m.get('result') or m.get('subtype', 'fout'), 400)}")
        else:
            uit.append(f"✅ {_kort(m.get('result', 'Klaar'), 400)}")
    return uit


def _voer_uit(tid: str) -> None:
    taak = lees(tid)
    if taak["status"] != "wacht":
        return
    pad = claude_pad()
    if not pad:
        zet(tid, status="fout", klaar=inbox.nu(),
            fout="Claude Code is niet gevonden. Installeer het en log in met je Pro-account (claude → /login).")
        return
    sleutels, code = kostenwacht.controleer_sleutels(), kostenwacht.scan_code()
    if code:
        zet(tid, status="fout", klaar=inbox.nu(), fout="⛔ KOSTENSTOP: " + "; ".join(code))
        return

    zet(tid, status="bezig", gestart=inbox.nu(), weggehaalde_sleutels=sleutels)
    cmd = [pad, "-p", prompt_voor(taak["soort"], taak["data"]), "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--max-turns", MAX_STAPPEN]
    log = MAP / f"{tid}.log"
    with log.open("w", encoding="utf-8") as f:
        f.write(f"▶ {datetime.now():%H:%M:%S} {taak['titel']} gestart (Pro-login, max {MAX_STAPPEN} stappen)\n")
        f.flush()
        proc = subprocess.Popen(cmd, cwd=werk.ROOT, env=schone_omgeving(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        _huidig.update(id=tid, proc=proc)
        niet_vertrouwd = False
        for regel in proc.stdout:
            niet_vertrouwd = niet_vertrouwd or "has not been trusted" in regel
            for leesbaar in _leesbaar(regel):
                f.write(leesbaar + "\n")
                f.flush()
        rc = proc.wait()
        _huidig.update(id=None, proc=None)
    taak = lees(tid)
    if niet_vertrouwd:
        zet(tid, status="fout", klaar=inbox.nu(), fout=NIET_VERTROUWD)
        return
    if taak.get("gestopt_door_jou"):
        zet(tid, status="gestopt", klaar=inbox.nu())
    elif rc == 0:
        zet(tid, status="klaar", klaar=inbox.nu())
    else:
        zet(tid, status="fout", klaar=inbox.nu(), fout=f"Claude stopte met code {rc}. Zie het logboek.")


def werker() -> None:
    while True:
        tid = _wachtrij.get()
        try:
            _voer_uit(tid)
        except Exception as e:  # zichtbaar maken in het OS
            try:
                zet(tid, status="fout", klaar=inbox.nu(), fout=f"{type(e).__name__}: {e}")
            except Exception:
                pass
        finally:
            _wachtrij.task_done()


def herstel() -> None:
    """Na een herstart: wachtende taken opnieuw inplannen, onderbroken taken als gestopt markeren."""
    if not MAP.exists():
        return
    for p in sorted(MAP.glob("*.json")):
        try:
            t = werk.lees_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        if t.get("status") == "wacht":
            _wachtrij.put(t["id"])
        elif t.get("status") == "bezig":
            zet(t["id"], status="gestopt", klaar=inbox.nu(), fout="Onderbroken doordat Clip-OS werd afgesloten.")
