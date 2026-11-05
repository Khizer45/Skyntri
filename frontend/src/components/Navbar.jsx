import { Menu, Moon, ShoppingCart, Sun } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import * as api from '../services/api.js'
import { useCartCount } from '../services/cartEvents.js'

export default function Navbar({ title, subtitle, onMenuClick }) {
  const { theme, toggleTheme } = useTheme()
  const { user } = useAuth()
  const cartCount = useCartCount()

  useEffect(() => {
    if (user) api.getCart().catch(() => {})
  }, [user])

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-neutral-200/70 bg-white/75 px-4 py-3 backdrop-blur-xl dark:border-white/5 dark:bg-surface-dark/75 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-1.5 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-lg font-bold text-neutral-900 dark:text-white">{title}</h1>
          {subtitle && <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <Link
          to="/cart"
          className="relative rounded-xl p-2 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-white/5"
          aria-label="Cart"
        >
          <ShoppingCart className="h-5 w-5" />
          {cartCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent-500 px-1 text-[10px] font-bold text-white">
              {cartCount}
            </span>
          )}
        </Link>
        <button
          onClick={toggleTheme}
          className="rounded-xl p-2 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-white/5"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
        <Link
          to="/profile"
          className="ml-1 flex h-9 w-9 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white shadow-glow"
          aria-label="Profile"
        >
          {(user?.fullName || 'S').charAt(0).toUpperCase()}
        </Link>
      </div>
    </header>
  )
}
