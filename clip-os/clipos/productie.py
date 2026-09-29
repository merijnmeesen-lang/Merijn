"""De productielijn: jobs aanmaken, ideeën registreren, video's maken en de dagelijkse scout."""

from __future__ import annotations

import traceback

from . import bron, controle, inbox, pakket, render, transcriptie, werk


def config() -> dict:
    return werk.lees_json(werk.ROOT / "config.json")


# ---------- jobs ----------

def nieuwe_job(bron_pad: str, brief: str | None = None, naam: str | None = None) -> str:
    werk.lees_brief(brief)  # meteen stoppen als de brief niet bestaat
    job = werk.nieuwe_job_id(naam or bron_pad.rstrip("/").split("/")[-1].split("=")[-1])
    job_dir = werk.JOBS / job
    job_dir.mkdir(parents=True)
    werk.schrijf_json(job_dir / "job.json", {"id": job, "bron": bron_pad, "brief": brief, "gemaakt": inbox.nu()})
    print(f"Job {job}: video binnenhalen…")
    bron.haal_binnen(bron_pad, job_dir)
    return job


def job_brief(job_dir) -> dict:
    return werk.lees_brief(werk.lees_json(job_dir / "job.json").get("brief"))


def te_doen() -> list[str]:
    """Jobs met transcript waarvoor nog geen ideeën in de inbox staan."""
    uit = []
    for job_dir in sorted(werk.JOBS.glob("*")):
        if (job_dir / "transcript.json").exists() and not (job_dir / "ideeen_geregistreerd").exists():
            uit.append(job_dir.name)
    return uit


# ---------- ideeën ----------

def valideer_clips(job_dir) -> tuple[list[dict], list[str]]:
    pad = job_dir / "clips.json"
    if not pad.exists():
        return [], [f"{pad} bestaat niet (de Hook-jager moet dit schrijven)"]
    clips = werk.lees_json(pad).get("clips", [])
    brief = job_brief(job_dir)
    duur_bron = werk.lees_json(job_dir / "transcript.json")["duur"]
    fouten, ids = [], set()
    for c in clips:
        cid = c.get("id", "?")
        for veld in ("id", "start", "end", "hook", "titel"):
            if not c.get(veld) and c.get(veld) != 0:
                fouten.append(f"{cid}: veld '{veld}' ontbreekt")
        if cid in ids:
            fouten.append(f"{cid}: dubbel id")
        ids.add(cid)
        try:
            lengte = float(c["end"]) - float(c["start"])
        except (KeyError, TypeError, ValueError):
            fouten.append(f"{cid}: start/end ongeldig")
            continue
        if float(c["start"]) < 0 or float(c["end"]) > duur_bron + 1:
            fouten.append(f"{cid}: valt buiten de video (0-{duur_bron:.0f}s)")
        if not (brief["min_seconden"] - 1 <= lengte <= brief["max_seconden"] - 1):
            fouten.append(f"{cid}: lengte {lengte:.1f}s, moet {brief['min_seconden']}-{brief['max_seconden'] - 1}s zijn")
    return clips, fouten


def registreer_ideeen(job: str) -> list[str]:
    job_dir = werk.job_map(job)
    clips, fouten = valideer_clips(job_dir)
    if fouten:
        raise SystemExit("clips.json klopt niet:\n  " + "\n  ".join(fouten))
    meta = werk.lees_json(job_dir / "job.json")
    bron_info = werk.lees_json(job_dir / "bron_info.json") if (job_dir / "bron_info.json").exists() else {}
    clips = sorted(clips, key=lambda c: -float(c.get("score", 0)))[: config()["max_ideeen_per_bron"]]
    nieuw = []
    for c in clips:
        vid = f"{job}__{c['id']}"
        if inbox.voeg_toe({
            "id": vid, "job": job, "clip_id": c["id"], "brief": meta.get("brief"),
            "start": float(c["start"]), "end": float(c["end"]),
            "duur": round(float(c["end"]) - float(c["start"]), 1),
            "hook": c["hook"], "titel": c["titel"],
            "beschrijving": c.get("beschrijving", ""), "hashtags": c.get("hashtags", []),
            "reden": c.get("reden", ""), "score": c.get("score"), "citaat": c.get("citaat", ""),
            "bron_titel": bron_info.get("titel") or meta.get("bron"), "bron_kanaal": bron_info.get("kanaal", ""),
        }):
            nieuw.append(vid)
    (job_dir / "ideeen_geregistreerd").write_text(inbox.nu(), encoding="utf-8")
    return nieuw


# ---------- video maken (na akkoord; kost geen Claude-gebruik) ----------

def maak(vid: str) -> dict:
    v = inbox.zet(vid, status="bezig", fout=None)
    try:
        job_dir = werk.job_map(v["job"])
        brief = job_brief(job_dir)
        video = render.render_clip(job_dir, {"id": v["clip_id"], "start": v["start"], "end": v["end"], "hook": v["hook"]},
                                   modus=v.get("modus", "auto"))
        uitslag = controle.controleer(video, v, brief)
        doel = pakket.maak_pakket(job_dir, v, brief, uitslag)
        return inbox.zet(
            vid, status="klaar", map=str(doel.relative_to(werk.ROOT)),
            controle=[[ok, t] for ok, t in uitslag], controle_ok=controle.geslaagd(uitslag),
        )
    except Exception as e:  # de fout moet zichtbaar worden in het dashboard
        traceback.print_exc()
        return inbox.zet(vid, status="fout", fout=f"{type(e).__name__}: {e}"[:1500])


# ---------- dagelijkse scout (gratis: alleen yt-dlp + whisper) ----------

def actieve_briefs() -> list[tuple[str, dict]]:
    uit = []
    for pad in sorted(werk.BRIEFS.glob("*.json")):
        if pad.stem == "voorbeeld":
            continue
        b = werk.lees_brief(pad.stem)
        if b.get("actief", True):
            uit.append((pad.stem, b))
    return uit


def _gezien() -> dict:
    pad = werk.DATA / "gezien.json"
    return werk.lees_json(pad) if pad.exists() else {}


def _markeer_gezien(sleutel: str) -> None:
    g = _gezien()
    g[sleutel] = inbox.nu()
    werk.DATA.mkdir(parents=True, exist_ok=True)
    werk.schrijf_json(werk.DATA / "gezien.json", g)


def nieuwe_bronnen(per_kanaal: int = 5) -> list[tuple[str, str, str]]:
    """(url, titel, briefnaam) voor video's die we nog niet verwerkt hebben, nieuwste eerst."""
    import yt_dlp

    gezien = _gezien()
    uit = []
    for naam, b in actieve_briefs():
        for url in b.get("bron_links", []):
            if url not in gezien:
                uit.append((url, url, naam))
        for kanaal in b.get("bron_kanalen", []):
            lijst_url = kanaal.rstrip("/")
            if "youtube.com/@" in lijst_url and not lijst_url.endswith(("/videos", "/streams")):
                lijst_url += "/videos"
            opties = {"extract_flat": True, "playlistend": per_kanaal, "quiet": True, "no_warnings": True}
            try:
                with yt_dlp.YoutubeDL(opties) as ydl:
                    info = ydl.extract_info(lijst_url, download=False)
            except Exception as e:
                print(f"⚠️  Kanaal {kanaal} niet te lezen: {e}")
                continue
            for item in info.get("entries") or []:
                url = item.get("url") or item.get("webpage_url")
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={item.get('id')}"
                if url and url not in gezien:
                    uit.append((url, item.get("title") or url, naam))
    return uit


def dag(max_bronnen: int | None = None) -> list[str]:
    cfg = config()
    max_bronnen = cfg["max_nieuwe_bronnen_per_dag"] if max_bronnen is None else max_bronnen
    gemaakt = []
    for url, titel, brief in nieuwe_bronnen()[:max_bronnen]:
        print(f"Nieuw: {titel} ({brief})")
        try:
            job = nieuwe_job(url, brief=brief, naam=titel)
            transcriptie.transcribeer(werk.JOBS / job, model=cfg["whisper_model"], taal=werk.lees_brief(brief).get("taal"))
            gemaakt.append(job)
        except SystemExit:
            raise
        except Exception as e:
            print(f"⚠️  Mislukt: {url}: {e}")
        _markeer_gezien(url)
    return gemaakt
