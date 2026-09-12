import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { supabase } from '../lib/supabase'

export function Onboarding() {
  const { refreshProfile } = useAuth()
  const [tab, setTab] = useState<'create' | 'join'>('create')
  const [name, setName] = useState('')
  const [restaurantName, setRestaurantName] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { error } = await supabase.rpc('create_restaurant', {
      restaurant_name: restaurantName,
      manager_name: name,
    })
    setSubmitting(false)
    if (error) return setError(error.message)
    await refreshProfile()
  }

  async function handleJoin(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { error } = await supabase.rpc('join_restaurant', {
      code: joinCode.trim(),
      staff_name: name,
    })
    setSubmitting(false)
    if (error) return setError(error.message)
    await refreshProfile()
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex gap-2 text-sm">
          <button
            type="button"
            onClick={() => setTab('create')}
            className={`flex-1 rounded-lg py-2 font-medium ${tab === 'create' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'}`}
          >
            Nieuwe zaak
          </button>
          <button
            type="button"
            onClick={() => setTab('join')}
            className={`flex-1 rounded-lg py-2 font-medium ${tab === 'join' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'}`}
          >
            Ik heb een code
          </button>
        </div>

        {tab === 'create' ? (
          <form onSubmit={handleCreate} className="space-y-3">
            <input
              required
              placeholder="Jouw naam"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <input
              required
              placeholder="Naam van de zaak"
              value={restaurantName}
              onChange={(e) => setRestaurantName(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Zaak starten
            </button>
          </form>
        ) : (
          <form onSubmit={handleJoin} className="space-y-3">
            <input
              required
              placeholder="Jouw naam"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <input
              required
              placeholder="Toegangscode van je manager"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Aansluiten
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
