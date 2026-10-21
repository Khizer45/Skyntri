import { Menu, Moon, Sparkles, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext.jsx'

export default function Navbar({ title, onMenuClick }) {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-neutral-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-neutral-800 dark:bg-surface-dark/90 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2 lg:hidden">
          <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        </div>
        <h1 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">{title}</h1>
      </div>
      <button
        onClick={toggleTheme}
        className="rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800 lg:hidden"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </header>
  )
}
