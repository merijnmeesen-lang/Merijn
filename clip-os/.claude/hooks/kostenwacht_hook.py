"""Claude Code-hook (PreToolUse, Bash): blokkeert elk commando dat een betaalde dienst kan gebruiken.

Exitcode 2 = Claude Code voert het commando NIET uit en toont de reden.
Gebruikt alleen de standaardbibliotheek, zodat de hook ook zonder venv werkt.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from clipos.kostenwacht import BETAALDE_SLEUTELS, VERBODEN_IMPORTS, ZWARTE_LIJST  # noqa: E402

EXTRA_PAKKETTEN = ["@anthropic-ai/sdk", "@anthropic-ai/claude-agent-sdk", "claude-agent-sdk", "openai-whisper-api"]


def reden_om_te_blokkeren(cmd: str) -> str | None:
    laag = cmd.lower()
    for host in ZWARTE_LIJST:
        if host in laag:
            return f"commando gebruikt betaalde dienst {host}"
    pakketten = VERBODEN_IMPORTS + EXTRA_PAKKETTEN
    installeer = re.search(r"\b(pip3?|uv|poetry|npm|pnpm|yarn|bun|brew)\b[^\n;&|]*\b(install|add)\b([^\n;&|]*)", laag)
    if installeer:
        args = installeer.group(3)
        for p in pakketten:
            if re.search(r"(^|[\s'\"=])" + re.escape(p.lower()) + r"($|[\s'\"=<>~\[])", args):
                return f"installatie van betaald pakket '{p}'"
    for sleutel in BETAALDE_SLEUTELS:
        if re.search(r"\b(export|set|setx)\s+" + sleutel.lower() + r"\b", laag) or re.search(r"\b" + sleutel.lower() + r"=\S", laag):
            return f"zet betaalde sleutel {sleutel}"
    if "clipos_kostenwacht_uit" in laag:
        return "probeert de kostenwacht uit te zetten"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    reden = reden_om_te_blokkeren(cmd)
    if reden:
        print(f"⛔ KOSTENSTOP: {reden}. Clip-OS mag niets gebruiken dat geld kost.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
