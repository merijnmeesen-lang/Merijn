import importlib.util
import socket
from pathlib import Path

import pytest

from clipos import kostenwacht

ROOT = Path(__file__).resolve().parent.parent


def laad_hook():
    spec = importlib.util.spec_from_file_location("hook", ROOT / ".claude" / "hooks" / "kostenwacht_hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_code_bevat_geen_betaalde_diensten():
    assert kostenwacht.scan_code() == []


def test_scan_vindt_verboden_import(tmp_path):
    (tmp_path / "x.py").write_text("import anthropic\nfrom openai import OpenAI\n")
    fouten = kostenwacht.scan_code(tmp_path)
    assert len(fouten) == 2


def test_betaalde_sleutel_geeft_harde_stop(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(SystemExit) as e:
        kostenwacht.bewaak()
    assert "KOSTENSTOP" in str(e.value)


def test_kostenwacht_kan_niet_uit(monkeypatch):
    monkeypatch.setenv("CLIPOS_KOSTENWACHT_UIT", "1")
    with pytest.raises(SystemExit):
        kostenwacht.bewaak()


@pytest.mark.parametrize("host,ok", [
    ("www.youtube.com", True),
    ("rr3---sn-abc.googlevideo.com", True),
    ("huggingface.co", True),
    ("api.anthropic.com", False),
    ("api.openai.com", False),
    ("evil-youtube.com", False),
    ("example.com", False),
])
def test_host_toegestaan(host, ok):
    assert kostenwacht.host_toegestaan(host) is ok


def test_zwarte_lijst_wint_van_toegestane_lijst(monkeypatch):
    monkeypatch.setattr(kostenwacht, "toegestane_sites", lambda: ["openai.com"])
    assert not kostenwacht.host_toegestaan("api.openai.com")


def test_netwerkslot_blokkeert_betaalde_dienst():
    oud = socket.getaddrinfo
    try:
        kostenwacht.installeer_netwerkslot()
        with pytest.raises(SystemExit):
            socket.getaddrinfo("api.anthropic.com", 443)
    finally:
        socket.getaddrinfo = oud


@pytest.mark.parametrize("cmd,blokkeer", [
    ("python -m clipos dag", False),
    ("pip install -r requirements.txt", False),
    ("pip install faster-whisper yt-dlp", False),
    ("pip install anthropic", True),
    ("pip3 install -q openai==1.2", True),
    ("npm install @anthropic-ai/sdk", True),
    ("curl https://api.openai.com/v1/chat/completions", True),
    ("export ANTHROPIC_API_KEY=sk-123", True),
    ("ANTHROPIC_API_KEY=sk-1 claude -p hi", True),
    ("CLIPOS_KOSTENWACHT_UIT=1 python -m clipos dag", True),
])
def test_hook(cmd, blokkeer):
    assert (laad_hook().reden_om_te_blokkeren(cmd) is not None) is blokkeer
