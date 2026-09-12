import { useEffect, useState, type FormEvent } from 'react'
import { addProduct, deleteProduct, getProducts, updateProduct } from '../lib/localStore'
import type { Product } from '../lib/types'

export function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [unit, setUnit] = useState('')
  const [parLevel, setParLevel] = useState('')

  useEffect(() => {
    setProducts(getProducts())
  }, [])

  function handleAdd(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim() || !unit.trim()) return setError('Vul naam en eenheid in.')

    addProduct({ name: name.trim(), category: category.trim(), unit: unit.trim(), par_level: Number(parLevel) || 0 })
    setProducts(getProducts())
    setName('')
    setCategory('')
    setUnit('')
    setParLevel('')
  }

  function handleParLevelChange(product: Product, value: string) {
    const par_level = Number(value)
    if (Number.isNaN(par_level)) return
    updateProduct(product.id, { par_level })
    setProducts(getProducts())
  }

  function removeProduct(id: string) {
    if (!confirm('Dit product verwijderen?')) return
    deleteProduct(id)
    setProducts(getProducts())
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Producten</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Stel per product de streefvoorraad in — dat is de hoeveelheid die er altijd zou moeten
          zijn na het bestellen.
        </p>
      </div>

      <form onSubmit={handleAdd} className="grid grid-cols-2 gap-2 rounded-xl border border-neutral-200 bg-white p-4 sm:grid-cols-4">
        <input
          required
          placeholder="Naam"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="col-span-2 rounded-lg border border-neutral-300 px-3 py-2 text-sm sm:col-span-1"
        />
        <input
          placeholder="Categorie"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Eenheid (kg, stuks...)"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />
        <input
          required
          type="number"
          step="any"
          placeholder="Streefvoorraad"
          value={parLevel}
          onChange={(e) => setParLevel(e.target.value)}
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          className="col-span-2 rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white sm:col-span-4"
        >
          Product toevoegen
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {products.length === 0 ? (
        <p className="text-sm text-neutral-400">Nog geen producten toegevoegd.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-left text-neutral-500">
              <tr>
                <th className="px-4 py-2 font-medium">Product</th>
                <th className="px-4 py-2 font-medium">Categorie</th>
                <th className="px-4 py-2 font-medium">Eenheid</th>
                <th className="px-4 py-2 font-medium">Streefvoorraad</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-t border-neutral-100">
                  <td className="px-4 py-2">{p.name}</td>
                  <td className="px-4 py-2 text-neutral-500">{p.category || '—'}</td>
                  <td className="px-4 py-2 text-neutral-500">{p.unit}</td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      step="any"
                      defaultValue={p.par_level}
                      onBlur={(e) => handleParLevelChange(p, e.target.value)}
                      className="w-20 rounded-lg border border-neutral-300 px-2 py-1"
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removeProduct(p.id)}
                      className="text-neutral-400 hover:text-red-600"
                    >
                      Verwijderen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
