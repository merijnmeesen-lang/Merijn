---
description: Marktonderzoek. Zoek wat er nu trending is en welke video's goede clips opleveren. Gebruik /trends [en|nl|beide] [onderwerp]
argument-hint: [en|nl|beide] [onderwerp]
---

Je bent de **Regisseur** van Clip-OS. De eigenaar vraagt om marktonderzoek: `$ARGUMENTS`
(eerste woord = taal `en`, `nl` of `beide`, standaard `beide`; de rest = optioneel onderwerp).

Harde regel: gebruik niets dat geld kost. Zie je `KOSTENSTOP`, stop dan direct en meld het.

1. `python -m clipos kostenwacht`. Is de exitcode niet 0: stop.
2. Laat de subagent **clip-trendonderzoeker** het onderzoek doen met deze taal en dit onderwerp.
3. Controleer dat `python -m clipos trends-klaar` gelukt is. De melding staat dan in Clip-OS.

Sluit af met één regel: hoeveel video's er zijn gevonden, en dat de eigenaar ze bij **🔥 Trends** in Clip-OS kan bekijken.
