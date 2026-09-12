import { useState, type FormEvent } from 'react'
import { supabase } from '../lib/supabase'

export function Login() {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const { error } =
      mode === 'signin'
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password })

    setSubmitting(false)
    if (error) setError(error.message)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-neutral-900">
          {mode === 'signin' ? 'Inloggen' : 'Account aanmaken'}
        </h1>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <input
            type="email"
            required
            placeholder="E-mailadres"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
          <input
            type="password"
            required
            minLength={6}
            placeholder="Wachtwoord"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-neutral-900 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {mode === 'signin' ? 'Inloggen' : 'Account aanmaken'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
          className="mt-4 text-sm text-neutral-500 underline"
        >
          {mode === 'signin' ? 'Nog geen account? Registreren' : 'Al een account? Inloggen'}
        </button>
      </div>
    </div>
  )
}
