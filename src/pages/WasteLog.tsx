import { useEffect, useState, type FormEvent } from 'react'
import { supabase } from '../lib/supabase'
import { useName } from '../lib/useName'
import type { Product, WasteLog as WasteLogRow } from '../lib/types'

const REASONS = ['Over datum', 'Aangebrand/mislukt', 'Retour klant', 'Gevallen/gemorst', 'Anders']

export function WasteLog() {
  const [products, setProducts] = useState<Product[]>([])
  const [recent, setRecent] = useState<(WasteLogRow & { products: Pick<Product, 'name' | 'unit'> })[]>([])
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState(REASONS[0])
  const [name, setName] = useName()
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function loadRecent() {
    const { data } = await supabase
      .from('waste_logs')
      .select('*, products(name, unit)')
      .order('logged_at', { ascending: false })
      .limit(10)
    if (data) setRecent(data)
  }

  useEffect(() => {
    supabase
      .from('products')
      .select('*')
      .order('name')
      .then(({ data }) => {
        if (data) {
          setProducts(data)
          setProductId((current) => current || data[0]?.id || '')
        }
      })
    loadRecent()
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!productId) return setError('Kies een product.')
    if (!name.trim()) return setError('Vul in wie dit invoert.')
    const qty = Number(quantity)
    if (!qty || qty <= 0) return setError('Vul een geldige hoeveelheid in.')

    setSaving(true)
    const { error } = await supabase.from('waste_logs').insert({
      product_id: productId,
      quantity: qty,
      reason,
      logged_by: name.trim(),
    })
    setSaving(false)
    if (error) return setError(error.message)

    setQuantity('')
    await loadRecent()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Derving invoeren</h1>
        <p className="mt-1 text-sm text-neutral-500">Wat is er weggegooid, en waarom?</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
        <input
          placeholder="Wie ben jij?"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />

        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        >
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>

        <input
          type="number"
          step="any"
          inputMode="decimal"
          placeholder="Hoeveelheid"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />

        <select
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        >
          {REASONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={saving || products.length === 0}
          className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? 'Bezig...' : 'Invoeren'}
        </button>
        {products.length === 0 && (
          <p className="text-xs text-neutral-400">
            Nog geen producten. Voeg eerst producten toe via het tabblad "Producten".
          </p>
        )}
      </form>

      {recent.length > 0 && (
        <div>
          <h2 className="mb-2 text-sm font-semibold text-neutral-500">Laatst ingevoerd</h2>
          <div className="space-y-1">
            {recent.map((r) => (
              <div
                key={r.id}
                className="flex justify-between rounded-lg border border-neutral-100 bg-white px-3 py-2 text-sm"
              >
                <span>
                  {r.products.name} — {r.quantity} {r.products.unit} ({r.reason})
                </span>
                <span className="text-neutral-400">{r.logged_by}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
