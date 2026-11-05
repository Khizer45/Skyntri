import {
  Boxes,
  ClipboardList,
  FileText,
  FlaskConical,
  History,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  Moon,
  Package,
  ScanFace,
  Settings,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Sun,
  TrendingUp,
  User,
  Users,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { useCartCount } from '../services/cartEvents.js'

const sections = [
  {
    title: 'Skin care',
    links: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/skin-analysis', label: 'Skin Analysis', icon: ScanFace },
      { to: '/ingredient-scanner', label: 'Ingredient Scanner', icon: FlaskConical },
      { to: '/progress-checker', label: 'Progress Checker', icon: TrendingUp },
      { to: '/assistant', label: 'AI Skin Assistant', icon: MessageCircle },
    ],
  },
  {
    title: 'Shop',
    links: [
      { to: '/shop', label: 'Shop', icon: ShoppingBag },
      { to: '/cart', label: 'Cart', icon: ShoppingCart, badge: 'cart' },
      { to: '/orders', label: 'My Orders', icon: Package },
    ],
  },
  {
    title: 'Account',
    links: [
      { to: '/history', label: 'History', icon: History },
      { to: '/reports', label: 'Reports', icon: FileText },
      { to: '/profile', label: 'Profile', icon: User },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
]

const adminSection = {
  title: 'Admin panel',
  links: [
    { to: '/admin', label: 'Overview', icon: ShieldCheck, end: true },
    { to: '/admin/products', label: 'Products', icon: Boxes },
    { to: '/admin/orders', label: 'Orders & Payments', icon: ClipboardList },
    { to: '/admin/users', label: 'Users', icon: Users },
  ],
}

function NavItem({ to, label, icon: Icon, badge, end, onClick, cartCount }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `group relative flex items-center gap-2.5 rounded-xl px-3 py-1.5 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-brand-50 text-brand-800 dark:bg-brand-900/30 dark:text-brand-200'
            : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-white/5 dark:hover:text-neutral-100'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-brand-500" />}
          <Icon className={`h-4 w-4 ${isActive ? 'text-brand-600 dark:text-brand-300' : ''}`} />
          <span className="flex-1">{label}</span>
          {badge === 'cart' && cartCount > 0 && (
            <span className="badge bg-accent-500 text-white">{cartCount}</span>
          )}
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const cartCount = useCartCount()
  const isAdmin = user?.role === 'admin'
  // Admins see their panel first so it is never hidden below the fold.
  const all = isAdmin ? [adminSection, ...sections] : sections

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-neutral-200/80 bg-white/95 backdrop-blur transition-transform duration-200 dark:border-white/5 dark:bg-panel-dark/95 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient shadow-glow">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="block font-display text-lg font-bold leading-none text-neutral-900 dark:text-white">Skyntri</span>
              <span className="text-[11px] text-neutral-400">AI skin health</span>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 lg:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="thin-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto px-3 pb-4">
          {all.map((section) => (
            <div key={section.title}>
              <p
                className={`mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider ${
                  section === adminSection ? 'text-accent-600 dark:text-accent-400' : 'text-neutral-400'
                }`}
              >
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.links.map((link) => (
                  <NavItem key={link.to} {...link} onClick={onClose} cartCount={cartCount} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-neutral-200/80 p-3 dark:border-white/5">
          <div className="flex items-center gap-2.5 rounded-xl bg-neutral-50 px-3 py-2.5 dark:bg-white/5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-xs font-bold text-white">
              {(user?.fullName || 'S').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-1.5 truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">
                {user?.fullName || 'Guest'}
                {isAdmin && <span className="badge bg-accent-100 text-accent-700 dark:bg-accent-900/40 dark:text-accent-200">Admin</span>}
              </p>
              <p className="truncate text-xs text-neutral-400">{user?.email}</p>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-1">
            <button
              onClick={toggleTheme}
              className="flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-white/5"
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
            <button
              onClick={logout}
              className="flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              <LogOut className="h-4 w-4" /> Logout
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
