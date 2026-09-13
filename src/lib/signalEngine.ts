import { emaSeries, macd, rsi } from './indicators'

export type SignalType = 'KOPEN' | 'VERKOPEN' | 'AFWACHTEN'

export interface TradeIdea {
  signal: SignalType
  price: number
  stopLoss: number | null
  takeProfit: number | null
  rsi: number
  trendEma: number
  macdLine: number
  macdSignal: number
  reasons: string[]
}

const TREND_PERIOD = 50
const SWING_WINDOW = 10
const RISK_REWARD = 2

/** Combineert RSI, EMA-trend en een MACD-crossover tot één koop/verkoop-advies.
 * Puur regelgebaseerd (geen ML) — transparant te herleiden per reden. */
export function buildTradeIdea(prices: number[]): TradeIdea {
  if (prices.length < TREND_PERIOD + 2) {
    throw new Error(`Niet genoeg koersdata (minimaal ${TREND_PERIOD + 2} punten, kies een langere periode).`)
  }

  const price = prices.at(-1)!
  const rsiValue = rsi(prices, 14)
  const trendEmaSeries = emaSeries(prices, TREND_PERIOD)
  const trendEma = trendEmaSeries.at(-1)!
  const { macdLine, signalLine } = macd(prices)
  const macdNow = macdLine.at(-1)!
  const macdPrev = macdLine.at(-2)!
  const signalNow = signalLine.at(-1)!
  const signalPrev = signalLine.at(-2)!

  const bullishCross = macdPrev <= signalPrev && macdNow > signalNow
  const bearishCross = macdPrev >= signalPrev && macdNow < signalNow

  let score = 0
  const reasons: string[] = []

  if (price > trendEma) {
    score += 1
    reasons.push(`Prijs (${fmt(price)}) staat boven EMA${TREND_PERIOD} (${fmt(trendEma)}) — opwaartse trend.`)
  } else {
    score -= 1
    reasons.push(`Prijs (${fmt(price)}) staat onder EMA${TREND_PERIOD} (${fmt(trendEma)}) — neerwaartse trend.`)
  }

  if (rsiValue < 30) {
    score += 1
    reasons.push(`RSI is ${rsiValue.toFixed(1)} — oversold, kan een koopmoment zijn.`)
  } else if (rsiValue > 70) {
    score -= 1
    reasons.push(`RSI is ${rsiValue.toFixed(1)} — overbought, kan een verkoopmoment zijn.`)
  } else {
    reasons.push(`RSI is ${rsiValue.toFixed(1)} — neutraal gebied.`)
  }

  if (bullishCross) {
    score += 1
    reasons.push('MACD is net omhoog door het signaal gekruist — bullish trigger.')
  } else if (bearishCross) {
    score -= 1
    reasons.push('MACD is net omlaag door het signaal gekruist — bearish trigger.')
  } else {
    reasons.push(macdNow > signalNow ? 'MACD ligt boven het signaal, maar geen verse cross.' : 'MACD ligt onder het signaal, maar geen verse cross.')
  }

  let signal: SignalType = 'AFWACHTEN'
  if (score >= 2) signal = 'KOPEN'
  else if (score <= -2) signal = 'VERKOPEN'

  let stopLoss: number | null = null
  let takeProfit: number | null = null
  if (signal === 'KOPEN') {
    const swingLow = Math.min(...prices.slice(-SWING_WINDOW))
    stopLoss = Math.min(swingLow * 0.99, price * 0.98)
    const risk = price - stopLoss
    takeProfit = price + risk * RISK_REWARD
  } else if (signal === 'VERKOPEN') {
    const swingHigh = Math.max(...prices.slice(-SWING_WINDOW))
    stopLoss = Math.max(swingHigh * 1.01, price * 1.02)
    const risk = stopLoss - price
    takeProfit = price - risk * RISK_REWARD
  }

  return {
    signal,
    price,
    stopLoss,
    takeProfit,
    rsi: rsiValue,
    trendEma,
    macdLine: macdNow,
    macdSignal: signalNow,
    reasons,
  }
}

function fmt(v: number): string {
  return v.toLocaleString('nl-NL', { maximumFractionDigits: v < 1 ? 6 : 2 })
}
