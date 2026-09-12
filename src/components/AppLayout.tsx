import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { supabase } from '../lib/supabase'

const staffLinks = [
  { to: '/', label: 'Voorraad' },
  { to: '/derving', label: 'Derving' },
]

const managerLinks = [
  { to: '/manager', label: 'Overzicht' },
  { to: '/manager/producten', label: 'Producten' },
  { to: '/', label: 'Voorraad' },
  { to: '/derving', label: 'Derving' },
]

export function AppLayout({ children }: { children: ReactNode }) {
  const { profile } = useAuth()
  const links = profile?.role === 'manager' ? managerLinks : staffLinks

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <nav className="flex gap-1">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isActive ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <button
            type="button"
            onClick={() => supabase.auth.signOut()}
            className="text-sm text-neutral-500 underline"
          >
            Uitloggen
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6">{children}</main>
    </div>
  )
}
