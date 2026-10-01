from datetime import date

import pytest

from clipos import claude_taken, trends


def test_normaliseer_berekent_views_per_dag():
    v = trends.normaliseer({"id": "abc123xyz", "title": "Big podcast", "view_count": 300000, "upload_date": "20260927",
                            "duration": 4500, "channel": "Founder Hours", "uploader_url": "https://www.youtube.com/@founderhours"},
                           vandaag=date(2026, 9, 30))
    assert v["dagen_oud"] == 3 and v["per_dag"] == 100000 and v["duur_min"] == 75
    assert v["url"] == "https://www.youtube.com/watch?v=abc123xyz" and v["geupload"] == "2026-09-27"


def test_normaliseer_zelfde_dag_deelt_niet_door_nul():
    v = trends.normaliseer({"id": "x" * 11, "view_count": 1000, "upload_date": "20260930"}, vandaag=date(2026, 9, 30))
    assert v["per_dag"] == 2000


def test_campagne_herkent_kanaal_via_handle_en_id():
    briefs = [("founder-vyro", {"bron_kanalen": ["https://www.youtube.com/@FounderHours/videos"]}),
              ("geld-cliparmy", {"bron_kanalen": ["https://www.youtube.com/channel/UCabc123"]})]
    assert trends.campagne_voor({"kanaal_url": "https://www.youtube.com/@founderhours"}, briefs) == "founder-vyro"
    assert trends.campagne_voor({"kanaal_url": "https://www.youtube.com/channel/UCabc123", "kanaal_id": "UCabc123"}, briefs) == "geld-cliparmy"
    assert trends.campagne_voor({"kanaal_url": "https://www.youtube.com/@iemandanders"}, briefs) == ""


def test_rapport_validatie():
    goed = {"videos": [{"titel": "t", "waarom": "w", "url": "https://www.youtube.com/watch?v=abcdef123", "toestemming": "onbekend"}]}
    assert trends.valideer_rapport(goed) == []
    fout = {"videos": [{"titel": "t", "waarom": "w", "url": "https://evil.example/x", "toestemming": "ja hoor"},
                       {"titel": "t", "waarom": "w", "url": "https://youtu.be/abcdef123", "toestemming": "campagne", "campagne": "bestaat-niet"}]}
    fouten = trends.valideer_rapport(fout)
    assert len(fouten) == 3
    assert trends.valideer_rapport({"videos": []})


def test_trends_taak_validatie():
    assert claude_taken.valideer("trends", {"taal": "EN", "onderwerp": "  AI  en   beleggen "}) == {"taal": "en", "onderwerp": "AI en beleggen"}
    assert claude_taken.prompt_voor("trends", {"taal": "nl", "onderwerp": ""}) == "/trends nl"
    for slecht in ({"taal": "de"}, {"taal": "en", "onderwerp": "x" * 81}, {"taal": "en", "onderwerp": "a; rm -rf /"}):
        with pytest.raises(ValueError):
            claude_taken.valideer("trends", slecht)


def test_ytdlp_gebruikt_systeemcertificaten():
    from clipos import werk
    opties = werk.ytdlp_opties(skip_download=True)
    assert "no-certifi" in opties["compat_opts"] and opties["skip_download"] and opties["quiet"]
