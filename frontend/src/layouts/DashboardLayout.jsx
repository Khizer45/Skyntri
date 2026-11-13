import { useState } from 'react'
import Navbar from '../components/Navbar.jsx'
import Sidebar from '../components/Sidebar.jsx'

/**
 * App shell: sidebar + top bar + content.
 *   width  "md" (reading width), "lg" (default) or "xl" (tables)
 *   fill   the content takes the full remaining height (chat)
 */
const WIDTHS = { md: 'max-w-3xl', lg: 'max-w-5xl', xl: 'max-w-6xl' }

export default function DashboardLayout({ title, subtitle, actions, width = 'lg', fill = false, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className={`flex min-w-0 flex-1 flex-col ${fill ? 'h-screen' : ''}`}>
        <Navbar title={title} subtitle={subtitle} actions={actions} onMenuClick={() => setSidebarOpen(true)} />
        {fill ? (
          <main className="flex min-h-0 flex-1 flex-col">{children}</main>
        ) : (
          <main className={`mx-auto w-full flex-1 px-4 py-6 sm:px-6 sm:py-8 ${WIDTHS[width] || WIDTHS.lg}`}>{children}</main>
        )}
      </div>
    </div>
  )
}
