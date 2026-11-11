import { ArrowRight, CalendarDays, MessageCircle, ScanFace, Stethoscope } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Card from '../components/Card.jsx'
import HistoryItem from '../components/HistoryItem.jsx'
import Markdown from '../components/Markdown.jsx'
import { Section, StatusBadge, dateOnly, dateTime } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const actions = [
  { to: '/skin-analysis', label: 'Analyse my skin', desc: 'Take or upload a photo', icon: ScanFace },
  { to: '/assistant', label: 'Ask the assistant', desc: 'Routines, ingredients, questions', icon: MessageCircle },
  { to: '/doctors', label: 'See a dermatologist', desc: 'Book an online or clinic visit', icon: Stethoscope },
]

export default function Dashboard() {
  const { user } = useAuth()
  const [history, setHistory] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [posts, setPosts] = useState([])

  useEffect(() => {
    api.getHistory().then(setHistory).catch(() => setHistory({ analyses: [], scans: [], progress: [], reports: [] }))
    api.listMyAppointments().then(setAppointments).catch(() => {})
    api.getPosts(2).then(setPosts).catch(() => {})
  }, [])

  const next = appointments
    .filter((a) => ['requested', 'confirmed'].includes(a.status) && new Date(a.ends_at) > new Date())
    .sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at))[0]

  const recent = history
    ? [...history.analyses, ...history.scans, ...history.progress, ...history.reports]
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .slice(0, 4)
    : []

  return (
    <DashboardLayout title="Home">
      <h2 className="text-2xl font-semibold text-neutral-900 dark:text-white">
        Hello{user?.fullName ? `, ${user.fullName.split(' ')[0]}` : ''}
      </h2>
      <p className="muted mt-1 text-sm">What would you like to do today?</p>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {actions.map(({ to, label, desc, icon: Icon }) => (
          <Link key={to} to={to} className="group">
            <Card className="h-full p-4 transition-colors group-hover:border-neutral-400 dark:group-hover:border-white/30">
              <Icon className="h-5 w-5 text-brand-600 dark:text-brand-300" strokeWidth={1.75} />
              <p className="mt-3 text-sm font-medium text-neutral-900 dark:text-white">{label}</p>
              <p className="muted mt-0.5 text-xs">{desc}</p>
            </Card>
          </Link>
        ))}
      </div>

      {next && (
        <Section title="Next appointment" className="mt-8">
          <Link to={`/appointments/${next.id}`}>
            <Card className="flex items-center gap-3 p-4 hover:border-neutral-400 dark:hover:border-white/30">
              <CalendarDays className="h-5 w-5 shrink-0 text-neutral-400" strokeWidth={1.75} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">{next.doctor_name}</p>
                <p className="muted text-xs">{dateTime(next.starts_at)}</p>
              </div>
              <StatusBadge status={next.status} />
              <ArrowRight className="h-4 w-4 text-neutral-400" />
            </Card>
          </Link>
        </Section>
      )}

      {posts.length > 0 && (
        <Section title="From the clinic" className="mt-8">
          <div className="space-y-3">
            {posts.map((post) => (
              <Card key={post.id} className="p-4">
                <p className="text-sm font-semibold text-neutral-900 dark:text-white">{post.title}</p>
                <p className="muted mb-2 text-xs">{dateOnly(post.published_at)}</p>
                <Markdown className="!text-sm !leading-6">{post.body}</Markdown>
              </Card>
            ))}
          </div>
        </Section>
      )}

      <Section
        title="Recent activity"
        className="mt-8"
        action={recent.length > 0 && <Link to="/history" className="link text-sm">View all</Link>}
      >
        {!history ? (
          <p className="muted text-sm">Loading…</p>
        ) : recent.length === 0 ? (
          <p className="muted text-sm">Nothing yet. Your analyses, scans and reports will appear here.</p>
        ) : (
          <Card>
            {recent.map((item) => (
              <HistoryItem key={item.id} {...item} onView={() => {}} />
            ))}
          </Card>
        )}
      </Section>
    </DashboardLayout>
  )
}
