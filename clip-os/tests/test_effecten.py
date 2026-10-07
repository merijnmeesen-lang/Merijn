"""Tests voor split-screen per shot, knip-detectie, pop-up tekst, geluidseffecten, snel uitschrijven en snel marktonderzoek."""

import sys
import time
import types

import numpy as np
import pytest

from clipos import effecten, productie, reframe, trends, werk
from clipos.ondertitels import maak_ass


def w(start, woord, duur=0.3):
    return {"start": start, "end": start + duur, "woord": woord}


# ---------- camerawissels ----------

def test_knip_tussen_twee_hoeken_die_op_elkaar_lijken():
    rng = np.random.default_rng(1)
    a = np.full((36, 64, 3), 30, np.uint8)
    b = a.copy()
    b[5:30, 10:30] = 70                                      # andere hoek in dezelfde donkere studio
    beelden = [np.clip(x.astype(int) + rng.integers(-2, 3, x.shape), 0, 255).astype(np.uint8)
               for x in [a] * 60 + [b] * 60]                  # 2 s + 2 s bij 30 fps, met wat ruis
    assert reframe.knippen_uit_beelden(np.stack(beelden), 30.0, 4.0) == [2.0]


def test_geen_knip_bij_beweging_of_ruis():
    rng = np.random.default_rng(2)
    beelden = np.stack([np.clip(80 + i // 3 + rng.integers(-6, 7, (36, 64, 3)), 0, 255).astype(np.uint8) for i in range(120)])
    assert reframe.knippen_uit_beelden(beelden, 30.0, 4.0) == []


# ---------- indeling per shot ----------

def meting(t, *gezichten):
    lijst = [{"cx": cx, "cy": 0.45, "onder": 0.6, "grootte": g} for cx, g in gezichten]
    return (t, lijst[0]["cx"] if lijst else None, lijst[0]["onder"] if lijst else None, lijst)


def test_split_alleen_in_het_brede_shot():
    posities = ([meting(i * 0.25, (0.4, 0.5)) for i in range(16)]                       # 0-4 s: close-up
                + [meting(4 + i * 0.25, (0.25, 0.15), (0.75, 0.15)) for i in range(16)]  # 4-8 s: breed shot, 2 mensen
                + [meting(8 + i * 0.25) for i in range(16)])                            # 8-12 s: achterhoofd
    lagen = reframe.indeling(posities, 12.0, knippen=[4.0, 8.0])
    assert [seg["soort"] for seg in lagen] == ["volg", "split", "vol"]
    assert lagen[1]["t"] == 4.0 and lagen[1]["links"]["cx"] == pytest.approx(0.25)
    assert reframe.intervallen(lagen, "split", 12.0) == [(4.0, 8.0)]
    assert [seg["soort"] for seg in reframe.indeling(posities, 12.0, knippen=[4.0, 8.0], split=False)] == ["volg", "volg", "vol"]


def test_stap_expressie():
    assert reframe.stap_expressie([(0.0, 10), (2.5, 20), (4.0, 30)]) == "if(lt(t\\,2.500)\\,10\\,if(lt(t\\,4.000)\\,20\\,30))"


# ---------- pop-up tekst ----------

def test_automatische_popups_pakken_bedragen_en_percentages():
    woorden = [w(1, "In"), w(2, "2020"), w(3, "he"), w(4, "lost"), w(5, "$3"), w(5.3, "billion."), w(9, "About"),
               w(10, "90%"), w(11, "of"), w(12, "people"), w(16, "had"), w(17, "2"), w(18, "kids")]
    assert effecten.automatische_popups(woorden) == [{"t": 5, "tekst": "$3 BILLION"}, {"t": 10, "tekst": "90%"}]


def test_kernwoorden_van_claude_gaan_voor():
    eigen = [{"t": 12.0, "tekst": "BANKRUPT"}, {"t": 99.0, "tekst": "buiten de clip"}]
    assert effecten.popup_lijst(eigen, [w(5, "$3"), w(5.3, "billion")], 0, 20) == [{"t": 12.0, "tekst": "BANKRUPT"}]


def test_kernwoorden_worden_gecontroleerd(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    werk.schrijf_json(job / "transcript.json", {"duur": 100})
    werk.schrijf_json(job / "job.json", {"brief": None})
    clip = {"id": "c1", "start": 10, "end": 40, "hook": "h", "titel": "t"}
    werk.schrijf_json(job / "clips.json", {"clips": [{**clip, "kernwoorden": [{"t": 20, "tekst": "$3 BILLION"}]}]})
    assert productie.valideer_clips(job)[1] == []
    werk.schrijf_json(job / "clips.json", {"clips": [{**clip, "kernwoorden": [{"t": 80, "tekst": "x"}]}]})
    assert any("kernwoorden" in f for f in productie.valideer_clips(job)[1])


def test_ass_met_popup_en_ondertitels_op_de_naad_tijdens_split():
    ass = maak_ass([w(1, "eerste"), w(5, "tweede")], 0, 8, popups=[(4.0, "$3 billion", 150)], split_intervallen=[(4.5, 8.0)])
    assert "Pop,,0,0,0,,{\\an5\\pos(540,150)" in ass and "$3 BILLION" in ass
    regels = [r for r in ass.splitlines() if ",Onder," in r]
    assert "\\pos(540,1035)" not in regels[0] and "\\pos(540,1035)" in regels[-1]


# ---------- geluidseffecten ----------

def test_geluidseffecten_niet_te_dicht_op_elkaar():
    assert effecten.momenten([5.0, 1.0, 1.5, 0.1, 9.9, 3.2, 7.0], 10.0, 2.0) == [1.0, 3.2, 7.0]


def test_audio_graaf_mengt_onder_de_spraak(tmp_path, monkeypatch):
    monkeypatch.setattr(werk, "DATA", tmp_path)
    filters, inputs, uit = effecten.audio_graaf("[ak]", {"whoosh": [1.0, 4.0], "boem": [6.0]}, eerste_input=1)
    assert uit == "[amix]" and len(inputs) == 2 and all(p.exists() for p in inputs)
    assert "amix=inputs=4" in filters[-1] and any("adelay=6000|6000" in f for f in filters)
    assert effecten.audio_graaf("[ak]", {"whoosh": []}, 1) == ([], [], "[ak]")


# ---------- alles samen: echte render met camerawissels ----------

def test_render_met_volgen_split_en_wazig_beeld(tmp_path):
    skimage = pytest.importorskip("skimage")
    import cv2
    from skimage import data

    from clipos import render
    g = np.ascontiguousarray(data.astronaut()[:, :, ::-1])[0:300, 100:330]
    groot, klein = cv2.resize(g, (230, 300)), cv2.resize(g, (110, 145))
    job = tmp_path / "job"
    job.mkdir()
    vw = cv2.VideoWriter(str(tmp_path / "s.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 25, (1280, 720))
    for kleur, maak in (((90, 120, 150), lambda b: b.__setitem__((slice(150, 450), slice(400, 630)), groot)),
                        ((150, 110, 70), lambda b: (b.__setitem__((slice(250, 395), slice(250, 360)), klein),
                                                    b.__setitem__((slice(250, 395), slice(900, 1010)), klein))),
                        ((40, 40, 40), lambda b: cv2.circle(b, (400, 600), 300, (15, 15, 15), -1))):
        beeld = np.full((720, 1280, 3), kleur, np.uint8)
        maak(beeld)
        for _ in range(100):
            vw.write(beeld)
    vw.release()
    werk.draai([werk.ffmpeg(), "-y", "-loglevel", "error", "-i", str(tmp_path / "s.mp4"), "-f", "lavfi", "-i", "sine=f=200:d=12",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(job / "bron.mp4")])
    woorden = [w(0.2 + i * 0.4, "word") for i in range(28)]
    werk.schrijf_json(job / "transcript.json", {"taal": "en", "duur": 12, "segmenten": [{"start": 0.2, "end": 11.5, "tekst": "", "woorden": woorden}]})
    video = render.render_clip(job, {"id": "c1", "start": 0.2, "end": 11.5, "hook": "Test", "kernwoorden": [{"t": 5.0, "tekst": "$3 BILLION"}]},
                               montage={"stiltes_eruit": False, "zoom": True, "split_screen": True, "geluidseffecten": True, "popup_tekst": True})
    r = werk.lees_json(video.parent / "render.json")
    assert r["modus"] == "mix" and r["camerawissels"] == 2
    assert [s["soort"] for s in r["indeling"]] == ["volg", "split", "vol"]
    assert r["popups"] and r["geluidseffecten"] >= 2
    info = werk.video_info(video)
    assert (info["breedte"], info["hoogte"]) == (1080, 1920) and info["audio"]


# ---------- snel uitschrijven ----------

def test_snel_uitschrijven_valt_terug_bij_een_fout(tmp_path, monkeypatch):
    from clipos import transcriptie

    class Seg:
        def __init__(self, a, b):
            self.start, self.end, self.text = a, b, " hoi"
            self.words = [types.SimpleNamespace(start=a, end=b, word=" hoi")]

    info = types.SimpleNamespace(language="nl", duration=2.0)
    gebruikt = []

    class Model:
        def __init__(self, *a, **k):
            gebruikt.append(("model", k.get("cpu_threads")))

        def transcribe(self, audio, **k):
            gebruikt.append("normaal")
            return iter([Seg(0, 1), Seg(1, 2)]), info

    class Batched:
        def __init__(self, model):
            pass

        def transcribe(self, audio, **k):
            assert k["batch_size"] == 8 and k["beam_size"] == 1 and k["word_timestamps"]

            def gen():
                yield Seg(0, 1)
                raise MemoryError("te weinig geheugen")
            return gen(), info

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model, BatchedInferencePipeline=Batched))
    monkeypatch.setattr(transcriptie, "laad_audio", lambda b: np.zeros(10, np.float32))
    transcriptie.transcribeer(tmp_path, snel=True)
    assert "normaal" in gebruikt and len(werk.lees_json(tmp_path / "transcript.json")["segmenten"]) == 2
    assert gebruikt[0][1] >= 2


# ---------- snel marktonderzoek ----------

def test_marktonderzoek_zoekt_alles_tegelijk(monkeypatch):
    monkeypatch.setattr(trends, "_plat", lambda url, n: (time.sleep(0.4), [{"id": f"{abs(hash(url)) % 997}-{i}", "duration": 3600,
                                                                             "view_count": i} for i in range(4)])[1])
    monkeypatch.setattr(trends, "_detail", lambda url: (time.sleep(0.4), {"url": url})[1])
    t = time.time()
    uit = trends.zoek_meerdere(["geld", "ai", "beleggen"], maximum=3, kanalen=["https://www.youtube.com/@x"])
    assert len(uit) == 12 and time.time() - t < 2.5            # één voor één zou ±6,4 s duren


def test_tekst_blijft_uit_de_knoppen_van_youtube():
    """Bovenin (statusbalk, 'Shorts', Live/Lens) en onderin (kanaalnaam, titel) legt YouTube knoppen over de video."""
    from clipos import ondertitels as o
    assert reframe.hook_y([(0.0, None, None)]) >= o.VEILIG_BOVEN
    assert reframe.hook_y([(0.0, 0.5, 0.05)]) >= o.VEILIG_BOVEN          # gezicht heel hoog in beeld
    onder_marge = int(o.KOP.split("Style: Onder,")[1].split("\n")[0].split(",")[-2])
    assert 1920 - onder_marge <= o.VEILIG_ONDER                          # onderkant van de ondertitels
    assert o.NAAD_HOOK_Y > o.VEILIG_BOVEN and o.NAAD_ONDERTITEL[1] < o.VEILIG_ONDER
    ass = maak_ass([w(1, "hoi")], 0, 5, hook="Hook", hook_y=o.NAAD_HOOK_Y, hook_onderkant=True)
    assert "{\\an2\\pos(540,935)}Hook" in ass


# ---------- scherpte ----------

def test_zoom_snijdt_uit_het_origineel_binnen_beeld():
    from clipos import render
    for x in (0, 657, 1314):                                   # links, midden, rechts in een 1920x1080-bron
        zb, zh, zx, zy = render.zoom_uitsnede(606, 1080, x, 0, 1.10, 1920, 1080)
        assert (zb, zh) == (550, 982) and 0 <= zx and zx + zb <= 1920 and 0 <= zy and zy + zh <= 1080
    assert render.zoom_uitsnede(606, 1080, 657, 0, 1.0, 1920, 1080) == (606, 1080, 657, 0)


def test_download_kiest_1440p_maar_geen_av1():
    import yt_dlp

    from clipos import bron

    def fmt(i, ext, v, a, h=None, tbr=1):
        d = {"format_id": i, "ext": ext, "vcodec": v, "acodec": a, "tbr": tbr, "url": "https://x/" + i, "protocol": "https"}
        return {**d, "height": h, "width": h * 16 // 9} if h else d
    ydl = yt_dlp.YoutubeDL({"quiet": True})
    for formats, verwacht in (
        ([fmt("137", "mp4", "avc1.640028", "none", 1080, 4000), fmt("271", "webm", "vp9", "none", 1440, 9000),
          fmt("400", "mp4", "av01.0.12M.08", "none", 1440, 7000), fmt("401", "mp4", "av01.0.13M.08", "none", 2160, 15000),
          fmt("140", "m4a", "none", "mp4a.40.2", None, 128)], "271+140"),
        ([fmt("137", "mp4", "avc1.640028", "none", 1080, 4000), fmt("248", "webm", "vp9", "none", 1080, 3000),
          fmt("140", "m4a", "none", "mp4a.40.2", None, 128)], "248+140"),
    ):
        info = {"formats": formats}
        ydl.sort_formats(info)
        gekozen = list(ydl.build_format_selector(bron.FORMAAT)({"formats": info["formats"], "has_merged_format": True}))
        assert gekozen[0]["format_id"] == verwacht


# ---------- hook verhuist mee, en nooit over het gezicht ----------

def meting_h(t, cx, cy, grootte):
    g = {"cx": cx, "cy": cy, "onder": min(1.0, cy + 0.56 * grootte), "grootte": grootte}
    return (t, cx, g["onder"], [g])


def test_hook_onder_de_kin_of_boven_het_hoofd():
    hoog = [meting_h(i * 0.25, 0.5, 0.30, 0.25) for i in range(8)]      # gezicht hoog in beeld: onder de kin
    y, boven = reframe.hook_plek(hoog)
    assert not boven and 340 <= y <= reframe.HOOK_MAX_Y
    laag = [meting_h(i * 0.25, 0.5, 0.62, 0.35) for i in range(8)]      # groot en laag: boven het hoofd
    y, boven = reframe.hook_plek(laag)
    assert boven and y - reframe.HOOK_HOOGTE >= 340 and y < 0.62 * 1920 - 0.5 * 0.35 * 1920


def test_hook_verhuist_mee_bij_camerawissel():
    from clipos import render
    lagen = [{"t": 0.0, "t_bron": 0.0, "soort": "volg", "x": 0.5},
             {"t": 1.5, "t_bron": 1.5, "soort": "split", "links": {}, "rechts": {}},
             {"t": 5.0, "t_bron": 5.0, "soort": "volg", "x": 0.5}]
    posities = [meting_h(i * 0.25, 0.5, 0.30, 0.25) for i in range(6)]
    stukken = render.hook_stukken(lagen, posities, 10.0)
    assert stukken[0][:2] == (0.0, 1.5) and not stukken[0][3]
    assert stukken[1] == (1.5, 3.0, 935, True)                          # op de naad tussen de twee sprekers


def test_valse_gezichten_in_de_achtergrond_geven_het_hele_beeld():
    rommel = [(i * 0.25, x, 0.5, [{"cx": x, "cy": 0.4, "onder": 0.5, "grootte": 0.08}]) if x is not None else (i * 0.25, None, None, [])
              for i, x in enumerate([0.1, None, 0.6, None, 0.35, None, 0.85, None, 0.2, None])]
    assert reframe.crop_segmenten(rommel, 3.0) == [(0.0, None)]
    echt = [(i * 0.25, 0.4 + (0.01 if i % 2 else 0), 0.5, []) for i in range(10)]
    assert reframe.crop_segmenten(echt, 3.0)[0][1] == pytest.approx(0.4, abs=0.02)
