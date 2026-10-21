import {
  LayoutDashboard,
  ScanFace,
  FlaskConical,
  TrendingUp,
  MessageCircle,
  History,
  FileText,
  User,
  Settings,
  LogOut,
  Moon,
  Sun,
  X,
  Sparkles,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/skin-analysis', label: 'Skin Analysis', icon: ScanFace },
  { to: '/ingredient-scanner', label: 'Ingredient Scanner', icon: FlaskConical },
  { to: '/progress-checker', label: 'Progress Checker', icon: TrendingUp },
  { to: '/assistant', label: 'AI Skin Assistant', icon: MessageCircle },
  { to: '/history', label: 'History', icon: History },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-neutral-200 bg-white transition-transform duration-200 dark:border-neutral-800 dark:bg-panel-dark lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Skyntri</span>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 lg:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-2">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                    : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-neutral-200 px-2.5 py-3 dark:border-neutral-800">
          <button
            onClick={toggleTheme}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>

          <div className="mt-2 flex items-center gap-2.5 rounded-lg px-3 py-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
              {(user?.fullName || 'S').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">{user?.fullName || 'Guest'}</p>
              <p className="truncate text-xs text-neutral-400">{user?.email}</p>
            </div>
          </div>

          <button
            onClick={logout}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>
    </>
  )
}
