import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Alert, Empty, StatusBadge, Tabs, dateTime, label } from '../components/ui.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

export function AppointmentRow({ appointment, to, who }) {
  return (
    <Link to={to} className="flex items-center gap-3 px-4 py-3.5 hover:bg-neutral-900/[0.03] dark:hover:bg-white/5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">{who}</p>
        <p className="muted text-xs">{dateTime(appointment.starts_at)} · {label(appointment.mode)}</p>
      </div>
      {appointment.payment_status === 'unpaid' && ['requested', 'confirmed'].includes(appointment.status) && (
        <StatusBadge status="unpaid" />
      )}
      <StatusBadge status={appointment.status} />
    </Link>
  )
}

export default function Appointments() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('upcoming')

  useEffect(() => {
    api.listMyAppointments().then(setItems).catch((err) => setError(err.message))
  }, [])

  const now = new Date()
  const upcoming = (items || [])
    .filter((a) => ['requested', 'confirmed'].includes(a.status) && new Date(a.ends_at) > now)
    .sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at))
  const past = (items || []).filter((a) => !upcoming.includes(a))
  const shown = tab === 'upcoming' ? upcoming : past

  return (
    <DashboardLayout
      title="Appointments"
      width="md"
      actions={<Link to="/doctors"><Button size="sm">Book</Button></Link>}
    >
      {error && <Alert className="mb-4">{error}</Alert>}
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[{ id: 'upcoming', label: 'Upcoming' }, { id: 'past', label: 'Past' }]}
      />
      {items === null && !error ? (
        <p className="muted text-sm">Loading…</p>
      ) : shown.length === 0 ? (
        <Empty title={tab === 'upcoming' ? 'No upcoming appointments' : 'No past appointments'}>
          {tab === 'upcoming' && <Link to="/doctors" className="link">Find a dermatologist</Link>}
        </Empty>
      ) : (
        <Card className="divide-soft overflow-hidden">
          {shown.map((a) => (
            <AppointmentRow key={a.id} appointment={a} to={`/appointments/${a.id}`} who={`${a.doctor_name} · ${a.doctor_specialty}`} />
          ))}
        </Card>
      )}
    </DashboardLayout>
  )
}
