import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../context/ThemeContext.jsx'
import * as api from '../services/api.js'

const SCRIPT_SRC = 'https://accounts.google.com/gsi/client'
let scriptPromise = null

function loadScript() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = SCRIPT_SRC
      script.async = true
      script.onload = resolve
      script.onerror = () => {
        scriptPromise = null
        reject(new Error('Google sign-in could not be loaded.'))
      }
      document.head.appendChild(script)
    })
  }
  return scriptPromise
}

/**
 * "Continue with Google". Renders nothing unless the server has a Google
 * client ID. The ID token goes to the server, which verifies it.
 */
export default function GoogleButton({ onCredential, onError }) {
  const holder = useRef(null)
  const [clientId, setClientId] = useState(null)
  const { theme } = useTheme()
  const dark = document.documentElement.classList.contains('dark') || theme === 'dark'

  useEffect(() => {
    let active = true
    api.getPublicConfig().then((config) => active && setClientId(config?.google_client_id || null)).catch(() => {})
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!clientId || !holder.current) return undefined
    let active = true
    loadScript()
      .then(() => {
        if (!active || !holder.current) return
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => response?.credential && onCredential(response.credential),
          ux_mode: 'popup',
        })
        holder.current.innerHTML = ''
        window.google.accounts.id.renderButton(holder.current, {
          type: 'standard',
          theme: dark ? 'filled_black' : 'outline',
          size: 'large',
          shape: 'rectangular',
          text: 'continue_with',
          width: Math.min(holder.current.offsetWidth || 320, 400),
        })
      })
      .catch((error) => onError?.(error.message))
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId, dark])

  if (!clientId) return null

  return (
    <div>
      <div ref={holder} className="flex min-h-[44px] justify-center" />
      <div className="my-5 flex items-center gap-3 text-xs text-neutral-400">
        <span className="h-px flex-1 bg-neutral-200 dark:bg-white/10" />
        or
        <span className="h-px flex-1 bg-neutral-200 dark:bg-white/10" />
      </div>
    </div>
  )
}
