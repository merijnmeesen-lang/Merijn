import { useState } from 'react'

const STORAGE_KEY = 'voorraad-app:name'

export function useName() {
  const [name, setName] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) ?? ''
    } catch {
      return ''
    }
  })

  function updateName(value: string) {
    setName(value)
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // localStorage unavailable (private browsing) — name just won't persist.
    }
  }

  return [name, updateName] as const
}
