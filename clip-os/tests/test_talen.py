from clipos import pakket, productie, werk


def test_verdeel_per_taal_geeft_elke_taal_een_beurt():
    bronnen = [
        ("en1", "t", "podcast-en", "en"),
        ("en2", "t", "podcast-en", "en"),
        ("en3", "t", "podcast-en", "en"),
        ("nl1", "t", "cliparmy", "nl"),
        ("nl2", "t", "cliparmy", "nl"),
    ]
    gekozen = productie.verdeel_per_taal(bronnen, {"en": 1, "nl": 1})
    assert [b[0] for b in gekozen] == ["en1", "nl1"]


def test_verdeel_per_taal_eigen_limiet_en_onbekende_taal():
    bronnen = [("a", "t", "x", "en"), ("b", "t", "x", "en"), ("c", "t", "y", None), ("d", "t", "y", None)]
    gekozen = productie.verdeel_per_taal(bronnen, {"en": 2}, standaard=1)
    assert [b[0] for b in gekozen] == ["a", "b", "c"]


def test_taal_info_uit_config():
    assert "Engels" in productie.taal_info("en")["label"]
    assert "Nederlands" in productie.taal_info("nl")["label"]
    assert productie.taal_info("de")["label"] == "de"


def _maak_job(tmp_path, monkeypatch):
    monkeypatch.setattr(werk, "OUTPUT", tmp_path / "output")
    job_dir = tmp_path / "jobs" / "job1"
    (job_dir / "clips" / "c01").mkdir(parents=True)
    (job_dir / "clips" / "c01" / "video.mp4").write_bytes(b"x")
    werk.schrijf_json(job_dir / "clips" / "c01" / "render.json", {"start": 1.0, "end": 31.0, "duur": 30.0, "modus": "volg"})
    return job_dir


def test_pakket_per_taal_met_account_en_zonder_platform(tmp_path, monkeypatch):
    job_dir = _maak_job(tmp_path, monkeypatch)
    v = {"clip_id": "c01", "titel": "He lost everything", "taal": "en", "beschrijving": "Wow.", "hashtags": ["#money"]}
    brief = werk.lees_brief(None)  # geen campagne → geen platform-stap
    doel = pakket.maak_pakket(job_dir, v, brief, [(True, "ok")], productie.taal_info("en"))
    assert doel.parent.parent.name == "en"
    tekst = (doel / "PLAATSEN.md").read_text(encoding="utf-8")
    assert "Plaats op:** je Engelse YouTube-kanaal" in tekst
    assert "He lost everything #Shorts" in tekst
    assert "## 2." not in tekst


def test_pakket_met_campagne_toont_indienstap(tmp_path, monkeypatch):
    job_dir = _maak_job(tmp_path, monkeypatch)
    v = {"clip_id": "c01", "titel": "Grootste fout", "taal": "nl", "beschrijving": "", "hashtags": ["#ad"]}
    brief = {**werk.lees_brief(None), "naam": "Test", "platform": "ClipArmy", "verplichte_hashtags": ["#ad"]}
    doel = pakket.maak_pakket(job_dir, v, brief, [(True, "ok")], productie.taal_info("nl"))
    tekst = (doel / "PLAATSEN.md").read_text(encoding="utf-8")
    assert doel.parent.parent.name == "nl"
    assert "## 2. ClipArmy" in tekst and "Nederlandse YouTube-kanaal" in tekst
