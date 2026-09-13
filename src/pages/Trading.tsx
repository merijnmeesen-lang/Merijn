import { useState } from 'react'
import {
  addTradeSignal,
  deleteTradeSignal,
  getRiskSettings,
  getTradeSignals,
  setRiskSettings,
  setTradeSignalOutcome,
} from '../lib/localStore'
import {
  CHAINS,
  fetchPriceHistoryByContract,
  fetchPriceHistoryByCoin,
  PRESET_ASSETS,
  QUOTE_CURRENCIES,
} from '../lib/marketData'
import { buildTradeIdea, computePositionSize, type TradeIdea } from '../lib/signalEngine'
import type { TradeOutcome } from '../lib/types'

const PERIODS = [
  { label: '24 uur', days: 1 },
  { label: '7 dagen', days: 7 },
  { label: '30 dagen', days: 30 },
]

const SIGNAL_STYLES: Record<TradeIdea['signal'], string> = {
  KOPEN: 'bg-green-100 text-green-800 border-green-200',
  VERKOPEN: 'bg-red-100 text-red-800 border-red-200',
  AFWACHTEN: 'bg-neutral-100 text-neutral-600 border-neutral-200',
}

export function Trading() {
  const [mode, setMode] = useState<'preset' | 'contract'>('preset')
  const [coinId, setCoinId] = useState(PRESET_ASSETS[0].coinId)
  const [platformId, setPlatformId] = useState(CHAINS[0].platformId)
  const [address, setAddress] = useState('')
  const [currency, setCurrency] = useState(QUOTE_CURRENCIES[0].code)
  const [days, setDays] = useState(7)
  const currencySymbol = QUOTE_CURRENCIES.find((c) => c.code === currency)?.symbol ?? ''

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [idea, setIdea] = useState<TradeIdea | null>(null)
  const [assetLabel, setAssetLabel] = useState('')
  const [saved, setSaved] = useState(false)

  const [history, setHistory] = useState(getTradeSignals())

  const [risk, setRisk] = useState(getRiskSettings())

  function updateRisk(patch: Partial<typeof risk>) {
    const next = { ...risk, ...patch }
    setRisk(next)
    setRiskSettings(next)
  }

  const [scanResults, setScanResults] = useState<{ label: string; idea: TradeIdea }[] | null>(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)

  async function runScan() {
    setScanLoading(true)
    setScanError(null)
    setScanResults(null)
    try {
      const results: { label: string; idea: TradeIdea }[] = []
      for (const asset of PRESET_ASSETS) {
        try {
          const points = await fetchPriceHistoryByCoin(asset.coinId, currency, days)
          results.push({ label: asset.label, idea: buildTradeIdea(points.map((p) => p.price)) })
        } catch {
          // Sla deze munt over (bv. tijdelijke rate limit) en ga door met de rest van de watchlist.
        }
      }
      if (results.length === 0) throw new Error('Geen enkele munt kon worden opgehaald, probeer het zo weer.')
      results.sort((a, b) => Math.abs(b.idea.score) - Math.abs(a.idea.score))
      setScanResults(results)
    } catch (e) {
      setScanError(e instanceof Error ? e.message : 'Scan mislukt.')
    } finally {
      setScanLoading(false)
    }
  }

  function saveScanResult(label: string, idea: TradeIdea) {
    addTradeSignal({
      asset_label: label,
      currency_symbol: currencySymbol,
      signal: idea.signal,
      price: idea.price,
      stop_loss: idea.stopLoss,
      take_profit: idea.takeProfit,
      reasons: idea.reasons,
    })
    setHistory(getTradeSignals())
  }

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    setIdea(null)
    setSaved(false)
    try {
      const label =
        mode === 'preset'
          ? PRESET_ASSETS.find((a) => a.coinId === coinId)?.label ?? coinId
          : `${address.trim()} (${CHAINS.find((c) => c.platformId === platformId)?.label})`

      if (mode === 'contract' && !address.trim()) {
        throw new Error('Vul een contractadres in.')
      }

      const points =
        mode === 'preset'
          ? await fetchPriceHistoryByCoin(coinId, currency, days)
          : await fetchPriceHistoryByContract(platformId, address, currency, days)

      const prices = points.map((p) => p.price)
      setAssetLabel(label)
      setIdea(buildTradeIdea(prices))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Onbekende fout bij het ophalen van koersdata.')
    } finally {
      setLoading(false)
    }
  }

  function saveSignal() {
    if (!idea) return
    addTradeSignal({
      asset_label: assetLabel,
      currency_symbol: currencySymbol,
      signal: idea.signal,
      price: idea.price,
      stop_loss: idea.stopLoss,
      take_profit: idea.takeProfit,
      reasons: idea.reasons,
    })
    setHistory(getTradeSignals())
    setSaved(true)
  }

  function updateOutcome(id: string, outcome: TradeOutcome) {
    setTradeSignalOutcome(id, outcome)
    setHistory(getTradeSignals())
  }

  function removeSignal(id: string) {
    deleteTradeSignal(id)
    setHistory(getTradeSignals())
  }

  const closed = history.filter((s) => s.outcome !== 'open')
  const wins = closed.filter((s) => s.outcome === 'winst').length
  const winRate = closed.length > 0 ? Math.round((wins / closed.length) * 100) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Trading signalen</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Regelgebaseerde koop/verkoop-signalen op basis van RSI, EMA-trend en MACD. Geen garantie op
          winst — test op een demo-account, dit is geen financieel advies.
        </p>
      </div>

      <div className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-neutral-700">Risico-instellingen</h2>
        <p className="text-xs text-neutral-500">
          Bepaalt hoe groot elke voorgestelde inzet is: bij het raken van de stop-loss verlies je nooit
          meer dan dit percentage van je account.
        </p>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-neutral-500">
            Account-omvang ({currencySymbol})
            <input
              type="number"
              min={0}
              step="any"
              value={risk.accountSize}
              onChange={(e) => updateRisk({ accountSize: Number(e.target.value) || 0 })}
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs text-neutral-500">
            Risico per trade (%)
            <input
              type="number"
              min={0}
              max={100}
              step="any"
              value={risk.riskPct}
              onChange={(e) => updateRisk({ riskPct: Number(e.target.value) || 0 })}
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
            />
          </label>
        </div>
      </div>

      <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-4">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('preset')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              mode === 'preset' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
            }`}
          >
            Bekende munt
          </button>
          <button
            type="button"
            onClick={() => setMode('contract')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              mode === 'contract' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
            }`}
          >
            Eigen token (contractadres)
          </button>
        </div>

        {mode === 'preset' ? (
          <select
            value={coinId}
            onChange={(e) => setCoinId(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          >
            {PRESET_ASSETS.map((a) => (
              <option key={a.coinId} value={a.coinId}>
                {a.label}
              </option>
            ))}
          </select>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <select
              value={platformId}
              onChange={(e) => setPlatformId(e.target.value)}
              className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
            >
              {CHAINS.map((c) => (
                <option key={c.platformId} value={c.platformId}>
                  {c.label}
                </option>
              ))}
            </select>
            <input
              placeholder="0x... contractadres"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="rounded-lg border border-neutral-300 px-3 py-2 text-sm sm:col-span-2"
            />
          </div>
        )}

        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        >
          {QUOTE_CURRENCIES.map((c) => (
            <option key={c.code} value={c.code}>
              Prijs in {c.label}
            </option>
          ))}
        </select>

        {currency === 'aud' && (
          <p className="rounded-lg bg-amber-50 p-2.5 text-xs text-amber-800">
            Let op: dit toont crypto-koersen omgerekend naar AUD, geen gehefboomde forex-handel. Voor
            echte on-chain AUD-blootstelling swap je meestal tegen een AUD-stablecoin (bv. AUDD) op een
            DEX — check eerst de liquiditeit, die is vaak dun.
          </p>
        )}

        <div className="flex gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              type="button"
              onClick={() => setDays(p.days)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                days === p.days ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={runAnalysis}
          disabled={loading}
          className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? 'Bezig met ophalen...' : 'Analyseer deze munt'}
        </button>

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
        <div>
          <h2 className="text-sm font-semibold text-neutral-700">Scan hele watchlist</h2>
          <p className="mt-1 text-xs text-neutral-500">
            Analyseert alle {PRESET_ASSETS.length} preset-munten in één keer en zet ze op volgorde van
            sterkste signaal, zodat je in één oogopslag ziet waar nu de beste (of enige) kans zit.
          </p>
        </div>
        <button
          type="button"
          onClick={runScan}
          disabled={scanLoading}
          className="w-full rounded-lg border border-neutral-900 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
        >
          {scanLoading ? 'Bezig met scannen...' : 'Scan alles'}
        </button>
        {scanError && <p className="text-sm text-red-600">{scanError}</p>}

        {scanResults && (
          <div className="space-y-2">
            {scanResults.map(({ label, idea: r }) => {
              const sizing =
                r.signal !== 'AFWACHTEN' ? computePositionSize(risk.accountSize, risk.riskPct, r.price, r.stopLoss!) : null
              return (
                <div key={label} className="rounded-lg border border-neutral-200 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-neutral-900">{label}</span>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${SIGNAL_STYLES[r.signal]}`}>
                      {r.signal}
                    </span>
                  </div>
                  <p className="mt-1 text-neutral-500">
                    Prijs {currencySymbol}
                    {fmt(r.price)}
                    {r.signal !== 'AFWACHTEN' && (
                      <>
                        {' '}
                        · SL {currencySymbol}
                        {fmt(r.stopLoss!)} · TP {currencySymbol}
                        {fmt(r.takeProfit!)}
                      </>
                    )}
                  </p>
                  {sizing && sizing.units > 0 && (
                    <p className="mt-1 text-neutral-700">
                      Voorstel: {sizing.units.toLocaleString('nl-NL', { maximumFractionDigits: 6 })} stuks ≈{' '}
                      {currencySymbol}
                      {fmt(sizing.positionValue)} (risico {currencySymbol}
                      {fmt(sizing.riskAmount)})
                    </p>
                  )}
                  {r.signal !== 'AFWACHTEN' && (
                    <button
                      type="button"
                      onClick={() => saveScanResult(label, r)}
                      className="mt-2 rounded-lg border border-neutral-300 px-2 py-1 text-xs font-medium text-neutral-700"
                    >
                      Signaal opslaan
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {idea && (
        <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-500">{assetLabel}</p>
              <p className="text-sm text-neutral-500">
                Huidige prijs:{' '}
                <span className="font-medium text-neutral-900">
                  {currencySymbol}
                  {fmt(idea.price)}
                </span>
              </p>
            </div>
            <span className={`rounded-lg border px-3 py-1.5 text-sm font-semibold ${SIGNAL_STYLES[idea.signal]}`}>
              {idea.signal}
            </span>
          </div>

          {idea.signal !== 'AFWACHTEN' && (
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <div className="rounded-lg bg-neutral-50 p-2">
                <p className="text-xs text-neutral-400">Entry</p>
                <p className="font-medium text-neutral-900">
                  {currencySymbol}
                  {fmt(idea.price)}
                </p>
              </div>
              <div className="rounded-lg bg-neutral-50 p-2">
                <p className="text-xs text-neutral-400">Stop-loss</p>
                <p className="font-medium text-red-600">
                  {currencySymbol}
                  {fmt(idea.stopLoss!)}
                </p>
              </div>
              <div className="rounded-lg bg-neutral-50 p-2">
                <p className="text-xs text-neutral-400">Take-profit</p>
                <p className="font-medium text-green-600">
                  {currencySymbol}
                  {fmt(idea.takeProfit!)}
                </p>
              </div>
            </div>
          )}

          {idea.signal !== 'AFWACHTEN' &&
            (() => {
              const sizing = computePositionSize(risk.accountSize, risk.riskPct, idea.price, idea.stopLoss!)
              if (sizing.units <= 0) return null
              return (
                <div className="rounded-lg bg-neutral-50 p-3 text-sm">
                  <p className="text-xs text-neutral-400">
                    Voorstel bij {currencySymbol}
                    {fmt(risk.accountSize)} account en {risk.riskPct}% risico
                  </p>
                  <p className="mt-1 font-medium text-neutral-900">
                    {sizing.units.toLocaleString('nl-NL', { maximumFractionDigits: 6 })} stuks ≈ {currencySymbol}
                    {fmt(sizing.positionValue)}
                  </p>
                  <p className="text-xs text-neutral-500">
                    Bij het raken van de stop-loss verlies je hier max. {currencySymbol}
                    {fmt(sizing.riskAmount)}.
                  </p>
                </div>
              )
            })()}

          <div>
            <h2 className="mb-1.5 text-sm font-semibold text-neutral-700">Waarom dit signaal</h2>
            <ul className="list-inside list-disc space-y-1 text-sm text-neutral-600">
              {idea.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          {idea.signal !== 'AFWACHTEN' && (
            <details className="rounded-lg bg-neutral-50 p-3 text-sm text-neutral-600">
              <summary className="cursor-pointer font-medium text-neutral-800">
                Hoe open ik dit in MetaMask?
              </summary>
              <ol className="mt-2 list-inside list-decimal space-y-1">
                <li>Open MetaMask (of een DEX zoals app.uniswap.org) en verbind je wallet.</li>
                <li>Zorg dat je op het juiste netwerk staat voor deze token.</li>
                <li>
                  {idea.signal === 'KOPEN'
                    ? 'Swap vanuit je stablecoin/ETH naar deze token, rond de aangegeven entry-prijs.'
                    : 'Swap deze token terug naar je stablecoin/ETH, rond de aangegeven entry-prijs.'}
                </li>
                <li>Controleer slippage en gasfee voor je bevestigt.</li>
                <li>
                  MetaMask/DEX-swaps hebben meestal geen automatische stop-loss of take-profit — houd de
                  prijs zelf in de gaten en swap handmatig terug op de aangegeven niveaus.
                </li>
              </ol>
            </details>
          )}

          <button
            type="button"
            onClick={saveSignal}
            disabled={saved}
            className="w-full rounded-lg border border-neutral-300 py-2 text-sm font-medium text-neutral-700 disabled:opacity-50"
          >
            {saved ? 'Signaal opgeslagen' : 'Signaal opslaan om later te beoordelen'}
          </button>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-700">Geschiedenis &amp; trackrecord</h2>
          {winRate !== null && (
            <span className="text-sm text-neutral-500">
              {wins}/{closed.length} winst ({winRate}%)
            </span>
          )}
        </div>

        {history.length === 0 ? (
          <p className="text-sm text-neutral-400">
            Nog geen signalen opgeslagen. Sla een signaal op en markeer later winst/verlies — zo bouw je
            een trackrecord op en zie je of de strategie werkt.
          </p>
        ) : (
          <div className="space-y-2">
            {history.map((s) => (
              <div key={s.id} className="rounded-xl border border-neutral-200 bg-white p-3 text-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-neutral-900">{s.asset_label}</span>{' '}
                    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${SIGNAL_STYLES[s.signal]}`}>
                      {s.signal}
                    </span>
                  </div>
                  <span className="text-xs text-neutral-400">{new Date(s.created_at).toLocaleString('nl-NL')}</span>
                </div>
                <p className="mt-1 text-neutral-500">
                  Entry {s.currency_symbol}
                  {fmt(s.price)}
                  {s.stop_loss !== null && ` · SL ${s.currency_symbol}${fmt(s.stop_loss)}`}
                  {s.take_profit !== null && ` · TP ${s.currency_symbol}${fmt(s.take_profit)}`}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  {(['open', 'winst', 'verlies'] as TradeOutcome[]).map((o) => (
                    <button
                      key={o}
                      type="button"
                      onClick={() => updateOutcome(s.id, o)}
                      className={`rounded-lg px-2 py-1 text-xs font-medium ${
                        s.outcome === o ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
                      }`}
                    >
                      {o === 'open' ? 'Open' : o === 'winst' ? 'Winst' : 'Verlies'}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => removeSignal(s.id)}
                    className="ml-auto text-neutral-400 hover:text-red-600"
                  >
                    Verwijderen
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function fmt(v: number): string {
  return v.toLocaleString('nl-NL', { maximumFractionDigits: v < 1 ? 6 : 2 })
}
