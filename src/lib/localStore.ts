import type { Product, StockCount, TradeOutcome, TradeSignal, WasteLog } from './types'

const KEYS = {
  products: 'voorraad-app:products',
  stockCounts: 'voorraad-app:stock_counts',
  wasteLogs: 'voorraad-app:waste_logs',
  tradeSignals: 'voorraad-app:trade_signals',
}

function read<T>(key: string): T[] {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T[]) : []
  } catch {
    return []
  }
}

function write<T>(key: string, items: T[]) {
  try {
    localStorage.setItem(key, JSON.stringify(items))
  } catch {
    // localStorage unavailable (private browsing, storage full) — write is dropped.
  }
}

export function getProducts(): Product[] {
  return read<Product>(KEYS.products).sort(
    (a, b) => (a.category || '').localeCompare(b.category || '') || a.name.localeCompare(b.name),
  )
}

export function addProduct(input: Omit<Product, 'id'>): Product {
  const product: Product = { id: crypto.randomUUID(), ...input }
  write(KEYS.products, [...read<Product>(KEYS.products), product])
  return product
}

export function updateProduct(id: string, patch: Partial<Product>) {
  write(
    KEYS.products,
    read<Product>(KEYS.products).map((p) => (p.id === id ? { ...p, ...patch } : p)),
  )
}

export function deleteProduct(id: string) {
  write(
    KEYS.products,
    read<Product>(KEYS.products).filter((p) => p.id !== id),
  )
  write(
    KEYS.stockCounts,
    read<StockCount>(KEYS.stockCounts).filter((c) => c.product_id !== id),
  )
  write(
    KEYS.wasteLogs,
    read<WasteLog>(KEYS.wasteLogs).filter((w) => w.product_id !== id),
  )
}

export function addStockCounts(
  entries: { product_id: string; quantity: number; counted_by: string }[],
) {
  const now = new Date().toISOString()
  const rows: StockCount[] = entries.map((e) => ({
    id: crypto.randomUUID(),
    counted_at: now,
    ...e,
  }))
  write(KEYS.stockCounts, [...read<StockCount>(KEYS.stockCounts), ...rows])
}

export function getWasteLogs(): WasteLog[] {
  return read<WasteLog>(KEYS.wasteLogs).sort(
    (a, b) => new Date(b.logged_at).getTime() - new Date(a.logged_at).getTime(),
  )
}

export function addWasteLog(input: Omit<WasteLog, 'id' | 'logged_at'>): WasteLog {
  const row: WasteLog = { id: crypto.randomUUID(), logged_at: new Date().toISOString(), ...input }
  write(KEYS.wasteLogs, [...read<WasteLog>(KEYS.wasteLogs), row])
  return row
}

export function getTradeSignals(): TradeSignal[] {
  return read<TradeSignal>(KEYS.tradeSignals).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
}

export function addTradeSignal(input: Omit<TradeSignal, 'id' | 'created_at' | 'outcome'>): TradeSignal {
  const row: TradeSignal = {
    id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
    outcome: 'open',
    ...input,
  }
  write(KEYS.tradeSignals, [...read<TradeSignal>(KEYS.tradeSignals), row])
  return row
}

export function setTradeSignalOutcome(id: string, outcome: TradeOutcome) {
  write(
    KEYS.tradeSignals,
    read<TradeSignal>(KEYS.tradeSignals).map((s) => (s.id === id ? { ...s, outcome } : s)),
  )
}

export function deleteTradeSignal(id: string) {
  write(KEYS.tradeSignals, read<TradeSignal>(KEYS.tradeSignals).filter((s) => s.id !== id))
}
