import {
  ScanFace,
  FlaskConical,
  TrendingUp,
  MessageCircle,
  ArrowUpRight,
  Activity,
  ClipboardList,
  ShoppingBag,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Card from '../components/Card.jsx'
import HistoryItem from '../components/HistoryItem.jsx'
import { SkeletonCard } from '../components/LoadingState.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

const quickActions = [
  { to: '/skin-analysis', label: 'Analyze Skin', icon: ScanFace, desc: 'Upload a photo for AI classification' },
  { to: '/ingredient-scanner', label: 'Scan Ingredients', icon: FlaskConical, desc: 'Check a product label for safety' },
  { to: '/progress-checker', label: 'Check Progress', icon: TrendingUp, desc: 'Compare before & after images' },
  { to: '/assistant', label: 'Ask AI Assistant', icon: MessageCircle, desc: 'Get personalized skincare guidance' },
]

export default function Dashboard() {
  const { user } = useAuth()
  const [history, setHistory] = useState(null)

  useEffect(() => {
    api.getHistory().then(setHistory)
  }, [])

  const recentAnalyses = history?.analyses?.slice(0, 2) || []
  const allRecent = history
    ? [...history.analyses, ...history.scans, ...history.progress, ...history.reports]
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .slice(0, 4)
    : []

  return (
    <DashboardLayout title="Dashboard">
      <section className="relative overflow-hidden rounded-3xl bg-hero-gradient p-6 text-white shadow-glow sm:p-8">
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-20 right-24 h-48 w-48 rounded-full bg-accent-400/20 blur-2xl" />
        <div className="relative max-w-xl">
          <p className="text-sm font-medium text-white/80">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
          <h2 className="mt-1 font-display text-3xl font-bold">
            Welcome back, {user?.fullName?.split(' ')[0] || 'there'}
          </h2>
          <p className="mt-2 text-sm text-white/85">
            Take a clear selfie in natural light to see your visible skin concerns, then find affordable products with the right ingredients.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Link to="/skin-analysis" className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-brand-800 shadow hover:bg-brand-50">
              <ScanFace className="h-4 w-4" /> Analyze my skin
            </Link>
            <Link to="/shop" className="inline-flex items-center gap-2 rounded-xl bg-white/15 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/30 hover:bg-white/25">
              <ShoppingBag className="h-4 w-4" /> Shop by ingredient
            </Link>
          </div>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {quickActions.map(({ to, label, icon: Icon, desc }) => (
          <Link key={to} to={to}>
            <Card className="group h-full p-5 transition-all hover:-translate-y-0.5 hover:shadow-card-hover">
              <div className="flex items-start justify-between">
                <div className="rounded-xl bg-brand-gradient p-2.5 shadow-glow">
                  <Icon className="h-4 w-4 text-white" />
                </div>
                <ArrowUpRight className="h-4 w-4 text-neutral-300 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-brand-500" />
              </div>
              <p className="mt-3 text-sm font-medium text-neutral-800 dark:text-neutral-100">{label}</p>
              <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{desc}</p>
            </Card>
          </Link>
        ))}
      </section>

      <section className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-neutral-400">
            <ClipboardList className="h-4 w-4" />
            <p className="text-xs font-medium uppercase tracking-wide">Total analyses</p>
          </div>
          <p className="mt-2 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
            {history ? history.analyses.length + history.scans.length + history.progress.length : '—'}
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-neutral-400">
            <Activity className="h-4 w-4" />
            <p className="text-xs font-medium uppercase tracking-wide">Recent condition</p>
          </div>
          <p className="mt-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            {recentAnalyses[0]?.result || 'No analyses yet'}
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-neutral-400">
            <TrendingUp className="h-4 w-4" />
            <p className="text-xs font-medium uppercase tracking-wide">Progress status</p>
          </div>
          <p className="mt-2 text-lg font-semibold text-brand-600 dark:text-brand-400">
            {history?.progress?.[0]?.result || 'Not tracked yet'}
          </p>
        </Card>
      </section>

      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Recent activity</h3>
          <Link to="/history" className="text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400">
            View all
          </Link>
        </div>
        {!history ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : allRecent.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No activity yet"
            description="Run your first skin analysis to see it appear here."
          />
        ) : (
          <Card>
            {allRecent.map((item) => (
              <HistoryItem key={item.id} {...item} onView={() => {}} />
            ))}
          </Card>
        )}
      </section>
    </DashboardLayout>
  )
}
