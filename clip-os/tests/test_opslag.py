"""Tests voor het opruimen van oude videobestanden (Instellingen → Opslag)."""

from datetime import datetime, timedelta

import pytest

from clipos import inbox, opslag, productie, werk

NU = datetime(2026, 10, 10, 12, 0, 0)
CFG = {"automatisch": True, "geplaatst_dagen": 2, "bron_dagen": 7}


def dagen_terug(n: float) -> str:
    return (NU - timedelta(days=n)).isoformat(timespec="seconds")


@pytest.fixture
def omgeving(tmp_path, monkeypatch):
    for naam in ("JOBS", "OUTPUT", "DATA"):
        monkeypatch.setattr(werk, naam, tmp_path / naam.lower())
    monkeypatch.setattr(werk, "ROOT", tmp_path)
    monkeypatch.setattr(inbox, "INBOX", tmp_path / "data" / "inbox")
    monkeypatch.setattr(inbox, "MELDINGEN", tmp_path / "data" / "meldingen.jsonl")
    return tmp_path


def maak_job(root, job, dagen_oud, bron="https://www.youtube.com/watch?v=abc", ideeen=True):
    d = root / "jobs" / job
    (d / "clips" / "c1").mkdir(parents=True)
    (d / "bron.mp4").write_bytes(b"x" * 1000)
    (d / "transcript.json").write_text("{}")
    (d / "clips" / "c1" / "video.mp4").write_bytes(b"v" * 100)
    werk.schrijf_json(d / "job.json", {"id": job, "bron": bron, "gemaakt": dagen_terug(dagen_oud)})
    if ideeen:
        (d / "ideeen_geregistreerd").write_text("ja")
    return d


def maak_voorstel(root, job, status, geplaatst_dagen=None):
    vid = f"{job}__c1"
    map_ = root / "output" / "en" / job / "c1-titel"
    map_.mkdir(parents=True, exist_ok=True)
    (map_ / "video.mp4").write_bytes(b"v" * 100)
    (map_ / "plaatsen.md").write_text("# titel")
    inbox.voeg_toe({"id": vid, "job": job, "clip_id": "c1", "titel": "T"})
    extra = {"geplaatst_op": dagen_terug(geplaatst_dagen)} if geplaatst_dagen is not None else {}
    inbox.zet(vid, status=status, map=str(map_.relative_to(root)), **extra)
    return vid, map_


def test_geplaatste_video_na_2_dagen_weg_maar_gegevens_blijven(omgeving):
    d = maak_job(omgeving, "oud", 1)
    vid, map_ = maak_voorstel(omgeving, "oud", "geplaatst", geplaatst_dagen=3)
    inbox.zet(vid, views=1234, link="https://youtube.com/shorts/abc")
    uit = opslag.ruim_op(nu=NU, cfg=CFG)
    assert uit["geplaatst"] == 1
    assert not map_.exists() and not (d / "clips" / "c1" / "video.mp4").exists()
    assert (d / "bron.mp4").exists()                          # bron is pas 1 dag oud
    v = inbox.lees(vid)
    assert v["views"] == 1234 and v["status"] == "geplaatst" and v["video_opgeruimd"]


def test_pas_geplaatst_en_nog_te_plaatsen_blijven_staan(omgeving):
    maak_job(omgeving, "a", 1)
    _, map_a = maak_voorstel(omgeving, "a", "geplaatst", geplaatst_dagen=1)
    maak_job(omgeving, "b", 1)
    _, map_b = maak_voorstel(omgeving, "b", "klaar")
    opslag.ruim_op(nu=NU, cfg=CFG)
    assert (map_a / "video.mp4").exists() and (map_b / "video.mp4").exists()


def test_oude_bronvideo_weg_behalve_als_er_een_video_van_gemaakt_wordt(omgeving):
    oud = maak_job(omgeving, "oud", 8)
    bezig = maak_job(omgeving, "bezig", 8)
    maak_voorstel(omgeving, "bezig", "akkoord")
    nieuw = maak_job(omgeving, "nieuw", 3)
    uit = opslag.ruim_op(nu=NU, cfg=CFG)
    assert uit["bronvideos"] == 1
    assert not (oud / "bron.mp4").exists() and (oud / "transcript.json").exists()
    assert (bezig / "bron.mp4").exists() and (nieuw / "bron.mp4").exists()


def test_eigen_bestand_dat_niet_meer_bestaat_blijft_zolang_er_ideeen_open_staan(omgeving, tmp_path):
    d = maak_job(omgeving, "eigen", 10, bron=str(tmp_path / "bestaat-niet.mp4"))
    maak_voorstel(omgeving, "eigen", "idee")
    opslag.ruim_op(nu=NU, cfg=CFG)
    assert (d / "bron.mp4").exists()


def test_proef_verwijdert_niets(omgeving):
    d = maak_job(omgeving, "oud", 8)
    r = opslag.ruim_op(proef=True, nu=NU, cfg=CFG)
    assert r["vrij_te_maken"] >= 1000 and (d / "bron.mp4").exists()


def test_nooit_iets_buiten_de_clipos_mappen(omgeving):
    geheim = omgeving / "lessenboek.md"
    geheim.write_text("belangrijk")
    maak_job(omgeving, "x", 1)
    vid, _ = maak_voorstel(omgeving, "x", "geplaatst", geplaatst_dagen=5)
    inbox.zet(vid, map="output/../lessenboek.md")             # gemanipuleerd pad
    inbox.zet(vid, map="output/en")                           # hele taalmap: ook niet
    opslag.ruim_op(nu=NU, cfg=CFG)
    assert geheim.read_text() == "belangrijk" and (omgeving / "output" / "en").exists()


def test_opgeruimde_bron_wordt_opnieuw_binnengehaald(omgeving, monkeypatch):
    d = maak_job(omgeving, "oud", 8)
    (d / "bron.mp4").unlink()
    gehaald = []
    monkeypatch.setattr(productie.bron, "haal_binnen", lambda b, j: gehaald.append(b) or (j / "bron.mp4"))
    productie.zorg_voor_bron(d)
    assert gehaald == ["https://www.youtube.com/watch?v=abc"]


def test_opslag_instellingen_worden_gevalideerd():
    from clipos import dashboard
    cfg = dashboard.valideer_config({"opslag": {"automatisch": False, "geplaatst_dagen": "2", "bron_dagen": 500}})
    assert cfg["opslag"] == {"automatisch": False, "geplaatst_dagen": 2, "bron_dagen": 90}
    with pytest.raises(ValueError):
        dashboard.valideer_config({"opslag": {"bron_dagen": "veel"}})


def test_leesbaar():
    assert opslag.leesbaar(3 * 1024 ** 3) == "3,0 GB" and opslag.leesbaar(512) == "512 B"


# ---------- knoppen bij Plaatsen en Resultaten ----------

class _NepHandler:
    """Roept de echte dashboard-logica aan zonder webserver."""
    def __init__(self):
        from clipos import dashboard
        self.h = dashboard.Handler.__new__(dashboard.Handler)
        self.h._json = lambda d, code=200: (code, d)

    def __call__(self, actie, vid, body):
        return self.h._voorstel(actie, vid, body)


@pytest.mark.parametrize("link", ["", "https://youtube.com/shorts/abcDEF12345"])
def test_geplaatst_met_en_zonder_link(omgeving, link):
    inbox.voeg_toe({"id": "t1", "titel": "T"})
    inbox.zet("t1", status="klaar")
    code, _ = _NepHandler()("geplaatst", "t1", {"link": link})
    assert code == 200 and inbox.lees("t1")["status"] == "geplaatst" and inbox.lees("t1")["link"] == link


def test_link_en_views_achteraf(omgeving):
    inbox.voeg_toe({"id": "t1", "titel": "T"})
    inbox.zet("t1", status="geplaatst")
    h = _NepHandler()
    assert h("link", "t1", {"link": "https://youtu.be/abcDEF12345"})[0] == 200
    assert h("views", "t1", {"views": "1.234"})[0] == 200
    assert inbox.lees("t1")["views"] == 1234
