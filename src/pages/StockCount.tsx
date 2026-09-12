import { useEffect, useMemo, useState } from 'react'
import { addStockCounts, getProducts } from '../lib/localStore'
import { useName } from '../lib/useName'
import type { Product } from '../lib/types'

type Period = 'weekday' | 'weekend'

interface OrderLine {
  product: Product
  suggested: number
}

function defaultPeriod(): Period {
  const day = new Date().getDay() // 0 = zondag
  return day >= 1 && day <= 4 ? 'weekday' : 'weekend'
}

export function StockCount() {
  const [products, setProducts] = useState<Product[]>([])
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const [name, setName] = useName()
  const [error, setError] = useState<string | null>(null)
  const [orderList, setOrderList] = useState<OrderLine[] | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setProducts(getProducts())
  }, [])

  const grouped = useMemo(() => {
    const groups = new Map<string, Product[]>()
    for (const p of products) {
      const key = p.category || 'Overig'
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(p)
    }
    return [...groups.entries()]
  }, [products])

  function parLevelFor(product: Product) {
    return period === 'weekday' ? product.par_level_weekday : product.par_level_weekend
  }

  function handleSubmit() {
    setError(null)
    const entries = Object.entries(counts).filter(([, v]) => v.trim() !== '')
    if (entries.length === 0) return setError('Vul minstens één voorraad in.')
    if (!name.trim()) return setError('Vul in wie de telling doet.')

    addStockCounts(
      entries.map(([product_id, qty]) => ({
        product_id,
        quantity: Number(qty),
        counted_by: name.trim(),
      })),
    )

    const lines: OrderLine[] = entries
      .map(([productId, qty]) => {
        const product = products.find((p) => p.id === productId)!
        const suggested = Math.max(parLevelFor(product) - Number(qty), 0)
        return { product, suggested }
      })
      .filter((line) => line.suggested > 0)
      .sort((a, b) => a.product.name.localeCompare(b.product.name))

    setOrderList(lines)
  }

  function orderListText() {
    if (!orderList) return ''
    const label = period === 'weekday' ? 'doordeweeks (ma–do)' : 'weekend (vr–zo)'
    const lines = orderList.map((l) => `- ${l.product.name}: ${l.suggested} ${l.product.unit}`)
    return `Bestellijst (${label}):\n${lines.join('\n')}`
  }

  function copyOrderList() {
    navigator.clipboard.writeText(orderListText())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function mailOrderList() {
    const subject = encodeURIComponent('Bestellijst Kreko')
    const body = encodeURIComponent(orderListText())
    window.location.href = `mailto:?subject=${subject}&body=${body}`
  }

  function whatsappOrderList() {
    const text = encodeURIComponent(orderListText())
    window.open(`https://wa.me/?text=${text}`, '_blank')
  }

  if (orderList) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-neutral-900">Bestellijst</h1>
        <p className="text-sm text-neutral-500">
          Op basis van de tellingen — dit is wat er bij Kreko besteld moet worden om weer op de
          streefvoorraad te komen. Er is (nog) geen directe koppeling met Kreko's
          besteltoepassing, dus gebruik onderstaande knoppen om de lijst snel over te nemen.
        </p>

        {orderList.length === 0 ? (
          <p className="rounded-xl border border-neutral-200 bg-white p-4 text-sm text-neutral-500">
            Niets te bestellen — alle geteld producten zitten op of boven de streefvoorraad.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 text-left text-neutral-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Product</th>
                  <th className="px-4 py-2 font-medium">Bestellen</th>
                </tr>
              </thead>
              <tbody>
                {orderList.map((line) => (
                  <tr key={line.product.id} className="border-t border-neutral-100">
                    <td className="px-4 py-2">{line.product.name}</td>
                    <td className="px-4 py-2 font-medium">
                      {line.suggested} {line.product.unit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={copyOrderList}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
          >
            {copied ? 'Gekopieerd ✓' : 'Kopieer lijst'}
          </button>
          <button
            type="button"
            onClick={whatsappOrderList}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
          >
            Stuur via WhatsApp
          </button>
          <button
            type="button"
            onClick={mailOrderList}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
          >
            Mail de lijst
          </button>
          <button
            type="button"
            onClick={() => {
              setOrderList(null)
              setCounts({})
            }}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
          >
            Nieuwe telling
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Voorraad tellen</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Vul in hoeveel er nu is. De bestellijst wordt automatisch berekend.
        </p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setPeriod('weekday')}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${
            period === 'weekday' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
          }`}
        >
          Doordeweeks (ma–do)
        </button>
        <button
          type="button"
          onClick={() => setPeriod('weekend')}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${
            period === 'weekend' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'
          }`}
        >
          Weekend (vr–zo)
        </button>
      </div>

      <input
        placeholder="Wie telt er (naam)?"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
      />

      {products.length === 0 ? (
        <p className="text-sm text-neutral-400">
          Nog geen producten. Voeg eerst producten toe via het tabblad "Producten".
        </p>
      ) : (
        <div className="space-y-5">
          {grouped.map(([category, items]) => (
            <div key={category}>
              <h2 className="mb-2 text-sm font-semibold text-neutral-500">{category}</h2>
              <div className="space-y-2">
                {items.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-neutral-900">{p.name}</p>
                      <p className="text-xs text-neutral-400">
                        Streefvoorraad: {parLevelFor(p)} {p.unit}
                      </p>
                    </div>
                    <input
                      type="number"
                      step="any"
                      inputMode="decimal"
                      placeholder={p.unit}
                      value={counts[p.id] ?? ''}
                      onChange={(e) => setCounts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      className="w-24 rounded-lg border border-neutral-300 px-2 py-2 text-right text-sm"
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {products.length > 0 && (
        <button
          type="button"
          onClick={handleSubmit}
          className="w-full rounded-lg bg-neutral-900 py-3 text-sm font-medium text-white"
        >
          Bestellijst genereren
        </button>
      )}
    </div>
  )
}
