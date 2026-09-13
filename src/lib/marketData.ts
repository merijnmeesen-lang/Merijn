// Koersdata via de publieke CoinGecko API (geen API-key nodig, wel rate-limited).

export interface Asset {
  label: string
  /** CoinGecko coin-id, bv. "bitcoin". */
  coinId: string
}

export const PRESET_ASSETS: Asset[] = [
  { label: 'Bitcoin (BTC)', coinId: 'bitcoin' },
  { label: 'Ethereum (ETH)', coinId: 'ethereum' },
  { label: 'Solana (SOL)', coinId: 'solana' },
  { label: 'BNB', coinId: 'binancecoin' },
  { label: 'XRP', coinId: 'ripple' },
  { label: 'Cardano (ADA)', coinId: 'cardano' },
  { label: 'Dogecoin (DOGE)', coinId: 'dogecoin' },
  { label: 'Polygon (MATIC)', coinId: 'matic-network' },
  { label: 'Chainlink (LINK)', coinId: 'chainlink' },
  { label: 'Avalanche (AVAX)', coinId: 'avalanche-2' },
]

export interface Chain {
  label: string
  /** CoinGecko "asset platform"-id. */
  platformId: string
}

export const CHAINS: Chain[] = [
  { label: 'Ethereum', platformId: 'ethereum' },
  { label: 'BNB Smart Chain', platformId: 'binance-smart-chain' },
  { label: 'Polygon', platformId: 'polygon-pos' },
  { label: 'Base', platformId: 'base' },
  { label: 'Arbitrum', platformId: 'arbitrum-one' },
  { label: 'Optimism', platformId: 'optimistic-ethereum' },
]

export interface PricePoint {
  timestamp: number
  price: number
}

export interface QuoteCurrency {
  code: string
  label: string
  symbol: string
}

/** CoinGecko ondersteunt tientallen fiat-valuta als `vs_currency`. Dit zijn de meest gebruikte. */
export const QUOTE_CURRENCIES: QuoteCurrency[] = [
  { code: 'aud', label: 'Australische dollar (AUD)', symbol: 'A$' },
  { code: 'usd', label: 'Amerikaanse dollar (USD)', symbol: '$' },
  { code: 'eur', label: 'Euro (EUR)', symbol: '€' },
  { code: 'gbp', label: 'Britse pond (GBP)', symbol: '£' },
]

const COINGECKO_BASE = 'https://api.coingecko.com/api/v3'

async function fetchMarketChart(url: string): Promise<PricePoint[]> {
  const res = await fetch(url)
  if (!res.ok) {
    if (res.status === 429) throw new Error('Te veel aanvragen bij CoinGecko, probeer over een minuut opnieuw.')
    if (res.status === 404) throw new Error('Munt of contractadres niet gevonden.')
    throw new Error(`Koersdata ophalen mislukt (status ${res.status}).`)
  }
  const data = (await res.json()) as { prices?: [number, number][] }
  if (!data.prices || data.prices.length === 0) throw new Error('Geen koersdata ontvangen.')
  return data.prices.map(([timestamp, price]) => ({ timestamp, price }))
}

/** Historische prijzen voor een preset munt (CoinGecko coin-id). `days` stuurt de granulariteit:
 * 1 dag → 5-minutelijks, 2–90 dagen → uurlijks. */
export function fetchPriceHistoryByCoin(coinId: string, vsCurrency: string, days: number): Promise<PricePoint[]> {
  return fetchMarketChart(
    `${COINGECKO_BASE}/coins/${encodeURIComponent(coinId)}/market_chart?vs_currency=${vsCurrency}&days=${days}`,
  )
}

/** Historische prijzen voor een willekeurige token via het contractadres op een chain. */
export function fetchPriceHistoryByContract(
  platformId: string,
  contractAddress: string,
  vsCurrency: string,
  days: number,
): Promise<PricePoint[]> {
  return fetchMarketChart(
    `${COINGECKO_BASE}/coins/${encodeURIComponent(platformId)}/contract/${encodeURIComponent(
      contractAddress.trim().toLowerCase(),
    )}/market_chart?vs_currency=${vsCurrency}&days=${days}`,
  )
}
