import { ArrowDownUp, History as HistoryIcon, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import Card from '../components/Card.jsx'
import HistoryItem from '../components/HistoryItem.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

const tabs = [
  { key: 'analyses', label: 'Skin Analyses' },
  { key: 'scans', label: 'Ingredient Scans' },
  { key: 'progress', label: 'Progress Checks' },
  { key: 'reports', label: 'Reports' },
]

export default function History() {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('analyses')
  const [query, setQuery] = useState('')
  const [sortDesc, setSortDesc] = useState(true)

  useEffect(() => {
    api.getHistory().then(setData)
  }, [])

  const items = useMemo(() => {
    if (!data) return []
    let list = data[tab] || []
    if (query.trim()) {
      list = list.filter((i) => i.result.toLowerCase().includes(query.toLowerCase()))
    }
    list = [...list].sort((a, b) =>
      sortDesc ? new Date(b.date) - new Date(a.date) : new Date(a.date) - new Date(b.date)
    )
    return list
  }, [data, tab, query, sortDesc])

  return (
    <DashboardLayout title="History">
      <div className="mb-4 flex flex-wrap items-center gap-1.5 border-b border-neutral-200 dark:border-neutral-800">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search results…"
            className="w-full rounded-lg border border-neutral-300 bg-white py-2 pl-8 pr-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
          />
        </div>
        <button
          onClick={() => setSortDesc((s) => !s)}
          className="flex items-center gap-1.5 self-start rounded-lg border border-neutral-300 px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
        >
          <ArrowDownUp className="h-3.5 w-3.5" />
          {sortDesc ? 'Newest first' : 'Oldest first'}
        </button>
      </div>

      {!data ? (
        <Card className="p-5">
          <Spinner label="Loading history…" />
        </Card>
      ) : items.length === 0 ? (
        <EmptyState icon={HistoryIcon} title="Nothing here yet" description="Results will appear as you use Skyntri." />
      ) : (
        <Card>
          {items.map((item) => (
            <HistoryItem key={item.id} {...item} onView={() => {}} />
          ))}
        </Card>
      )}
    </DashboardLayout>
  )
}
