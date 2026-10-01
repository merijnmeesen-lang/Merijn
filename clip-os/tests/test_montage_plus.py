"""Tests voor stiltes eruit, zooms, split-screen en automatische views."""

import pytest

from clipos import reframe, tempo, views, werk


def w(start, woord, duur=0.3):
    return {"start": start, "end": start + duur, "woord": woord}


# ---------- 1. stiltes en stopwoorden ----------

def test_lange_pauzes_en_stopwoorden_worden_geknipt():
    woorden = [w(1.0, "Hallo"), w(1.4, "daar."), w(3.0, "uhm"), w(4.0, "Nieuwe"), w(4.4, "zin")]
    stukken = tempo.bewaar_segmenten(woorden, 0.9, 5.0, max_stilte=0.4)
    assert len(stukken) == 2                                   # pauze 1.7 -> 4.0 (met uhm erin) is weg
    assert stukken[0][0] == pytest.approx(0.9) and stukken[1][1] == pytest.approx(4.85)
    assert tempo.nieuwe_duur(stukken) < 5.0 - 0.9 - 1.5


def test_korte_pauzes_blijven_staan():
    woorden = [w(1.0, "een"), w(1.5, "twee"), w(2.0, "drie")]  # pauzes van 0.2 s
    assert len(tempo.bewaar_segmenten(woorden, 1.0, 2.5, max_stilte=0.4)) == 1


def test_tijden_omrekenen_naar_ingekorte_clip():
    stukken = [(1.0, 3.0), (5.0, 6.0)]
    assert tempo.remap(2.0, stukken) == pytest.approx(1.0)
    assert tempo.remap(5.5, stukken) == pytest.approx(2.5)
    assert tempo.remap(4.0, stukken) == pytest.approx(2.0)     # in een weggeknipt stuk -> op de knip
    nieuw = tempo.remap_woorden([w(5.2, "hoi"), w(4.0, "uhm")], stukken)
    assert [x["woord"] for x in nieuw] == ["hoi"] and nieuw[0]["start"] == pytest.approx(2.2)


def test_select_expressie_is_relatief_aan_clipstart():
    assert tempo.select_expressie([(10.0, 12.5), (13.0, 14.0)], 10.0) == "between(t\\,0.000\\,2.500)+between(t\\,3.000\\,4.000)"


# ---------- 2. zooms ----------

def test_punch_in_na_elke_tweede_knip_en_nadruk_zoom():
    stukken = [(0.0, 2.0), (3.0, 5.0), (6.0, 8.0), (9.0, 11.0)]
    punch, sterk = tempo.zoom_intervallen(stukken, [6.5], tempo.nieuwe_duur(stukken))
    assert punch == [(2.0, 4.0), (6.0, 8.0)]
    assert sterk == [(4.5, 5.9)]
    assert tempo.zoom_intervallen(stukken, [100.0], 8.0)[1] == []   # nadruk buiten de clip telt niet


# ---------- 3. split-screen ----------

def meting(t, *gezichten):
    lijst = [{"cx": cx, "cy": 0.45, "onder": 0.6, "grootte": g} for cx, g in gezichten]
    return (t, lijst[0]["cx"] if lijst else None, lijst[0]["onder"] if lijst else None, lijst)


def test_twee_sprekers_geeft_split_screen():
    posities = [meting(i * 0.5, (0.25, 0.3), (0.75, 0.28)) for i in range(10)]
    split = reframe.split_analyse(posities)
    assert split and split["links"]["cx"] == pytest.approx(0.25) and split["rechts"]["cx"] == pytest.approx(0.75)


def test_geen_split_bij_een_spreker_of_klein_gezicht_op_achtergrond():
    assert reframe.split_analyse([meting(i, (0.5, 0.3)) for i in range(10)]) is None
    assert reframe.split_analyse([meting(i, (0.3, 0.4), (0.8, 0.05)) for i in range(10)]) is None
    assert reframe.split_analyse([meting(i, (0.45, 0.3), (0.55, 0.3)) for i in range(10)]) is None


def test_split_crop_blijft_binnen_beeld_en_is_9_bij_8():
    for persoon in ({"cx": 0.02, "cy": 0.1, "grootte": 0.3}, {"cx": 0.98, "cy": 0.95, "grootte": 0.5}):
        cb, ch, x, y = reframe.split_crop(persoon, 1920, 1080)
        assert 0 <= x and x + cb <= 1920 and 0 <= y and y + ch <= 1080
        assert abs(cb / ch - 9 / 8) < 0.02 and cb % 2 == 0 and ch % 2 == 0


def test_gezichtsdetector_vindt_een_echt_gezicht():
    import numpy as np
    pytest.importorskip("skimage")
    from skimage import data
    beeld = np.ascontiguousarray(data.astronaut()[:, :, ::-1])
    gevonden = reframe._detector()(beeld)
    assert gevonden and 150 < gevonden[0][0] < 220 and 40 < gevonden[0][1] < 90


# ---------- 4. views ----------

def test_views_automatisch_ophalen(tmp_path, monkeypatch):
    from clipos import inbox
    monkeypatch.setattr(inbox, "INBOX", tmp_path)
    inbox.voeg_toe({"id": "a", "titel": "A"})
    inbox.zet("a", status="geplaatst", link="https://www.youtube.com/shorts/abcDEF12345")
    inbox.voeg_toe({"id": "b", "titel": "B"})
    inbox.zet("b", status="geplaatst", link="")                 # geen link: overslaan
    uit = views.werk_bij(extractor=lambda url: {"view_count": 1234, "like_count": 56, "comment_count": 7})
    assert uit == {"bijgewerkt": 1, "fouten": []}
    a = inbox.lees("a")
    assert a["views"] == 1234 and a["likes"] == 56 and a["views_auto"] and len(a["views_historie"]) == 1


def test_een_meting_per_dag_en_groei():
    h = views.voeg_meting_toe([], 100, "2026-10-01")
    h = views.voeg_meting_toe(h, 150, "2026-10-01")            # zelfde dag: vervangen
    h = views.voeg_meting_toe(h, 400, "2026-10-02")
    assert h == [["2026-10-01", 150], ["2026-10-02", 400]] and views.groei(h) == 250


@pytest.mark.parametrize("link,ok", [
    ("https://www.youtube.com/shorts/abcDEF12345", True),
    ("https://youtu.be/abcDEF12345", True),
    ("https://www.tiktok.com/@kanaal/video/123", True),
    ("https://evil.example/shorts/x", False),
    ("javascript:alert(1)", False),
])
def test_geldige_link(link, ok):
    assert views.geldige_link(link) is ok


# ---------- instellingen ----------

def test_montage_instellingen_worden_gevalideerd():
    from clipos import dashboard
    cfg = dashboard.valideer_config({"montage": {"stiltes_eruit": False, "max_stilte": "9", "zoom": 1}})
    assert cfg["montage"] == {"stiltes_eruit": False, "max_stilte": 1.5, "zoom": True, "split_screen": True}
    with pytest.raises(ValueError):
        dashboard.valideer_config({"montage": {"max_stilte": "veel"}})


# ---------- alles samen: een echte (korte) render ----------

def test_render_knipt_stiltes_en_houdt_beeld_en_geluid(tmp_path, monkeypatch):
    from clipos import render
    job = tmp_path / "job"
    job.mkdir()
    werk.draai([werk.ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25:duration=8",
                "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000:duration=8", "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-shortest", str(job / "bron.mp4")])
    woorden = [w(0.5, "Eerste"), w(0.9, "zin."), w(3.5, "uhm"), w(5.0, "Tweede"), w(5.4, "zin.")]
    werk.schrijf_json(job / "transcript.json", {"taal": "nl", "duur": 8.0, "segmenten": [{"start": 0.5, "end": 5.7, "tekst": "", "woorden": woorden}]})
    monkeypatch.setattr(reframe, "gezicht_posities", lambda *a, **k: [(i * 0.5, None, None, []) for i in range(14)])
    video = render.render_clip(job, {"id": "c1", "start": 0.5, "end": 5.7, "hook": "Test"},
                               montage={"stiltes_eruit": True, "max_stilte": 0.4, "zoom": True, "split_screen": True})
    r = werk.lees_json(video.parent / "render.json")
    info = werk.video_info(video)
    assert r["knippen"] == 1 and r["ingekort"] > 3.0
    assert (info["breedte"], info["hoogte"]) == (1080, 1920) and info["audio"]
    assert abs(info["duur"] - r["duur"]) < 0.3
