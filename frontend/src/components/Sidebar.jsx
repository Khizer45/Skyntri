import {
  CalendarDays,
  FileText,
  FlaskConical,
  History,
  Home,
  LogOut,
  MessageCircle,
  Moon,
  Package,
  ScanFace,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Stethoscope,
  Sun,
  TrendingUp,
  UserRound,
  X,
} from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'

const groups = [
  {
    links: [
      { to: '/dashboard', label: 'Home', icon: Home },
      { to: '/skin-analysis', label: 'Skin analysis', icon: ScanFace },
      { to: '/assistant', label: 'Assistant', icon: MessageCircle },
      { to: '/doctors', label: 'Doctors', icon: Stethoscope },
      { to: '/appointments', label: 'Appointments', icon: CalendarDays },
    ],
  },
  {
    title: 'Tools',
    links: [
      { to: '/ingredient-scanner', label: 'Ingredient scanner', icon: FlaskConical },
      { to: '/progress-checker', label: 'Progress', icon: TrendingUp },
      { to: '/shop', label: 'Shop', icon: ShoppingBag },
      { to: '/orders', label: 'Orders', icon: Package },
    ],
  },
  {
    title: 'Records',
    links: [
      { to: '/history', label: 'History', icon: History },
      { to: '/reports', label: 'Reports', icon: FileText },
    ],
  },
]

function NavItem({ to, label, icon: Icon, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
          isActive
            ? 'bg-neutral-900/[0.07] font-medium text-neutral-900 dark:bg-white/10 dark:text-white'
            : 'text-neutral-600 hover:bg-neutral-900/[0.04] hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-white/5 dark:hover:text-neutral-100'
        }`
      }
    >
      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
      {label}
    </NavLink>
  )
}

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const staff = []
  if (user?.role === 'doctor') staff.push({ to: '/doctor', label: 'Doctor portal', icon: UserRound })
  if (user?.role === 'admin') staff.push({ to: '/admin', label: 'Admin', icon: ShieldCheck })
  const all = staff.length ? [{ title: 'Clinic staff', links: staff }, ...groups] : groups

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 flex-col border-r border-neutral-200 bg-sidebar-light transition-transform duration-200 dark:border-white/10 dark:bg-sidebar-dark lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-14 items-center justify-between px-4">
          <Link to="/dashboard" onClick={onClose} className="text-lg font-semibold tracking-tight text-neutral-900 dark:text-white">
            Skyntri
          </Link>
          <button onClick={onClose} className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-900/5 dark:hover:bg-white/10 lg:hidden" aria-label="Close menu">
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="thin-scrollbar min-h-0 flex-1 space-y-5 overflow-y-auto px-2.5 pb-4 pt-1">
          {all.map((group, index) => (
            <div key={group.title || index}>
              {group.title && (
                <p className="mb-1 px-2.5 text-xs font-medium text-neutral-400 dark:text-neutral-500">{group.title}</p>
              )}
              <div className="space-y-0.5">
                {group.links.map((link) => (
                  <NavItem key={link.to} {...link} onClick={onClose} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-neutral-200 p-2.5 dark:border-white/10">
          <Link
            to="/settings"
            onClick={onClose}
            className="flex items-center gap-2.5 rounded-lg px-2 py-2 hover:bg-neutral-900/[0.04] dark:hover:bg-white/5"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-xs font-semibold text-white dark:bg-white dark:text-neutral-900">
              {(user?.fullName || 'S').charAt(0).toUpperCase()}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-neutral-900 dark:text-white">{user?.fullName || 'Guest'}</span>
              <span className="block truncate text-xs text-neutral-500 dark:text-neutral-400">{user?.email}</span>
            </span>
            <Settings className="h-4 w-4 shrink-0 text-neutral-400" strokeWidth={1.75} />
          </Link>
          <div className="mt-1 grid grid-cols-2 gap-1">
            <button
              onClick={toggleTheme}
              className="flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-neutral-600 hover:bg-neutral-900/[0.04] dark:text-neutral-400 dark:hover:bg-white/5"
            >
              {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
            <button
              onClick={logout}
              className="flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-neutral-600 hover:bg-neutral-900/[0.04] dark:text-neutral-400 dark:hover:bg-white/5"
            >
              <LogOut className="h-3.5 w-3.5" /> Log out
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
