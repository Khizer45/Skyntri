import { NavLink } from 'react-router-dom'
import DashboardLayout from './DashboardLayout.jsx'

const tabs = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/doctors', label: 'Doctors' },
  { to: '/admin/appointments', label: 'Appointments' },
  { to: '/admin/products', label: 'Products' },
  { to: '/admin/orders', label: 'Orders' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/automation', label: 'Automation' },
  { to: '/admin/settings', label: 'Settings' },
]

export default function AdminLayout({ title, subtitle, children }) {
  return (
    <DashboardLayout title={title ? `Admin · ${title}` : 'Admin'} subtitle={subtitle} width="xl">
      <nav className="no-scrollbar -mx-1 mb-6 flex gap-1 overflow-x-auto border-b border-neutral-200 px-1 dark:border-white/10" aria-label="Admin sections">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'border-neutral-900 text-neutral-900 dark:border-white dark:text-white'
                  : 'border-transparent text-neutral-500 hover:text-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-200'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {children}
    </DashboardLayout>
  )
}
