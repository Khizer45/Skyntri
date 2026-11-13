import { Menu, ShoppingCart } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import * as api from '../services/api.js'
import { useCartCount } from '../services/cartEvents.js'

export default function Navbar({ title, subtitle, onMenuClick, actions }) {
  const { user } = useAuth()
  const cartCount = useCartCount()

  useEffect(() => {
    if (user) api.getCart().catch(() => {})
  }, [user])

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-neutral-200 bg-surface-light/90 px-4 backdrop-blur dark:border-white/10 dark:bg-surface-dark/90 sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button
          onClick={onMenuClick}
          className="-ml-1.5 rounded-md p-1.5 text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-neutral-900 dark:text-white">{title}</h1>
          {subtitle && <p className="muted hidden truncate text-xs sm:block">{subtitle}</p>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {actions}
        <Link
          to="/cart"
          className="relative rounded-md p-2 text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10"
          aria-label={cartCount > 0 ? `Cart, ${cartCount} items` : 'Cart'}
        >
          <ShoppingCart className="h-[18px] w-[18px]" strokeWidth={1.75} />
          {cartCount > 0 && (
            <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent-500 px-1 text-[10px] font-semibold text-white">
              {cartCount}
            </span>
          )}
        </Link>
      </div>
    </header>
  )
}
