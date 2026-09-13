import { useState } from 'react'
import { addTradeSignal, deleteTradeSignal, getTradeSignals, setTradeSignalOutcome } from '../lib/localStore'
import {
  CHAINS,
  fetchPriceHistoryByContract,
  fetchPriceHistoryByCoin,
  PRESET_ASSETS,
  QUOTE_CURRENCIES,
} from '../lib/marketData'
import { buildTradeIdea, type TradeIdea } from '../lib/signalEngine'
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

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [idea, setIdea] = useState<TradeIdea | null>(null)
  const [assetLabel, setAssetLabel] = useState('')
  const [currencySymbol, setCurrencySymbol] = useState(QUOTE_CURRENCIES[0].symbol)
  const [saved, setSaved] = useState(false)

  const [history, setHistory] = useState(getTradeSignals())

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
      setCurrencySymbol(QUOTE_CURRENCIES.find((c) => c.code === currency)?.symbol ?? '')
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
          {loading ? 'Bezig met ophalen...' : 'Analyseer'}
        </button>

        {error && <p className="text-sm text-red-600">{error}</p>}
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
