// Forex-koersdata via de gratis Frankfurter API (ECB-referentiekoersen, geen key nodig). Levert
// alleen dagkoersen (één punt per handelsdag, geen weekend) — prima voor een swingstrategie op
// dag-EMA/RSI/MACD, niet geschikt om mee te scalpen op minuten zoals in MetaTrader zelf.

export interface PricePoint {
  timestamp: number
  price: number
}

export interface ForexCurrency {
  code: string
  label: string
}

export const FOREX_CURRENCIES: ForexCurrency[] = [
  { code: 'AUD', label: 'Australische dollar' },
  { code: 'USD', label: 'Amerikaanse dollar' },
  { code: 'EUR', label: 'Euro' },
  { code: 'GBP', label: 'Britse pond' },
  { code: 'CAD', label: 'Canadese dollar' },
  { code: 'CHF', label: 'Zwitserse frank' },
  { code: 'JPY', label: 'Japanse yen' },
  { code: 'NZD', label: 'Nieuw-Zeelandse dollar' },
  { code: 'NOK', label: 'Noorse kroon' },
  { code: 'SEK', label: 'Zweedse kroon' },
  { code: 'DKK', label: 'Deense kroon' },
  { code: 'PLN', label: 'Poolse zloty' },
  { code: 'HUF', label: 'Hongaarse forint' },
  { code: 'HKD', label: 'Hongkongse dollar' },
  { code: 'SGD', label: 'Singaporese dollar' },
  { code: 'ZAR', label: 'Zuid-Afrikaanse rand' },
]

const FRANKFURTER_BASE = 'https://api.frankfurter.dev/v1'

/** Dagkoersen voor `quote` per 1 `base`, over de laatste `days` kalenderdagen. */
export async function fetchForexHistory(base: string, quote: string, days: number): Promise<PricePoint[]> {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  const isoDate = (d: Date) => d.toISOString().slice(0, 10)

  const res = await fetch(`${FRANKFURTER_BASE}/${isoDate(start)}..${isoDate(end)}?base=${base}&symbols=${quote}`)
  if (!res.ok) {
    if (res.status === 404) throw new Error('Valutapaar niet gevonden.')
    throw new Error(`Koersdata ophalen mislukt (status ${res.status}).`)
  }
  const data = (await res.json()) as { rates?: Record<string, Record<string, number>> }
  if (!data.rates) throw new Error('Geen koersdata ontvangen.')

  const points = Object.entries(data.rates)
    .map(([date, rates]) => ({ timestamp: new Date(date).getTime(), price: rates[quote] }))
    .filter((p) => typeof p.price === 'number')
    .sort((a, b) => a.timestamp - b.timestamp)

  if (points.length === 0) throw new Error('Geen koersdata ontvangen voor dit paar.')
  return points
}
