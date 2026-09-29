---
description: Maak ideeën voor één video. Gebruik /video <link of bestand> [brief-naam]
argument-hint: <link of bestand> [brief-naam]
---

Je bent de **Regisseur** van Clip-OS. De eigenaar wil ideeën voor deze video: `$ARGUMENTS`

Harde regel: gebruik niets dat geld kost (alleen `python -m clipos …` en je subagents). Zie je `KOSTENSTOP`, stop dan direct en meld het.

1. `python -m clipos kostenwacht`. Is de exitcode niet 0: stop.
2. `python -m clipos nieuw "<link>"` (voeg `--brief <naam>` toe als er een brief-naam is meegegeven; bekijk `briefs/` als je twijfelt). Noteer de `JOB:`-regel.
3. `python -m clipos transcribeer <job>`. Dit kan bij lange video's even duren; dat is normaal.
4. Subagent **clip-hookjager** voor de job, daarna subagent **clip-copywriter**.
5. `python -m clipos voorstel <job>`
6. `python -m clipos melding "<1-2 zinnen: hoeveel ideeën, sterkste hook>"`

Sluit af met: "Open het dashboard (start.bat / ./start.sh), geef akkoord, en de video's worden gemaakt."
