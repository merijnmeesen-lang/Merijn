# AUD Signalentool voor MT5

Een Python-tool die de Australische dollar analyseert tegen zijn belangrijkste
tegenhangers en per paar een handelssignaal geeft: **BUY / SELL / HOLD**, met
concrete entry-, stoploss- en take-profitprijzen.

> **Deze tool plaatst nooit orders.** Ze leest alleen koersdata uit MT5
> (read-only) en geeft advies. Het handelen zelf doe je handmatig in MT5.

## Geanalyseerde paren

AUDUSD, AUDJPY, AUDNZD, AUDCAD, AUDCHF, EURAUD, GBPAUD

## Strategie

- **Trendfilter:** EMA(fast) vs. EMA(slow) op de slotkoers (standaard 50/200).
  EMA(fast) > EMA(slow) = opwaartse trend, omgekeerd = neerwaartse trend.
- **Momentum:** RSI bevestigt de trend (standaard: RSI > 50 voor een BUY in
  een uptrend, RSI < 50 voor een SELL in een downtrend). Bevestigt het
  momentum de trend niet, dan is het signaal **HOLD**.
- **Stoploss:** ATR-gebaseerd — entry ∓ (ATR × multiplier).
- **Take-profit:** vaste risk/reward-ratio ten opzichte van het risico tot de
  stoploss (standaard 1:2).

Alle periodes en multipliers zijn instelbaar in [`config.yaml`](./config.yaml).

## Installatie

1. Zorg voor Python 3.10 of hoger.
2. Installeer de dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   Voor development (tests + linter) installeer je in plaats daarvan:

   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Belangrijk voor live data:** het `MetaTrader5`-package werkt alleen op
   Windows en vereist dat de **MT5-terminal open staat en ingelogd is** op
   het account waarvan je koersdata wilt uitlezen (algo-trading hoeft niet
   aangezet te zijn — de tool leest alleen data, ze plaatst geen orders).
   Zonder een bereikbare, ingelogde terminal (of op een niet-Windows systeem)
   valt de tool automatisch terug op deterministische demo-data, zodat je de
   tool ook kunt uittesten zonder MT5.

## Gebruik

```bash
python analyze.py
```

Voorbeeldoutput:

```
======================================================================
AUD SIGNALENTOOL -- alleen advies, plaatst nooit zelf orders
======================================================================
Paar     Signaal Trend    RSI      Entry   Stoploss  Take-profit  Bron
----------------------------------------------------------------------
AUDUSD   SELL   DOWN    40.9    0.64027    0.64464      0.63154  MT5 (live)
AUDJPY   HOLD   UP      40.7   97.60115          -            -  MT5 (live)
...
----------------------------------------------------------------------
Samenvatting: 0 BUY, 1 SELL, 6 HOLD
```

De kolom "Bron" laat zien of de data van een live MT5-verbinding komt, of
(bij het ontbreken daarvan) van de ingebouwde demo-dataset.

## Configuratie

Pas [`config.yaml`](./config.yaml) aan om de strategie te finetunen, zonder
de code te wijzigen:

```yaml
pairs: [AUDUSD, AUDJPY, AUDNZD, AUDCAD, AUDCHF, EURAUD, GBPAUD]
timeframe: H1        # M1, M5, M15, M30, H1, H4, D1
bars_count: 300       # moet ruim boven ema_slow liggen

ema_fast: 50
ema_slow: 200

rsi_period: 14
rsi_buy_threshold: 50.0
rsi_sell_threshold: 50.0

atr_period: 14
atr_multiplier: 1.5

rr_ratio: 2.0         # take-profit = 1:2 ten opzichte van het risico
```

Let op: sommige brokers gebruiken een suffix in hun symboolnamen (bv.
`AUDUSD.a` of `AUDUSDm`). Pas in dat geval de `pairs`-lijst aan naar de exacte
symboolnamen zoals ze in het MT5 Market Watch-venster staan.

## Tests

De unit tests draaien volledig op vaste, deterministische sample-data — er is
**geen live MT5-verbinding nodig** om de tests uit te voeren:

```bash
pytest
```

Ze valideren:
- de indicatorberekeningen (EMA, RSI, ATR) tegen handmatig uitgerekende
  waarden en bekende randgevallen (vlakke markt, alleen stijgingen/dalingen);
- dat het signaal (BUY/SELL/HOLD) correct volgt uit de trend/momentum-combinatie;
- dat stoploss en take-profit correct berekend worden uit ATR, de
  multiplier en de risk/reward-ratio.

## Linter

```bash
ruff check .
```

## Projectstructuur

```
mt5-aud-signals/
├── analyze.py              # entrypoint: haalt data op, print het rapport
├── config.yaml              # instelbare strategie-parameters
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml           # ruff- en pytest-configuratie
├── mt5_signals/
│   ├── config.py            # laden/valideren van config.yaml
│   ├── mt5_client.py        # read-only MT5-koppeling (lazy import)
│   ├── sample_data.py       # deterministische demo-data (fallback)
│   ├── data_source.py       # kiest live MT5 of demo-data
│   ├── indicators.py        # EMA, RSI, ATR (pure pandas-functies)
│   ├── signals.py           # signaal-/SL/TP-logica
│   └── report.py            # terminal-rapportage
└── tests/
    ├── test_indicators.py
    └── test_signals.py
```

## Disclaimer

Deze tool is bedoeld als hulpmiddel bij handmatige analyse en plaatst zelf
**geen** orders. De gegenereerde signalen zijn geen financieel advies; de
gebruiker is zelf verantwoordelijk voor elke handelsbeslissing in MT5.
