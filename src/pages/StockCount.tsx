import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { useName } from '../lib/useName'
import type { Product } from '../lib/types'

interface OrderLine {
  product: Product
  suggested: number
}

export function StockCount() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [name, setName] = useName()
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [orderList, setOrderList] = useState<OrderLine[] | null>(null)

  useEffect(() => {
    supabase
      .from('products')
      .select('*')
      .order('category')
      .order('name')
      .then(({ data, error }) => {
        if (error) setError(error.message)
        else setProducts(data)
        setLoading(false)
      })
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

  async function handleSubmit() {
    setError(null)
    const entries = Object.entries(counts).filter(([, v]) => v.trim() !== '')
    if (entries.length === 0) return setError('Vul minstens één voorraad in.')
    if (!name.trim()) return setError('Vul in wie de telling doet.')

    setSaving(true)
    const rows = entries.map(([product_id, qty]) => ({
      product_id,
      quantity: Number(qty),
      counted_by: name.trim(),
    }))
    const { error } = await supabase.from('stock_counts').insert(rows)
    setSaving(false)
    if (error) return setError(error.message)

    const lines: OrderLine[] = entries
      .map(([productId, qty]) => {
        const product = products.find((p) => p.id === productId)!
        const suggested = Math.max(product.par_level - Number(qty), 0)
        return { product, suggested }
      })
      .filter((line) => line.suggested > 0)
      .sort((a, b) => a.product.name.localeCompare(b.product.name))

    setOrderList(lines)
  }

  function copyOrderList() {
    if (!orderList) return
    const text = orderList.map((l) => `${l.product.name}: ${l.suggested} ${l.product.unit}`).join('\n')
    navigator.clipboard.writeText(text)
  }

  if (orderList) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-neutral-900">Bestellijst</h1>
        <p className="text-sm text-neutral-500">
          Op basis van de tellingen — dit is wat er bij Kreko besteld moet worden om weer op de
          streefvoorraad te komen.
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

        <div className="flex gap-2">
          <button
            type="button"
            onClick={copyOrderList}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
          >
            Kopieer lijst
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

      <input
        placeholder="Wie telt er (naam)?"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
      />

      {loading ? (
        <p className="text-sm text-neutral-400">Laden...</p>
      ) : products.length === 0 ? (
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
                        Streefvoorraad: {p.par_level} {p.unit}
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
          disabled={saving}
          className="w-full rounded-lg bg-neutral-900 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? 'Bezig...' : 'Bestellijst genereren'}
        </button>
      )}
    </div>
  )
}
