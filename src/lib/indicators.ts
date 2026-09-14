// Technische indicatoren, berekend op een reeks slotkoersen (oud → nieuw).

export function sma(values: number[], period: number): number {
  const window = values.slice(-period)
  return window.reduce((sum, v) => sum + v, 0) / window.length
}

/** Exponential moving average als array, gelijke lengte als input. De eerste
 * `period - 1` waarden zijn `NaN` (nog niet genoeg data). */
export function emaSeries(values: number[], period: number): number[] {
  const result = new Array(values.length).fill(NaN)
  if (values.length < period) return result

  const k = 2 / (period + 1)
  let prev = sma(values.slice(0, period), period)
  result[period - 1] = prev

  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k)
    result[i] = prev
  }
  return result
}

export function ema(values: number[], period: number): number {
  return emaSeries(values, period).at(-1) ?? NaN
}

/** RSI (Wilder's smoothing), laatste waarde. */
export function rsi(values: number[], period = 14): number {
  if (values.length < period + 1) return NaN

  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const change = values[i] - values[i - 1]
    if (change >= 0) avgGain += change
    else avgLoss -= change
  }
  avgGain /= period
  avgLoss /= period

  for (let i = period + 1; i < values.length; i++) {
    const change = values[i] - values[i - 1]
    const gain = change >= 0 ? change : 0
    const loss = change < 0 ? -change : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
  }

  if (avgGain === 0 && avgLoss === 0) return 50
  if (avgLoss === 0) return 100
  const rs = avgGain / avgLoss
  return 100 - 100 / (1 + rs)
}

export interface MacdResult {
  macdLine: number[]
  signalLine: number[]
  histogram: number[]
}

/** MACD als volledige reeksen (nodig om een crossover te herkennen). */
export function macd(values: number[], fast = 12, slow = 26, signal = 9): MacdResult {
  const fastEma = emaSeries(values, fast)
  const slowEma = emaSeries(values, slow)
  const macdLine = values.map((_, i) =>
    Number.isNaN(fastEma[i]) || Number.isNaN(slowEma[i]) ? NaN : fastEma[i] - slowEma[i],
  )

  const macdValid = macdLine.filter((v) => !Number.isNaN(v))
  const signalValid = emaSeries(macdValid, signal)
  const signalLine = new Array(values.length).fill(NaN)
  const offset = macdLine.length - macdValid.length
  signalValid.forEach((v, i) => {
    signalLine[offset + i] = v
  })

  const histogram = macdLine.map((v, i) => (Number.isNaN(v) || Number.isNaN(signalLine[i]) ? NaN : v - signalLine[i]))

  return { macdLine, signalLine, histogram }
}
