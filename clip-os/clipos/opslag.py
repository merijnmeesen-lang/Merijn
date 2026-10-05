"""Opslag: laten zien hoeveel ruimte Clip-OS gebruikt en oude videobestanden opruimen.

Wat weg mag (instelbaar in Instellingen → Opslag):
- geplaatste video's, `geplaatst_dagen` na het plaatsen (YouTube heeft er dan een kopie van);
- bronvideo's (de gedownloade podcasts), `bron_dagen` na het downloaden, zolang er geen video van wordt gemaakt.
  Is zo'n bronvideo later toch nodig (een idee goedkeuren of 'Opnieuw maken'), dan haalt Clip-OS hem opnieuw binnen;
- halve downloads en oude logboeken.

Wat altijd blijft: ideeën, views, trendonderzoek, lessenboek, instellingen, transcripten en video's die nog
geplaatst moeten worden. Er wordt alleen iets verwijderd binnen jobs/, output/ en data/claude/.
"""

from __future__ import annotations

import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from . import inbox, werk

IN_PRODUCTIE = ("akkoord", "bezig")
HALVE_DOWNLOAD = ("*.part", "*.ytdl", "*.temp.*", "bron.f*.*")
LOG_DAGEN = 30
LOG_MAX = 5 * 1024 * 1024
STAAT: dict = {"bezig": False, "laatst": None, "uitslag": None}
_slot = threading.Lock()


def _grootte(pad: Path) -> int:
    if pad.is_file():
        return pad.stat().st_size
    totaal = 0
    for p in pad.rglob("*") if pad.exists() else []:
        try:
            if p.is_file():
                totaal += p.stat().st_size
        except OSError:
            continue
    return totaal


def _dagen_geleden(iso: str | None, nu: datetime) -> float | None:
    try:
        return (nu - datetime.fromisoformat(str(iso))).total_seconds() / 86400
    except (TypeError, ValueError):
        return None


def _binnen(pad: Path, *mappen: Path) -> bool:
    """Veiligheidsslot: nooit iets verwijderen buiten de mappen van Clip-OS."""
    try:
        echt = pad.resolve()
    except OSError:
        return False
    for m in mappen:
        try:
            echt.relative_to(m.resolve())
            return echt != m.resolve()
        except ValueError:
            continue
    return False


def geplaatst_op(v: dict) -> str | None:
    if v.get("gepland_op"):  # ingepland: telt vanaf het moment dat hij live gaat
        return max(v["gepland_op"], v.get("geplaatst_op") or "")
    if v.get("geplaatst_op"):
        return v["geplaatst_op"]
    for tijd, status in reversed(v.get("historie") or []):
        if status == "geplaatst":
            return tijd
    return None


def job_leeftijd(job_dir: Path, nu: datetime) -> float:
    try:
        dagen = _dagen_geleden(werk.lees_json(job_dir / "job.json").get("gemaakt"), nu)
    except (OSError, ValueError):
        dagen = None
    if dagen is None:
        bron = job_dir / "bron.mp4"
        dagen = (time.time() - bron.stat().st_mtime) / 86400 if bron.exists() else 0.0
    return dagen


def opnieuw_te_halen(job_dir: Path) -> bool:
    """Kan de bronvideo later opnieuw binnengehaald worden (link, of het originele bestand bestaat nog)?"""
    try:
        bron = str(werk.lees_json(job_dir / "job.json").get("bron") or "")
    except (OSError, ValueError):
        return False
    return bron.startswith(("http://", "https://")) or (bool(bron) and Path(bron).expanduser().exists())


def plan(nu: datetime | None = None, cfg: dict | None = None) -> list[dict]:
    """Wat er weg mag, zonder iets te verwijderen: [{pad, soort, grootte, id?}]."""
    nu = nu or datetime.now()
    cfg = cfg or werk.opslag_instellingen()
    voorstellen = inbox.alle()
    uit: list[dict] = []

    def voeg_toe(pad: Path, soort: str, **extra) -> None:
        if pad.exists() and _binnen(pad, werk.JOBS, werk.OUTPUT, werk.DATA / "claude"):
            uit.append({"pad": pad, "soort": soort, "grootte": _grootte(pad), **extra})

    # 1. geplaatste video's
    for v in voorstellen:
        dagen = _dagen_geleden(geplaatst_op(v), nu)
        if v.get("status") != "geplaatst" or dagen is None or dagen < float(cfg["geplaatst_dagen"]):
            continue
        if v.get("map"):
            map_ = werk.ROOT / v["map"]
            if _binnen(map_, werk.OUTPUT) and len(map_.resolve().relative_to(werk.OUTPUT.resolve()).parts) == 3:  # output/<taal>/<job>/<clip>
                voeg_toe(map_, "geplaatst", id=v["id"])
        if v.get("job") and v.get("clip_id"):
            voeg_toe(werk.JOBS / v["job"] / "clips" / v["clip_id"] / "video.mp4", "geplaatst", id=v["id"])

    # 2. bronvideo's
    per_job: dict[str, set] = {}
    for v in voorstellen:
        per_job.setdefault(v.get("job"), set()).add(v.get("status"))
    for job_dir in sorted(werk.JOBS.glob("*")) if werk.JOBS.exists() else []:
        bron = job_dir / "bron.mp4"
        if not bron.exists() or job_leeftijd(job_dir, nu) < float(cfg["bron_dagen"]):
            continue
        statussen = per_job.get(job_dir.name, set())
        if statussen & set(IN_PRODUCTIE):
            continue  # er wordt nu een video van gemaakt
        if not opnieuw_te_halen(job_dir) and (statussen & {"idee", "klaar", "fout"} or not (job_dir / "ideeen_geregistreerd").exists()):
            continue  # eigen bestand dat niet meer bestaat: alleen weg als er niets meer mee hoeft
        voeg_toe(bron, "bron")

    # 3. halve downloads (ouder dan een dag)
    for job_dir in werk.JOBS.glob("*") if werk.JOBS.exists() else []:
        for patroon in HALVE_DOWNLOAD:
            for p in job_dir.glob(patroon):
                if p.is_file() and p.name != "bron.mp4" and time.time() - p.stat().st_mtime > 86400:
                    voeg_toe(p, "rest")

    # 4. logboeken van afgeronde Claude-taken
    for p in (werk.DATA / "claude").glob("*.json") if (werk.DATA / "claude").exists() else []:
        try:
            taak = werk.lees_json(p)
        except (OSError, ValueError):
            continue
        dagen = _dagen_geleden(taak.get("klaar") or taak.get("gemaakt"), nu)
        if taak.get("status") in ("klaar", "fout", "gestopt") and dagen is not None and dagen >= LOG_DAGEN:
            voeg_toe(p, "log")
            voeg_toe(p.with_suffix(".log"), "log")
    return uit


def _verwijder(item: dict) -> bool:
    pad = item["pad"]
    if not _binnen(pad, werk.JOBS, werk.OUTPUT, werk.DATA / "claude"):
        return False
    try:
        if pad.is_dir():
            shutil.rmtree(pad)
            ouder = pad.parent  # lege job-map in output/ ook weg
            if ouder != werk.OUTPUT and _binnen(ouder, werk.OUTPUT) and not any(ouder.iterdir()):
                ouder.rmdir()
        else:
            pad.unlink()
        return True
    except OSError:
        return False  # bijv. bestand staat nog open in een videospeler: volgende keer opnieuw


def _kort_logboek() -> int:
    """data/dagelijks.log groeit elke dag: boven 5 MB alleen de laatste 1 MB bewaren."""
    log = werk.DATA / "dagelijks.log"
    try:
        if log.exists() and log.stat().st_size > LOG_MAX:
            voor = log.stat().st_size
            with log.open("rb") as f:
                f.seek(-1024 * 1024, 2)
                staart = f.read()
            log.write_bytes(b"(ouder logboek opgeruimd)\n" + staart[staart.find(b"\n") + 1:])
            return voor - log.stat().st_size
    except OSError:
        pass
    return 0


def ruim_op(proef: bool = False, nu: datetime | None = None, cfg: dict | None = None) -> dict:
    """Ruim op volgens de instellingen. `proef=True`: alleen laten zien wat er weg zou gaan."""
    with _slot:
        items = plan(nu, cfg)
        if proef:
            return {"proef": True, "items": [{**i, "pad": str(i["pad"])} for i in items],
                    "vrij_te_maken": sum(i["grootte"] for i in items)}
        weg = [i for i in items if _verwijder(i)]
        nu_ = inbox.nu()
        for vid in {i["id"] for i in weg if i.get("id")}:
            try:
                inbox.zet(vid, video_opgeruimd=nu_)
            except (OSError, ValueError):
                pass
        uitslag = {
            "vrijgemaakt": sum(i["grootte"] for i in weg) + _kort_logboek(),
            "bronvideos": sum(1 for i in weg if i["soort"] == "bron"),
            "geplaatst": len({i["id"] for i in weg if i["soort"] == "geplaatst"}),
            "overig": sum(1 for i in weg if i["soort"] in ("rest", "log")),
        }
        STAAT.update(laatst=nu_, uitslag=uitslag)
        _bewaar_staat(uitslag)
        if uitslag["bronvideos"] or uitslag["geplaatst"]:
            wat = [f"{n} {naam}" for n, naam in ((uitslag["bronvideos"], "bronvideo('s)"), (uitslag["geplaatst"], "geplaatste video('s)")) if n]
            inbox.melding(f"🧹 Opgeruimd: {leesbaar(uitslag['vrijgemaakt'])} vrijgemaakt ({' en '.join(wat)}).", soort="opslag")
        return uitslag


def _bewaar_staat(uitslag: dict) -> None:
    pad = werk.DATA / "opslag.json"
    try:
        oud = werk.lees_json(pad) if pad.exists() else {}
    except (OSError, ValueError):
        oud = {}
    werk.DATA.mkdir(parents=True, exist_ok=True)
    werk.schrijf_json(pad, {"laatst": inbox.nu(), "uitslag": uitslag,
                            "totaal_vrijgemaakt": int(oud.get("totaal_vrijgemaakt", 0)) + uitslag["vrijgemaakt"]})


# ---------- met de hand verwijderen (knoppen in Clip-OS) ----------

KLEINE_BESTANDEN = {"job.json", "bron_info.json", "transcript.json", "transcript.txt", "clips.json", "ideeen_geregistreerd", "afgekeurd"}


def _video_van(v: dict) -> list[Path]:
    """De videobestanden van één voorstel (in output/ en jobs/), alleen binnen de Clip-OS-mappen."""
    uit = []
    if v.get("map"):
        map_ = werk.ROOT / v["map"]
        if _binnen(map_, werk.OUTPUT) and len(map_.resolve().relative_to(werk.OUTPUT.resolve()).parts) == 3:
            uit.append(map_)
    if v.get("job") and v.get("clip_id"):
        pad = werk.JOBS / v["job"] / "clips" / v["clip_id"] / "video.mp4"
        if _binnen(pad, werk.JOBS):
            uit.append(pad)
    return [p for p in uit if p.exists()]


def verwijder_video(vid: str, reden: str = "") -> dict:
    """Een gemaakte video (bij Plaatsen) weggooien. Het idee gaat naar 'afgewezen' en kan terug ('Terugzetten')."""
    v = inbox.lees(vid)
    if v.get("status") not in ("klaar", "fout"):
        raise ValueError("Alleen video's die klaar zijn (of mislukt) kun je hier verwijderen.")
    for pad in _video_van(v):
        _verwijder({"pad": pad})
    reden = " ".join(str(reden).split())[:300]
    return inbox.zet(vid, status="afgewezen", map=None, video_opgeruimd=inbox.nu(),
                     afwijsreden=f"Video verwijderd{': ' + reden if reden else ''}")


def bron_bezig(job: str) -> bool:
    """Wordt er nu iets met deze bron gedaan (video maken of een Claude-taak)?"""
    if any(v.get("job") == job and v.get("status") in IN_PRODUCTIE for v in inbox.alle()):
        return True
    for p in (werk.DATA / "claude").glob("*.json") if (werk.DATA / "claude").exists() else []:
        try:
            t = werk.lees_json(p)
        except (OSError, ValueError):
            continue
        if t.get("status") in ("wacht", "bezig") and (t.get("data") or {}).get("job") == job:
            return True
    return False


def verwijder_bron(job: str, reden: str = "") -> dict:
    """Een bronvideo afkeuren: de podcast en de clips weg, de ideeën die nog openstaan naar 'afgewezen'.

    Klaar en geplaatste video's blijven staan (met hun views). Kleine bestanden (transcript, gegevens) blijven
    bewaard, zodat 'Opnieuw maken' van een video die al klaar is nog werkt."""
    import re

    if not re.fullmatch(r"[\w.\-]{1,160}", job or ""):
        raise ValueError("Onbekende bronvideo")
    job_dir = werk.JOBS / job
    if not (job_dir.is_dir() and _binnen(job_dir, werk.JOBS)):
        raise ValueError("Onbekende bronvideo")
    if bron_bezig(job):
        raise ValueError("Clip-OS is nu met deze video bezig. Wacht tot dat klaar is en probeer het dan opnieuw.")
    reden = " ".join(str(reden).split())[:300]
    vrij = 0
    for pad in list(job_dir.iterdir()):
        if pad.name in KLEINE_BESTANDEN:
            continue
        vrij += _grootte(pad)
        _verwijder({"pad": pad})
    (job_dir / "afgekeurd").write_text(f"{inbox.nu()} {reden}".strip(), encoding="utf-8")
    ideeen = 0
    for v in inbox.alle():
        if v.get("job") == job and v.get("status") in ("idee", "fout"):
            inbox.zet(v["id"], status="afgewezen", bron_afgekeurd=True,
                      afwijsreden=f"Bron afgekeurd{': ' + reden if reden else ''}")
            ideeen += 1
    return {"vrijgemaakt": vrij, "ideeen": ideeen}


def leesbaar(n: float) -> str:
    for eenheid in ("B", "KB", "MB", "GB"):
        if n < 1024 or eenheid == "GB":
            return f"{n:.0f} {eenheid}" if eenheid in ("B", "KB") else f"{n:.1f} {eenheid}".replace(".", ",")
        n /= 1024
    return f"{n:.1f} GB"


def overzicht() -> dict:
    """Hoeveel ruimte Clip-OS gebruikt, per soort, plus de vrije ruimte op de schijf."""
    bron = clips = overig = 0
    for job_dir in werk.JOBS.glob("*") if werk.JOBS.exists() else []:
        b = _grootte(job_dir / "bron.mp4")
        c = _grootte(job_dir / "clips")
        bron += b
        clips += c
        overig += _grootte(job_dir) - b - c
    klaar = _grootte(werk.OUTPUT)
    gegevens = _grootte(werk.DATA)
    try:
        schijf = shutil.disk_usage(werk.ROOT)
        vrij, totaal = schijf.free, schijf.total
    except OSError:
        vrij = totaal = None
    pad = werk.DATA / "opslag.json"
    try:
        laatst = werk.lees_json(pad) if pad.exists() else {}
    except (OSError, ValueError):
        laatst = {}
    return {
        "bronvideos": bron, "clips": clips, "klaar": klaar, "overig": overig + gegevens,
        "totaal": bron + clips + klaar + overig + gegevens, "schijf_vrij": vrij, "schijf_totaal": totaal,
        "laatst": laatst.get("laatst"), "uitslag": laatst.get("uitslag"), "totaal_vrijgemaakt": laatst.get("totaal_vrijgemaakt", 0),
        "bezig": STAAT["bezig"],
    }


def automatisch() -> dict | None:
    """Opruimen als dat aan staat (bij het starten van Clip-OS, elke paar uur, en in de dagelijkse run)."""
    if not werk.opslag_instellingen().get("automatisch", True):
        return None
    return ruim_op()


def start_achtergrond(elke_uren: float = 6) -> None:
    def lus() -> None:
        while True:
            STAAT["bezig"] = True
            try:
                automatisch()
            except Exception as e:  # opruimen mag Clip-OS nooit laten crashen
                print(f"⚠️  Opruimen mislukt: {e}")
            finally:
                STAAT["bezig"] = False
            time.sleep(elke_uren * 3600)
    threading.Thread(target=lus, daemon=True).start()
