import { useEffect, useState, type FormEvent } from 'react'
import { getClaudeSample, type SampleFn } from '../lib/claudeSample'
import { addWasteLog, getProducts, getWasteLogs } from '../lib/localStore'
import { useName } from '../lib/useName'
import type { Product, WasteLog as WasteLogRow } from '../lib/types'

const REASONS = ['Over datum', 'Aangebrand/mislukt', 'Retour klant', 'Gevallen/gemorst', 'Anders']

interface ReviewRow {
  tempId: string
  product_id: string
  quantity: string
  reason: string
}

function matchProductId(products: Product[], name: string): string {
  const norm = (s: string) => s.toLowerCase().trim()
  const target = norm(name)
  return (
    products.find((p) => norm(p.name) === target)?.id ??
    products.find((p) => norm(p.name).includes(target) || target.includes(norm(p.name)))?.id ??
    products[0]?.id ??
    ''
  )
}

function extractErrorMessage(code: unknown): string {
  switch (code) {
    case 'not_granted':
      return 'Je hebt Claude geen toestemming gegeven in deze preview, dus de foto kon niet gelezen worden.'
    case 'image_rejected':
      return 'Deze foto kon niet gelezen worden. Probeer een scherpere foto (jpg/png).'
    case 'rate_limited':
      return 'Even te veel aanvragen achter elkaar. Probeer over een minuutje opnieuw.'
    case 'invalid_json':
      return 'Kon de foto niet goed omzetten naar een lijst. Probeer opnieuw of vul handmatig in.'
    default:
      return 'Er ging iets mis bij het lezen van de foto. Vul de derving voor nu handmatig in.'
  }
}

export function WasteLog() {
  const [products, setProducts] = useState<Product[]>([])
  const [recent, setRecent] = useState<WasteLogRow[]>([])
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState(REASONS[0])
  const [name, setName] = useName()
  const [error, setError] = useState<string | null>(null)

  const [sample, setSample] = useState<SampleFn | null>(null)
  const [photoStatus, setPhotoStatus] = useState<'checking' | 'no-sample' | 'no-images' | 'ready'>('checking')
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [reviewRows, setReviewRows] = useState<ReviewRow[] | null>(null)

  useEffect(() => {
    const loaded = getProducts()
    setProducts(loaded)
    setProductId((current) => current || loaded[0]?.id || '')
    setRecent(getWasteLogs().slice(0, 10))

    getClaudeSample().then((s) => {
      setSample(s)
      if (!s) return setPhotoStatus('no-sample')
      s.limits()
        .then((l) => setPhotoStatus(l.images ? 'ready' : 'no-images'))
        .catch(() => setPhotoStatus('no-images'))
    })
  }, [])

  function productFor(id: string) {
    return products.find((p) => p.id === id)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!productId) return setError('Kies een product.')
    if (!name.trim()) return setError('Vul in wie dit invoert.')
    const qty = Number(quantity)
    if (!qty || qty <= 0) return setError('Vul een geldige hoeveelheid in.')

    addWasteLog({ product_id: productId, quantity: qty, reason, logged_by: name.trim() })
    setQuantity('')
    setRecent(getWasteLogs().slice(0, 10))
  }

  async function handlePhoto(file: File) {
    if (!sample) return
    setExtracting(true)
    setExtractError(null)
    try {
      const productNames = products.map((p) => p.name)
      const prompt = `Dit is een foto van een handgeschreven of gedrukte dervingslijst uit een restaurant. Elke regel bevat meestal een productnaam en een hoeveelheid, soms een reden.

Bekende producten in het systeem: ${productNames.join(', ') || '(nog geen producten ingevoerd)'}

Geef ALLEEN een JSON array terug, geen andere tekst, met dit formaat:
[{"product": string, "quantity": number, "reason": string}]

Gebruik voor "product" zo veel mogelijk exact een van de bekende producten hierboven (kies de dichtstbijzijnde match als de foto een net iets andere naam gebruikt). Gebruik voor "reason" precies een van: ${REASONS.join(', ')} — kies "Anders" als niets past. Sla regels over die niet leesbaar zijn.`

      const rows = await sample.json<{ product: string; quantity: number; reason: string }[]>(prompt, {
        images: file,
        modelTier: 'default',
        cache: false,
      })

      const mapped: ReviewRow[] = (Array.isArray(rows) ? rows : [])
        .filter((r) => r && Number(r.quantity) > 0)
        .map((r) => ({
          tempId: crypto.randomUUID(),
          product_id: matchProductId(products, String(r.product ?? '')),
          quantity: String(r.quantity),
          reason: REASONS.includes(r.reason) ? r.reason : REASONS[REASONS.length - 1],
        }))

      if (mapped.length === 0) {
        setExtractError('Geen items herkend op de foto. Probeer een scherpere foto of vul handmatig in.')
      } else {
        setReviewRows(mapped)
      }
    } catch (e) {
      setExtractError(extractErrorMessage((e as { code?: string })?.code))
    } finally {
      setExtracting(false)
    }
  }

  function updateReviewRow(index: number, patch: Partial<ReviewRow>) {
    setReviewRows((prev) => prev && prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  function removeReviewRow(index: number) {
    setReviewRows((prev) => prev && prev.filter((_, i) => i !== index))
  }

  function saveReviewRows() {
    if (!reviewRows) return
    if (!name.trim()) return setExtractError('Vul bovenaan in wie dit invoert, voor je opslaat.')

    for (const row of reviewRows) {
      const qty = Number(row.quantity)
      if (!row.product_id || !qty || qty <= 0) continue
      addWasteLog({ product_id: row.product_id, quantity: qty, reason: row.reason, logged_by: name.trim() })
    }
    setReviewRows(null)
    setExtractError(null)
    setRecent(getWasteLogs().slice(0, 10))
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-neutral-900">Derving invoeren</h1>
        <p className="mt-1 text-sm text-neutral-500">Wat is er weggegooid, en waarom?</p>
      </div>

      <input
        placeholder="Wie ben jij?"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
      />

      {!reviewRows && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-4 text-center">
          {photoStatus === 'ready' ? (
            <>
              <label className="cursor-pointer text-sm font-medium text-neutral-700">
                {extracting ? 'Foto wordt gelezen...' : '📷 Foto van papieren dervingslijst uploaden'}
                <input
                  type="file"
                  accept="image/*"
                  hidden
                  disabled={extracting}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    e.target.value = ''
                    if (file) handlePhoto(file)
                  }}
                />
              </label>
              <p className="mt-1 text-xs text-neutral-400">
                De lijst wordt automatisch gelezen — je controleert 'm hieronder voor je opslaat.
              </p>
              {extractError && <p className="mt-2 text-sm text-red-600">{extractError}</p>}
            </>
          ) : (
            <p className="text-xs text-neutral-400">
              📷 Fotofunctie:{' '}
              {photoStatus === 'checking' && 'wordt gecontroleerd...'}
              {photoStatus === 'no-sample' && 'niet beschikbaar in deze weergave (sample-capability niet gevonden)'}
              {photoStatus === 'no-images' && 'wel beschikbaar, maar foto\'s uploaden wordt hier niet ondersteund'}
            </p>
          )}
        </div>
      )}

      {reviewRows && (
        <div className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
          <div>
            <h2 className="text-sm font-semibold text-neutral-900">Controleer wat herkend is</h2>
            <p className="text-xs text-neutral-500">Pas aan waar nodig en verwijder foute regels.</p>
          </div>
          <div className="space-y-2">
            {reviewRows.map((row, i) => (
              <div key={row.tempId} className="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-100 p-2">
                <select
                  value={row.product_id}
                  onChange={(e) => updateReviewRow(i, { product_id: e.target.value })}
                  className="min-w-32 flex-1 rounded-lg border border-neutral-300 px-2 py-1.5 text-sm"
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
                  value={row.quantity}
                  onChange={(e) => updateReviewRow(i, { quantity: e.target.value })}
                  className="w-20 rounded-lg border border-neutral-300 px-2 py-1.5 text-sm"
                />
                <select
                  value={row.reason}
                  onChange={(e) => updateReviewRow(i, { reason: e.target.value })}
                  className="rounded-lg border border-neutral-300 px-2 py-1.5 text-sm"
                >
                  {REASONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeReviewRow(i)}
                  className="text-xs text-neutral-400 hover:text-red-600"
                >
                  Verwijderen
                </button>
              </div>
            ))}
          </div>
          {extractError && <p className="text-sm text-red-600">{extractError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={saveReviewRows}
              disabled={reviewRows.length === 0}
              className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Alles opslaan ({reviewRows.length})
            </button>
            <button
              type="button"
              onClick={() => setReviewRows(null)}
              className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
            >
              Annuleren
            </button>
          </div>
        </div>
      )}

      {!reviewRows && (
        <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-neutral-200 bg-white p-4">
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
            disabled={products.length === 0}
            className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Invoeren
          </button>
          {products.length === 0 && (
            <p className="text-xs text-neutral-400">
              Nog geen producten. Voeg eerst producten toe via het tabblad "Producten".
            </p>
          )}
        </form>
      )}

      {recent.length > 0 && (
        <div>
          <h2 className="mb-2 text-sm font-semibold text-neutral-500">Laatst ingevoerd</h2>
          <div className="space-y-1">
            {recent.map((r) => {
              const product = productFor(r.product_id)
              return (
                <div
                  key={r.id}
                  className="flex justify-between rounded-lg border border-neutral-100 bg-white px-3 py-2 text-sm"
                >
                  <span>
                    {product?.name ?? 'Onbekend product'} — {r.quantity} {product?.unit} ({r.reason})
                  </span>
                  <span className="text-neutral-400">{r.logged_by}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
