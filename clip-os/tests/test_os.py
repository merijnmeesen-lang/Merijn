import json

import pytest

from clipos import claude_taken, dashboard


def test_claude_krijgt_geen_betaalde_sleutels(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-geheim")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ook")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = claude_taken.schone_omgeving()
    assert "ANTHROPIC_API_KEY" not in env and "OPENAI_API_KEY" not in env
    assert env["PATH"] == "/usr/bin"


@pytest.mark.parametrize("soort,data", [
    ("video", {"link": "geen link"}),
    ("video", {"link": "https://youtu.be/x", "brief": "../../geheim"}),
    ("video", {"link": "https://youtu.be/x", "brief": "bestaat-niet"}),
    ("campagne", {"tekst": "te kort"}),
    ("iets", {}),
])
def test_ongeldige_taken_worden_geweigerd(soort, data):
    with pytest.raises(ValueError):
        claude_taken.valideer(soort, data)


def test_prompts():
    # video: Clip-OS downloadt en transcribeert eerst zelf; Claude krijgt daarna alleen het denkwerk
    assert claude_taken.prompt_voor("video", {"link": "https://youtu.be/x", "brief": "", "job": "j1"}) == "/ideeen j1"
    assert claude_taken.prompt_voor("dagelijks", {}) == "/dagelijks"


def test_logboek_is_leesbaar():
    regels = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hallo"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Task", "input": {"subagent_type": "clip-hookjager", "description": "zoeken"}}]}},
        {"type": "assistant", "parent_tool_use_id": "t", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python -m clipos te-doen"}}]}},
        {"type": "result", "is_error": False, "result": "Klaar!"},
    ]
    uit = [r for m in regels for r in claude_taken._leesbaar(json.dumps(m))]
    assert uit == ["💬 Hallo", "🤖 Agent clip-hookjager: zoeken", "   ↳ ⚙️  python -m clipos te-doen", "✅ Klaar!"]


def test_taak_id_kan_geen_pad_zijn():
    with pytest.raises(ValueError):
        claude_taken._pad("../../etc/passwd")


def test_brief_validatie():
    b = dashboard.valideer_brief({"naam": "Test", "taal": "EN", "min_seconden": "20", "max_seconden": 50,
                                  "verplichte_hashtags": "#ad, #vyro\n#x", "bron_kanalen": "https://www.youtube.com/@a"})
    assert b["taal"] == "en" and b["verplichte_hashtags"] == ["#ad", "#vyro", "#x"] and b["min_seconden"] == 20
    for fout in ({"naam": "", "taal": "en"}, {"naam": "x", "taal": "nederlands"},
                 {"naam": "x", "taal": "en", "min_seconden": 60, "max_seconden": 30},
                 {"naam": "x", "taal": "en", "bron_links": "javascript:alert(1)"}):
        with pytest.raises(ValueError):
            dashboard.valideer_brief(fout)


def test_config_validatie_begrenst_daglimiet():
    cfg = dashboard.valideer_config({"talen": {"en": {"label": "EN", "account": "x", "max_nieuwe_bronnen_per_dag": 99}}})
    assert cfg["talen"]["en"]["max_nieuwe_bronnen_per_dag"] == 5
    with pytest.raises(ValueError):
        dashboard.valideer_config({"whisper_model": "gpt-4"})
    with pytest.raises(ValueError):
        dashboard.valideer_config({"talen": {"../x": {}}})


def test_video_en_afmaken_gaan_naar_ideeen_na_voorbereiding(tmp_path, monkeypatch):
    from clipos import werk
    assert claude_taken.prompt_voor("video", {"link": "https://youtu.be/x", "job": "20261001-abc"}) == "/ideeen 20261001-abc"
    assert claude_taken.prompt_voor("afmaken", {"job": "20261001-abc"}) == "/ideeen 20261001-abc"
    monkeypatch.setattr(werk, "JOBS", tmp_path)
    (tmp_path / "20261001-abc").mkdir()
    (tmp_path / "20261001-abc" / "job.json").write_text("{}")
    assert claude_taken.valideer("afmaken", {"job": "20261001-abc"}) == {"job": "20261001-abc"}
    for slecht in ("bestaat-niet", "../../etc", ""):
        with pytest.raises(ValueError):
            claude_taken.valideer("afmaken", {"job": slecht})


def test_open_jobs(tmp_path, monkeypatch):
    from clipos import productie, werk
    monkeypatch.setattr(werk, "JOBS", tmp_path)
    for naam, klaar in (("a-job", False), ("b-job", True)):
        d = tmp_path / naam
        d.mkdir()
        (d / "job.json").write_text('{"bron": "https://youtu.be/x"}')
        (d / "bron.mp4").write_bytes(b"x")
        if klaar:
            (d / "ideeen_geregistreerd").write_text("x")
    jobs = productie.open_jobs()
    assert [j["job"] for j in jobs] == ["a-job"] and jobs[0]["gedownload"] and not jobs[0]["uitgeschreven"]
