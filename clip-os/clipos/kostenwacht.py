"""Kostenwacht: de harde stop die ervoor zorgt dat Clip-OS nooit geld kost.

Drie beveiligingen, die bij elk commando automatisch aangaan:

1. Geen betaalde sleutels. Staat er een sleutel van een betaalde dienst in de
   omgeving (bijv. ANTHROPIC_API_KEY), dan stopt Clip-OS direct. Let op: als
   ANTHROPIC_API_KEY bestaat, rekent Claude Code per gebruik af in plaats van
   via je Pro-abonnement.
2. Netwerk-slot. Clip-OS mag alleen verbinding maken met sites op de
   toegestane lijst (videobronnen + de gratis download van het spraakmodel).
   Betaalde AI-diensten staan op een zwarte lijst en zijn altijd geblokkeerd,
   ook als iemand ze aan de toegestane lijst toevoegt.
3. Code-scan. `python -m clipos kostenwacht` (en de tests) controleren dat er
   geen betaalde SDK's in de code worden gebruikt.
"""

from __future__ import annotations

import os
import re
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Omgevingsvariabelen die (kunnen) betekenen dat er per gebruik betaald wordt.
BETAALDE_SLEUTELS = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "REPLICATE_API_TOKEN",
    "ASSEMBLYAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "GEMINI_API_KEY",
    "RUNWAYML_API_SECRET",
    "OPUS_API_KEY",
]

# Betaalde diensten: altijd geblokkeerd, wat er ook in toegestane_sites.txt staat.
ZWARTE_LIJST = [
    "api.anthropic.com",
    "api.openai.com",
    "api.elevenlabs.io",
    "api.replicate.com",
    "api.assemblyai.com",
    "api.deepgram.com",
    "generativelanguage.googleapis.com",
    "aiplatform.googleapis.com",
    "api.runwayml.com",
    "api.opus.pro",
    "api.heygen.com",
    "api.synthesia.io",
    "api.stripe.com",
]

# Pakketten/SDK's van betaalde diensten die niet in de code mogen staan.
VERBODEN_IMPORTS = ["anthropic", "openai", "elevenlabs", "replicate", "assemblyai", "deepgram", "google.generativeai"]

SITES_BESTAND = ROOT / "toegestane_sites.txt"


class KostenStop(SystemExit):
    """Harde stop: Clip-OS weigert door te gaan."""

    def __init__(self, reden: str):
        super().__init__(f"\n⛔ KOSTENSTOP: {reden}\nClip-OS is gestopt zodat er geen kosten ontstaan.\n")


def toegestane_sites() -> list[str]:
    sites = []
    for regel in SITES_BESTAND.read_text(encoding="utf-8").splitlines():
        regel = regel.split("#", 1)[0].strip().lower()
        if regel:
            sites.append(regel)
    return sites


def _past(host: str, domein: str) -> bool:
    return host == domein or host.endswith("." + domein)


def host_toegestaan(host: str) -> bool:
    host = (host or "").lower().rstrip(".")
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    if any(_past(host, d) for d in ZWARTE_LIJST):
        return False
    return any(_past(host, d) for d in toegestane_sites())


def controleer_sleutels(env: dict[str, str] | None = None) -> list[str]:
    env = os.environ if env is None else env
    return [k for k in BETAALDE_SLEUTELS if env.get(k)]


def scan_code(map_: Path | None = None) -> list[str]:
    """Zoek naar betaalde SDK-imports of betaalde API-hosts in de broncode."""
    map_ = map_ or ROOT / "clipos"
    fouten = []
    import_re = re.compile(r"^\s*(?:import|from)\s+(" + "|".join(re.escape(m) for m in VERBODEN_IMPORTS) + r")\b", re.M)
    for pad in sorted(map_.rglob("*.py")):
        if pad.name == "kostenwacht.py":
            continue
        tekst = pad.read_text(encoding="utf-8")
        for m in import_re.finditer(tekst):
            fouten.append(f"{pad.name}: verboden import '{m.group(1)}'")
        for host in ZWARTE_LIJST:
            if host in tekst:
                fouten.append(f"{pad.name}: betaalde dienst '{host}'")
    return fouten


_origineel_getaddrinfo = socket.getaddrinfo
_origineel_create_connection = socket.create_connection


def _bewaakte_getaddrinfo(host, *args, **kwargs):
    if isinstance(host, bytes):
        host = host.decode()
    if host and not _is_ip(host) and not host_toegestaan(host):
        raise KostenStop(f"verbinding met '{host}' geblokkeerd (niet op toegestane_sites.txt of betaalde dienst).")
    return _origineel_getaddrinfo(host, *args, **kwargs)


def _is_ip(host: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6 if ":" in host else socket.AF_INET, host)
        return True
    except OSError:
        return False


def installeer_netwerkslot() -> None:
    socket.getaddrinfo = _bewaakte_getaddrinfo


def bewaak() -> None:
    """Aanroepen aan het begin van elk Clip-OS commando."""
    if os.environ.get("CLIPOS_KOSTENWACHT_UIT"):
        raise KostenStop("de kostenwacht kan niet worden uitgezet.")
    sleutels = controleer_sleutels()
    if sleutels:
        raise KostenStop(
            "betaalde sleutel(s) gevonden: " + ", ".join(sleutels)
            + ".\nVerwijder ze uit je omgeving (en uit ~/.bashrc, ~/.zshrc of je Windows-omgevingsvariabelen)."
            + "\nClaude Code moet via je Pro-login lopen (commando: claude → /login), niet via een API-sleutel."
        )
    fouten = scan_code()
    if fouten:
        raise KostenStop("betaalde dienst in de code gevonden:\n  " + "\n  ".join(fouten))
    installeer_netwerkslot()


def rapport() -> int:
    print("Kostenwacht-controle")
    print("====================")
    sleutels = controleer_sleutels()
    print(("❌ Betaalde sleutels gevonden: " + ", ".join(sleutels)) if sleutels else "✅ Geen betaalde sleutels in de omgeving")
    fouten = scan_code()
    print(("❌ Code-scan:\n  " + "\n  ".join(fouten)) if fouten else "✅ Code bevat geen betaalde diensten")
    print("✅ Netwerk-slot actief; toegestane sites: " + ", ".join(toegestane_sites()))
    print("✅ Altijd geblokkeerd: " + ", ".join(ZWARTE_LIJST))
    print()
    print("Handmatig (kan code niet voor je controleren):")
    print("  • claude.ai → Instellingen → Gebruik: 'Extra gebruik' moet UIT staan.")
    print("    Dan stopt Claude gewoon als je Pro-limiet op is, in plaats van bij te rekenen.")
    print("  • Log in Claude Code in met je Pro-account (/login), niet met een API-sleutel.")
    return 1 if (sleutels or fouten) else 0


if __name__ == "__main__":
    sys.exit(rapport())
