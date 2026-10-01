"""Clip-OS opdrachtregel. Gebruik: python -m clipos <commando>  (zie: python -m clipos -h)"""

from __future__ import annotations

import argparse
import json
import sys

from . import kostenwacht


def utf8_uitvoer() -> None:
    """Windows gebruikt voor doorgestuurde uitvoer cp1252; dan crasht print() op emoji zoals ✅."""
    for stroom in (sys.stdout, sys.stderr):
        try:
            stroom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    utf8_uitvoer()
    from .werk import systeemcertificaten
    systeemcertificaten()
    p = argparse.ArgumentParser(prog="python -m clipos", description="Clip-OS: lange video → kant-en-klare clips (gratis, lokaal).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("kostenwacht", help="controleer dat niets geld kan kosten")
    s = sub.add_parser("nieuw", help="nieuwe job: video binnenhalen (link of bestand)")
    s.add_argument("bron"); s.add_argument("--brief"); s.add_argument("--naam")
    s = sub.add_parser("transcribeer", help="spraak → tekst met tijd per woord (lokaal)")
    s.add_argument("job"); s.add_argument("--model"); s.add_argument("--taal")
    s = sub.add_parser("dag", help="dagelijkse scout: nieuwe video's ophalen + transcriberen (per taal)")
    s.add_argument("--max", type=int, help="maximum nieuwe video's per taal (standaard: config.json)")
    sub.add_parser("te-doen", help="jobs die nog ideeën nodig hebben")
    s = sub.add_parser("check-ideeen", help="controleer clips.json zonder te registreren")
    s.add_argument("job")
    s = sub.add_parser("voorstel", help="ideeën uit clips.json in de inbox zetten")
    s.add_argument("job")
    s = sub.add_parser("maak", help="video maken voor een voorstel (normaal via Akkoord in het dashboard)")
    s.add_argument("id")
    s = sub.add_parser("dashboard", help="Clip-OS openen in je browser (Chrome)")
    s.add_argument("--poort", type=int); s.add_argument("--geen-browser", action="store_true")
    s = sub.add_parser("melding", help="bericht in het dashboard + bureaubladmelding")
    s.add_argument("tekst")
    sub.add_parser("status", help="overzicht van de inbox")
    s = sub.add_parser("frames", help="stilstaande beelden van een klare video (voor controle)")
    s.add_argument("id")
    s = sub.add_parser("notitie", help="notitie van de controleur bij een video")
    s.add_argument("id"); s.add_argument("tekst")
    sub.add_parser("resultaten", help="geplaatste video's met views (voor de analist)")
    sub.add_parser("planning", help="zo zet je de dagelijkse run aan")
    s = sub.add_parser("trends", help="trending podcasts/interviews op YouTube zoeken (voor de trendonderzoeker)")
    s.add_argument("zoekterm", nargs="?"); s.add_argument("--kanaal"); s.add_argument("--max", type=int, default=8)
    s.add_argument("--periode", choices=["dag", "week", "maand"], default="week")
    s.add_argument("--min-minuten", type=int, default=10)
    sub.add_parser("trends-klaar", help="rapport van de trendonderzoeker controleren en melden")
    a = p.parse_args(argv)

    if a.cmd == "kostenwacht":
        return kostenwacht.rapport()
    kostenwacht.bewaak()  # harde stop vóór elk ander commando

    from . import inbox, productie, render, transcriptie, werk
    werk.standaardbestanden()

    if a.cmd == "nieuw":
        job = productie.nieuwe_job(a.bron, brief=a.brief, naam=a.naam)
        print(f"JOB: {job}")
    elif a.cmd == "transcribeer":
        cfg = productie.config()
        job_dir = werk.job_map(a.job)
        taal = a.taal or productie.job_brief(job_dir).get("taal")
        print(transcriptie.transcribeer(job_dir, model=a.model or cfg["whisper_model"], taal=taal))
    elif a.cmd == "dag":
        jobs = productie.dag(a.max)
        print(f"{len(jobs)} nieuwe bron(nen) verwerkt.")
        for job in productie.te_doen():
            print(f"TE_DOEN: {job}")
    elif a.cmd == "te-doen":
        for job in productie.te_doen():
            print(f"TE_DOEN: {job}")
    elif a.cmd == "check-ideeen":
        clips, fouten = productie.valideer_clips(werk.job_map(a.job))
        print(f"{len(clips)} ideeën; " + ("OK" if not fouten else "FOUTEN:\n  " + "\n  ".join(fouten)))
        return 1 if fouten else 0
    elif a.cmd == "voorstel":
        nieuw = productie.registreer_ideeen(a.job)
        print(f"{len(nieuw)} ideeën in de inbox gezet.")
    elif a.cmd == "maak":
        v = productie.maak(a.id)
        print(f"{v['status']}: {v.get('map') or v.get('fout')}")
        return 0 if v["status"] == "klaar" else 1
    elif a.cmd == "dashboard":
        from . import dashboard
        dashboard.start(a.poort or productie.config()["dashboard_poort"], browser=not a.geen_browser)
    elif a.cmd == "melding":
        inbox.melding(a.tekst)
        t = inbox.telling()
        inbox.systeem_melding("Clip-OS", f"{t['idee']} ideeën wachten op je akkoord · {t['klaar']} video's klaar om te plaatsen")
        print("Melding geplaatst.")
    elif a.cmd == "status":
        t = inbox.telling()
        print(" · ".join(f"{k}: {n}" for k, n in t.items()))
        alle = inbox.alle()
        for taal in sorted({v.get("taal") or "?" for v in alle}):
            van_taal = [v for v in alle if (v.get("taal") or "?") == taal]
            ideeen = sum(v.get("status") == "idee" for v in van_taal)
            klaar = sum(v.get("status") == "klaar" for v in van_taal)
            print(f"  {productie.taal_info(taal)['label']}: {ideeen} ideeën, {klaar} klaar om te plaatsen")
        for m in inbox.meldingen(1):
            print(f"Laatste melding ({m['tijd']}): {m['tekst']}")
    elif a.cmd == "frames":
        v = inbox.lees(a.id)
        if v.get("status") not in ("klaar", "geplaatst"):
            raise SystemExit(f"Voorstel heeft status '{v.get('status')}', nog geen video.")
        map_ = werk.ROOT / v["map"]
        for pad in render.frames(map_ / "video.mp4", map_):
            print(pad)
    elif a.cmd == "notitie":
        inbox.zet(a.id, notitie=a.tekst[:500])
        print("Notitie opgeslagen.")
    elif a.cmd == "resultaten":
        rijen = [v for v in inbox.alle() if v.get("status") == "geplaatst"]
        print("views\ttaal\tduur\tscore\tbrief\thook\ttitel")
        for v in sorted(rijen, key=lambda v: -(v.get("views") or 0)):
            print(f"{v.get('views', '?')}\t{v.get('taal')}\t{v.get('duur')}\t{v.get('score')}\t{v.get('brief')}\t{v.get('hook')}\t{v.get('titel')}")
        afgewezen = [v for v in inbox.alle() if v.get("status") == "afgewezen"]
        if afgewezen:
            print("\nDoor jou afgewezen ideeën (hook | reden):")
            for v in afgewezen[-20:]:
                print(f"- {v.get('hook')} | {v.get('afwijsreden') or '-'}")
    elif a.cmd == "trends":
        from . import trends
        if not (a.zoekterm or a.kanaal):
            raise SystemExit("Geef een zoekterm of --kanaal <url>.")
        import yt_dlp
        try:
            videos = trends.kanaal(a.kanaal, a.max, a.min_minuten) if a.kanaal else trends.zoek(a.zoekterm, a.periode, a.max, a.min_minuten)
        except yt_dlp.utils.DownloadError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                raise SystemExit("YouTube geweigerd door een beveiligingscertificaat (vaak antivirus zoals Norton). "
                                 "Oplossing: dubbelklik update.bat, dan gebruikt Clip-OS de certificaten van Windows.")
            raise SystemExit(f"YouTube niet bereikbaar of niets gevonden: {str(e)[:300]}")
        print(json.dumps(trends.verrijk(videos), ensure_ascii=False, indent=1))
    elif a.cmd == "trends-klaar":
        from . import trends
        r = trends.rond_af()
        print(f"Rapport OK: {len(r['videos'])} video's. Melding geplaatst.")
    elif a.cmd == "planning":
        from . import planning
        planning.uitleg()
    return 0


if __name__ == "__main__":
    sys.exit(main())
