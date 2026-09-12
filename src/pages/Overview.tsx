import { subDays } from 'date-fns'
import { useEffect, useState } from 'react'
import { getProducts, getWasteLogs } from '../lib/localStore'

interface WasteTotal {
  product_id: string
  name: string
  unit: string
  category: string
  total: number
}

const PERIODS = [
  { label: '7 dagen', days: 7 },
  { label: '30 dagen', days: 30 },
  { label: '90 dagen', days: 90 },
]

export function Overview() {
  const [days, setDays] = useState(30)
  const [totals, setTotals] = useState<WasteTotal[]>([])
  const [entryCount, setEntryCount] = useState(0)

  useEffect(() => {
    const products = getProducts()
    const since = subDays(new Date(), days)
    const logs = getWasteLogs().filter((l) => new Date(l.logged_at) >= since)

    setEntryCount(logs.length)
    const byProduct = new Map<string, WasteTotal>()
    for (const log of logs) {
      const product = products.find((p) => p.id === log.product_id)
      if (!product) continue
      const existing = byProduct.get(log.product_id)
      if (existing) {
        existing.total += log.quantity
      } else {
        byProduct.set(log.product_id, {
          product_id: log.product_id,
          name: product.name,
          unit: product.unit,
          category: product.category || 'Overig',
          total: log.quantity,
        })
      }
    }
    setTotals([...byProduct.values()].sort((a, b) => b.total - a.total))
  }, [days])

  const maxTotal = Math.max(...totals.map((t) => t.total), 1)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Overzicht derving</h1>
        <p className="mt-1 text-sm text-neutral-500">Wat wordt er het meest weggegooid?</p>
      </div>

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

      {totals.length === 0 ? (
        <p className="rounded-xl border border-neutral-200 bg-white p-4 text-sm text-neutral-500">
          Geen derving ingevoerd in deze periode.
        </p>
      ) : (
        <>
          <p className="text-sm text-neutral-500">
            {entryCount} {entryCount === 1 ? 'melding' : 'meldingen'} in de afgelopen {days} dagen
          </p>
          <div className="space-y-2">
            {totals.map((t) => (
              <div key={t.product_id} className="rounded-xl border border-neutral-200 bg-white p-3">
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-medium text-neutral-900">{t.name}</span>
                  <span className="text-neutral-500">
                    {t.total} {t.unit}
                  </span>
                </div>
                <p className="mb-1.5 text-xs text-neutral-400">{t.category}</p>
                <div className="h-1.5 w-full rounded-full bg-neutral-100">
                  <div
                    className="h-1.5 rounded-full bg-neutral-900"
                    style={{ width: `${(t.total / maxTotal) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
