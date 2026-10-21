import { Sparkles } from 'lucide-react'
import { useTheme } from '../context/ThemeContext.jsx'
import { Moon, Sun } from 'lucide-react'

export default function AuthLayout({ title, subtitle, children }) {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="flex min-h-screen flex-col bg-surface-light dark:bg-surface-dark">
      <div className="flex items-center justify-between px-5 py-4 sm:px-8">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Skyntri</span>
        </div>
        <button
          onClick={toggleTheme}
          className="rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm">
          <div className="mb-6 text-center">
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{title}</h1>
            {subtitle && <p className="mt-1.5 text-sm text-neutral-500 dark:text-neutral-400">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
