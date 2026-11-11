import { Moon, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext.jsx'

export default function AuthLayout({ title, subtitle, children }) {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex h-14 items-center justify-between px-5 sm:px-8">
        <Link to="/" className="text-lg font-semibold tracking-tight text-neutral-900 dark:text-white">
          Skyntri
        </Link>
        <button
          onClick={toggleTheme}
          className="rounded-md p-2 text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm">
          <div className="mb-7 text-center">
            <h1 className="text-2xl font-semibold text-neutral-900 dark:text-white">{title}</h1>
            {subtitle && <p className="muted mt-2 text-sm">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
