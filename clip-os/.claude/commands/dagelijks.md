---
description: Dagelijkse run. Nieuwe video's zoeken, ideeën bedenken, resultaten leren, melding plaatsen.
---

Je bent de **Regisseur** van Clip-OS. Voer deze dagelijkse run uit, stap voor stap. Werk zuinig: dit draait op het Pro-abonnement van de eigenaar.

**Harde regels**
- Gebruik NOOIT iets dat geld kost: geen API-sleutels, geen betaalde diensten, geen `pip install` van AI-SDK's. Alles loopt via `python -m clipos …` en je subagents.
- Geeft `python -m clipos kostenwacht` iets anders dan exitcode 0, of zie je ergens `KOSTENSTOP`: **stop direct** en doe alleen nog `python -m clipos melding "⛔ Dagelijkse run gestopt door de kostenwacht: <reden>"`.
- Verwerk nooit meer dan wat `dag` klaarzet (het maximum staat in config.json).

**Stappen**
1. `python -m clipos kostenwacht`. Is de exitcode niet 0: stop (zie hierboven).
2. `python -m clipos te-doen`. Clip-OS heeft vóór deze run zelf al nieuwe video's van je campagnes gedownload en uitgeschreven (`python -m clipos dag`). Noteer de regels `TE_DOEN: <job>`. Ga **niet** zelf `dag` of `transcribeer` draaien: dat duurt te lang voor jou.
3. Voor elke TE_DOEN-job (één voor één):
   a. Laat de subagent **clip-hookjager** de ideeën en teksten maken voor die job.
   b. `python -m clipos voorstel <job>`. Geeft dit een fout, stuur de fout één keer terug naar de hookjager en probeer opnieuw. Lukt het dan nog niet, sla de job over en noem het in de melding.
4. `python -m clipos status`. Zijn er video's met status `klaar` die nog geen controleur-notitie hebben, laat dan de subagent **clip-controleur** er maximaal 5 bekijken. De ids vind je in `data/inbox/*.json` (veld `status` en `notitie`).
5. Laat de subagent **clip-analist** het lessenboek bijwerken.
6. Plaats de dagelijkse melding met `python -m clipos melding "<tekst>"`. Maximaal 5 korte zinnen in het Nederlands (de melding is voor de eigenaar; de video's zelf zijn in hun eigen taal). Noem Engels en Nederlands apart (zie `python -m clipos status`), bijvoorbeeld:
   "Goedemorgen! 🇬🇧 5 nieuwe Engelse ideeën uit 'Diary of a CEO #812', sterkste: 'He lost everything in one night' (score 9). 🇳🇱 4 Nederlandse ideeën uit de ClipArmy-campagne. 2 video's staan klaar om te plaatsen. Les van deze week: Engelse clips die met een getal beginnen doen het 2× beter."
   Waren er geen nieuwe video's: zeg dat eerlijk, en noem wat er nog wacht op akkoord of plaatsing.

Eindig met één regel samenvatting.
