import { useEffect, useState } from 'react'

// Tiny event bus so the sidebar/top bar cart badge updates after any cart change.
const EVENT = 'skyntri:cart'
let lastCount = 0

export function publishCartCount(count) {
  lastCount = Number(count) || 0
  window.dispatchEvent(new CustomEvent(EVENT, { detail: lastCount }))
}

export function useCartCount() {
  const [count, setCount] = useState(lastCount)
  useEffect(() => {
    const handler = (e) => setCount(e.detail)
    window.addEventListener(EVENT, handler)
    return () => window.removeEventListener(EVENT, handler)
  }, [])
  return count
}
