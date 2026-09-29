# 🎬 Clip-OS

Claude bedenkt de clips en het systeem maakt de video's. **Jij plaatst ze** op YouTube en ClipArmy (of Klippie, Whop, Vyro).
Alles draait op je eigen computer en kost **€0**: alleen je Claude Pro-abonnement, met een harde kostenstop.

```
Elke ochtend (automatisch)                 Jij (±10 min per dag)
───────────────────────────                ─────────────────────────────
🔭 Scout: nieuwe video's van je campagnes
📥 Bron: downloaden + transcriberen
🎣 Hook-jager (Claude): sterkste momenten
✍️ Copywriter (Claude): titel + hashtags
📊 Analist (Claude): leert van je views
🔔 Melding in het dashboard        ──────►  💡 Ideeën bekijken → Akkoord / Afwijzen
                                                     │
✂️ Editor: 9:16, gezicht volgen,     ◄───────────────┘  (direct, gratis, zonder Claude)
   ondertitels, hook, geluid
🛡️ Controleur: techniek + brief-eisen
✅ Klaar om te plaatsen              ──────►  📤 Plaatsen op YouTube + ClipArmy
                                              📈 Views invullen → Claude leert
```

## 💶 Kosten: harde stop

| Laag | Wat het doet |
|---|---|
| **Code** (`clipos/kostenwacht.py`) | Elk commando stopt direct als er een betaalde sleutel is (zoals `ANTHROPIC_API_KEY`). Clip-OS kan alleen verbinden met sites in `toegestane_sites.txt`. Betaalde AI-diensten staan op een zwarte lijst die niet uit te zetten is. |
| **Claude Code** (`.claude/hooks`) | Blokkeert elk commando dat een betaalde dienst aanroept, een betaalde SDK installeert of een API-sleutel zet. |
| **Dagelijkse run** | Wist betaalde sleutels vóór het starten, controleert de kostenwacht, en begrenst Claude (`--max-turns 80`, maximaal 2 nieuwe video's per dag). |
| **Tests** | `pytest` faalt zodra iemand een betaalde dienst in de code zet. |

**Twee dingen die alleen jij kunt instellen (één keer):**
1. Ga op **claude.ai naar Instellingen → Gebruik** en zet **"Extra gebruik" UIT**. Dan stopt Claude gewoon als je Pro-limiet op is, in plaats van bij te rekenen.
2. Log in Claude Code in met je **Pro-account** (`claude` → `/login`), niet met een API-sleutel.

Controleren kan altijd met `python -m clipos kostenwacht`.

## 🛠️ Installatie (eenmalig)

Nodig: **Python 3.10+** ([python.org](https://www.python.org/downloads/); vink op Windows "Add to PATH" aan) en **Claude Code** ([installatie](https://code.claude.com/docs)), ingelogd met je Pro-account.

1. Download deze map `clip-os` naar je computer.
2. Dubbelklik **`setup.bat`** (Windows), of draai `./setup.sh` (Mac/Linux).
   Dit installeert alles gratis, ook ffmpeg. De eerste transcriptie downloadt eenmalig het gratis spraakmodel.

## ▶️ Gebruik

**Dashboard openen:** dubbelklik `start.bat` (of `./start.sh`). Het dashboard opent in je browser op `http://127.0.0.1:8765`.

**Campagne toevoegen:** open een terminal in deze map, typ `claude` en daarna:
```
/campagne <plak hier de campagnetekst van ClipArmy/Klippie/…>
```
Claude maakt er een brief van in `briefs/`, met lengte, hashtags, taal en de bronkanalen.

**Direct een video laten uitwerken:**
```
/video https://www.youtube.com/watch?v=… <brief-naam>
```

**Elke dag automatisch:** `python -m clipos planning` geeft het commando om de dagelijkse run in te plannen (Windows Taakplanner of Mac/Linux cron). Je computer moet op dat moment aan staan. Handmatig starten kan met `dagelijks.bat` / `./dagelijks.sh`.

**In het dashboard:**
- 💡 **Nieuwe ideeën:** pas eventueel de hook of titel aan, en klik **Akkoord** of **Afwijzen**.
- ✅ **Klaar om te plaatsen:** bekijk de video en klik op de titel of beschrijving om te kopiëren. De video staat ook in `output/…/video.mp4`, met een checklist in `PLAATSEN.md`.
- 📈 **Geplaatst:** vul na 1 tot 3 dagen de views in. De Analist leert daarvan en schrijft het in `lessenboek.md`.

## 🤖 De agents

| Agent | Wie | Wat |
|---|---|---|
| Regisseur | Claude (`/dagelijks`, `/video`) | stuurt de rest aan, schrijft de dagelijkse melding |
| Scout | Claude (`clip-scout`) + code | campagnetekst omzetten naar een brief; nieuwe video's van kanalen vinden |
| Bron | code (yt-dlp, faster-whisper) | downloaden en transcriberen, lokaal |
| Hook-jager | Claude (`clip-hookjager`) | sterkste momenten kiezen, met score en reden |
| Copywriter | Claude (`clip-copywriter`) | titel, beschrijving en hashtags volgens de brief |
| Editor | code (ffmpeg, OpenCV) | 9:16 met gezichtsvolging, woord-voor-woord ondertitels, hook bovenin, geluid op −14 LUFS |
| Controleur | code + Claude (`clip-controleur`) | techniek- en brief-eisen, en een blik op de beelden |
| Analist | Claude (`clip-analist`) | leert van views en afwijzingen, werkt `lessenboek.md` bij |

## 📁 Mappen

```
briefs/        campagne-eisen (één .json per campagne)
jobs/          werkmap per bronvideo (download, transcript, clips.json)
output/        KLAAR OM TE PLAATSEN: video.mp4 + PLAATSEN.md per clip
data/          inbox, meldingen, logboek
lessenboek.md  wat werkt, wat niet (houdt de Analist bij)
config.json    maximum per dag, spraakmodel, poort
```

## 🌍 Taal

De video krijgt altijd de taal van de bron: een Engelse podcast wordt een Engelse clip, met Engelse ondertitels, hook, titel en hashtags. Het dashboard en de meldingen aan jou blijven Nederlands.
- **Engels** (Vyro, Whop): de meeste campagnes en de hoogste tarieven. Zie `briefs/voorbeeld-engels.json`.
- **Nederlands** (ClipArmy, Klippie, ClipHub): minder campagnes en lagere tarieven, maar ook weinig concurrentie. Zie `briefs/voorbeeld.json`.
- Gebruik **per taal een apart account** op YouTube en TikTok. Het algoritme moet snappen voor wie je kanaal is.

## ⚠️ Goed om te weten

- **Snelheid:** transcriberen gebeurt op je processor. Een podcast van een uur duurt al snel 10 tot 30 minuten. Daarom draait dat 's ochtends automatisch. Voor Nederlands kun je in `config.json` `"whisper_model": "medium"` zetten. Dat is nauwkeuriger, maar trager.
- **Pro-limiet:** als je limiet op is, stopt Claude tot de reset. Dat kost niets, zolang "Extra gebruik" uit staat.
- **Alleen clippen met toestemming**, dus via campagnes. De brief bepaalt welke bronnen mogen.
- **Sites toevoegen:** komt een campagnebron van een andere gratis videosite, zet die dan in `toegestane_sites.txt`. Betaalde AI-diensten blijven altijd geblokkeerd.
- **Tests draaien:** `pip install pytest` en daarna `pytest`.
