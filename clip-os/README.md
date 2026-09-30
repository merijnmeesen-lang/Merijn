# 🎬 Clip-OS

Claude bedenkt de clips en het systeem maakt de video's. **Jij plaatst ze** op YouTube en ClipArmy (of Klippie, Whop, Vyro).
Je werkt erin via **Chrome**. Alles draait op je eigen computer en kost **€0**: alleen je Claude Pro-abonnement, met een harde kostenstop.

```
Elke ochtend (automatisch)                 Jij (±10 min per dag)
───────────────────────────                ─────────────────────────────
🔭 Scout: nieuwe video's van je campagnes
📥 Bron: downloaden + transcriberen
🎣 Hook-jager (Claude): sterkste momenten
✍️ Copywriter (Claude): titel + hashtags
📊 Analist (Claude): leert van je views
🔔 Melding in Clip-OS             ──────►  💡 Ideeën bekijken → Akkoord / Afwijzen
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
| **Dagelijkse run** | Wist betaalde sleutels vóór het starten, controleert de kostenwacht, en begrenst Claude (`--max-turns 80`, standaard 1 nieuwe bronvideo per taal per dag). |
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

## 🖥️ Werken in Clip-OS (in Chrome)

Dubbelklik **`start.bat`** (Windows) of draai `./start.sh` (Mac/Linux). Clip-OS opent in je browser op **http://127.0.0.1:8765**. Laat het venster open zolang je werkt. Tip: zet het in Chrome bij je bladwijzers, of kies ⋮ → *Opslaan en delen* → *Snelkoppeling maken* → *Openen als venster*. Dan werkt het als een los programma.

| App | Wat je er doet |
|---|---|
| 🏠 **Vandaag** | bericht van Claude, cijfers per taal, een link plakken zodat Claude begint, de dagelijkse run starten, activiteit |
| 💡 **Ideeën** | hook of titel aanpassen, en daarna **Akkoord, maak video** of afwijzen (✕) |
| 🎬 **Studio** | video's die nu gemaakt worden (gewone code, geen Claude-gebruik); mislukte opnieuw proberen |
| 📤 **Plaatsen** | video bekijken, op welk kanaal hij moet, titel en beschrijving kopiëren, mp4 downloaden, **Geplaatst** klikken |
| 📈 **Resultaten** | views invullen, top 10-grafiek, totalen per taal |
| 🎯 **Campagnes** | campagnetekst plakken zodat Claude hem invult, of zelf invullen in een formulier; aan/uit per campagne |
| 🤖 **Claude** | je team van agents (actieve agents lichten op), taken starten, **live logboek** en een **stopknop** |
| 📘 **Lessenboek** | wat Claude geleerd heeft van je views en afwijzingen |
| ⚙️ **Instellingen** | talen, accounts en daglimieten, spraakmodel, thema (donker/licht), status van de kostenwacht |

Met de taalknoppen bovenin (**Alle · 🇬🇧 EN · 🇳🇱 NL**) filter je elke pagina op taal.

**Claude vanuit de browser:** de knoppen *Laat Claude beginnen*, *Dagelijkse run* en *Laat Claude invullen* starten Claude Code op je computer, op je **Pro-login**. Er loopt één taak tegelijk, met maximaal 80 stappen. Betaalde sleutels worden altijd weggehaald voordat Claude start. Je kunt elke taak stoppen.

**Veilig:** Clip-OS is alleen bereikbaar vanaf je eigen computer. Elke actie vereist een geheime sleutel die alleen de Clip-OS-pagina kent. Andere websites kunnen dus niets starten of wijzigen.

### Zonder browser (terminal)

Alles kan ook in de terminal. Typ `claude` in deze map, en daarna:
```
/campagne <plak hier de campagnetekst>
/video https://www.youtube.com/watch?v=… <campagne-naam>
/dagelijks
```

**Elke dag automatisch:** `python -m clipos planning` geeft het commando om de dagelijkse run in te plannen (Windows Taakplanner of Mac/Linux cron). Je computer moet op dat moment aan staan. Handmatig starten kan met `dagelijks.bat` / `./dagelijks.sh`, of met de knop in Clip-OS.

## 🔥 Trends: als je niet weet wat je moet plaatsen

Open **Trends** in Clip-OS, kies Engels, Nederlands of beide (en eventueel een onderwerp) en klik op **Zoek wat trending is**. Dan gebeurt het volgende:
1. De **Trendonderzoeker** (Claude, via je Pro-account) zoekt op internet wat er deze week speelt rond geld, business en AI.
2. Clip-OS zoekt op YouTube de podcasts en interviews van deze week, en rekent uit welke het snelst stijgen in **views per dag**.
3. Je krijgt een lijst met per video het label **✅ Campagne** (clippen mag) of **⚠️ Toestemming onbekend**, plus de reden waarom er goede clips in zitten.
4. Met **Maak ideeën** werkt Clip-OS de video meteen uit.

Plaats alleen clips van makers die toestemming geven, bijvoorbeeld via een campagne.

## 🔄 Updates

### Eenmalig: overstappen naar updates met 1 klik
Heb je Clip-OS als zip gedownload? Stap dan één keer over naar een versie die zichzelf kan bijwerken:
1. Open **PowerShell** en typ `git --version`. Zie je een foutmelding, typ dan `winget install --id Git.Git -e`, sluit PowerShell en open het opnieuw.
2. Typ:
   ```
   cd $HOME\Documents
   git clone -b claude/tender-lovelace-ouybr3 https://github.com/merijnmeesen-lang/Merijn.git ClipOS
   ```
   Er opent een browservenster om in te loggen bij GitHub. Log in en klik op **Authorize**.
3. Open **Documenten → ClipOS → clip-os**. Dubbelklik **`overzetten.bat`**: dat neemt je accounts, campagnes, ideeën en video's mee uit de oude map. Dubbelklik daarna **`setup.bat`** (eenmalig).
4. Maak een nieuwe snelkoppeling naar **`start.bat`** in deze map, en verwijder de oude snelkoppeling.

### Daarna: updaten
Dubbelklik **`update.bat`**. Daarna sluit je het zwarte venster van Clip-OS en start je `start.bat` opnieuw. Je instellingen (`config.json`), lessenboek, campagnes en video's worden nooit overschreven.

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
output/en/     KLAAR OM TE PLAATSEN (Engels): video.mp4 + PLAATSEN.md per clip
output/nl/     KLAAR OM TE PLAATSEN (Nederlands)
data/          inbox, meldingen, logboek
lessenboek.md  wat werkt, wat niet, per taal (houdt de Analist bij)
config.json    jouw talen + accounts + daglimieten (wordt aangemaakt uit config.voorbeeld.json)
```

## 🌍 Twee talen: Engels én Nederlands

Clip-OS maakt Engelse en Nederlandse video's naast elkaar. De taal komt uit de campagne-brief (`"taal": "en"` of `"nl"`). Een Engelse bron krijgt Engelse ondertitels, hook, titel en hashtags, een Nederlandse bron krijgt Nederlandse. Clip-OS zelf en de meldingen aan jou blijven Nederlands.

| | 🇬🇧 Engels | 🇳🇱 Nederlands |
|---|---|---|
| Plaatsen op | je Engelse YouTube-kanaal (+ Vyro/Whop) | je Nederlandse YouTube-kanaal (+ ClipArmy/Klippie) |
| Voorbeeldbrief | `briefs/voorbeeld-engels.json` | `briefs/voorbeeld.json` |
| Output-map | `output/en/…` | `output/nl/…` |

- **Elke dag allebei:** in `config.json` → `talen` heeft elke taal een eigen daglimiet (standaard 1 nieuwe bronvideo per taal per dag), zodat de ene taal de andere niet verdringt. Daar zet je ook de naam van je account per taal neer. Die staat dan bij elke video ("📍 Plaats op: …").
- **In Clip-OS:** elke kaart heeft een taalbadge. Met de taalknoppen bovenin filter je op 🇬🇧 of 🇳🇱.
- **Leren per taal:** de Analist houdt de lessen voor Engels en Nederlands apart bij.
- Gebruik **per taal een apart YouTube- en TikTok-account**. Het algoritme moet snappen voor wie je kanaal is.
- Een Engelse campagne zonder clipplatform (alleen je eigen kanaal)? Laat `platform` leeg in de brief. Dan slaat de checklist de indienstap over.

## ⚠️ Goed om te weten

- **Snelheid:** transcriberen gebeurt op je processor. Een podcast van een uur duurt al snel 10 tot 30 minuten. Daarom draait dat 's ochtends automatisch. Voor Nederlands kun je in `config.json` `"whisper_model": "medium"` zetten. Dat is nauwkeuriger, maar trager.
- **Pro-limiet:** als je limiet op is, stopt Claude tot de reset. Dat kost niets, zolang "Extra gebruik" uit staat.
- **Alleen clippen met toestemming**, dus via campagnes. De brief bepaalt welke bronnen mogen.
- **Sites toevoegen:** komt een campagnebron van een andere gratis videosite, zet die dan in `toegestane_sites.txt`. Betaalde AI-diensten blijven altijd geblokkeerd.
- **Tests draaien:** `pip install pytest` en daarna `pytest`.
