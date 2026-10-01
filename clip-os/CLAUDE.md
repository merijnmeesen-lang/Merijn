# Clip-OS: instructies voor Claude

Dit is Clip-OS: een lokaal systeem dat van lange (podcast)video's korte clips maakt voor YouTube Shorts,
in het Engels (The Money Clip) en Nederlands (De Geldclip). De eigenaar is geen programmeur: leg dingen
in gewoon Nederlands uit en geef stap-voor-stap instructies.

## Harde regels (nooit breken)
- **Nooit kosten.** Geen betaalde API's, SDK's of diensten (anthropic, openai, elevenlabs, …). Alles draait
  gratis en lokaal; Claude zelf draait via het Pro-abonnement van de eigenaar. De kostenwacht
  (`clipos/kostenwacht.py`, `.claude/hooks/kostenwacht_hook.py`) nooit uitzetten of omzeilen.
- **Plaatsen doet de eigenaar zelf.** Bouw geen automatisch uploaden naar YouTube/TikTok/clipplatforms.
- Clippen alleen met toestemming (via campagnes). Campagne-eisen in `briefs/*.json` gaan voor.

## Opbouw
- `clipos/`: Python-pakket (`python -m clipos …`): download (yt-dlp), transcriptie (faster-whisper),
  montage (ffmpeg + OpenCV), controle, inbox, dagelijkse scout.
- `clipos/dashboard.py` + `clipos/web/` (index.html, app.css, app.js): de Clip-OS-webapp op
  http://127.0.0.1:8765 (start.bat). Geen build-stap; gewone HTML/CSS/JS.
- `clipos/claude_taken.py`: start Claude-taken vanuit de webapp (`claude -p`, Pro-login, max 80 stappen).
- `.claude/agents/`: de agents (hookjager, copywriter, controleur, analist, scout).
  `.claude/commands/`: /video, /dagelijks, /campagne.
- `config.json` en `lessenboek.md` zijn persoonlijk en staan niet in git (ze worden aangemaakt uit `config.voorbeeld.json`
  en `lessenboek.voorbeeld.md`). Nieuwe config-opties altijd met een standaardwaarde lezen (`.get`), want
  bestaande installaties hebben ze nog niet. `briefs/` (campagnes), `branding/`.
- Montage: `clipos/tempo.py` (stiltes/uhm's eruit, zooms), `clipos/reframe.py` (gezicht volgen met YuNet-model in
  `clipos/modellen/`, split-screen bij twee sprekers), `clipos/render.py`. Aan/uit via `montage` in config.json.
- `clipos/views.py`: views/likes van geplaatste video's ophalen via de link (yt-dlp, alleen lezen).
- `clipos/trends.py` + agent `clip-trendonderzoeker` + `/trends`: marktonderzoek (pagina Trends).
- Updates: `update.bat` (git pull). Eenmalige overstap vanaf de zip-versie: `overzetten.bat`.
- Werkdata (niet in git): `jobs/`, `output/`, `data/`.
- yt-dlp altijd via `werk.ytdlp_opties(...)` aanroepen (systeemcertificaten; nodig bij antivirus zoals Norton).
  Uitvoer is UTF-8 (`utf8_uitvoer` in `__main__`); Windows gebruikt anders cp1252 en crasht op emoji.

## Na een wijziging
- Tests: `python -m pytest` (installeer eerst `pip install pytest` in de venv als dat nog niet is gebeurd).
- `python -m clipos kostenwacht` moet groen blijven.
- Vertel de eigenaar dat hij Clip-OS opnieuw moet starten (zwarte venster sluiten, `start.bat` openen)
  zodat de wijziging actief wordt.
