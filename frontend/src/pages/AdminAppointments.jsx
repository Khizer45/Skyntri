import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Alert, Empty, StatusBadge, dateTime, label, money } from '../components/ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

const FILTERS = ['', 'requested', 'confirmed', 'completed', 'cancelled', 'no_show']
const NEXT_PAYMENT = { unpaid: ['paid', 'Mark paid'], paid: ['refunded', 'Mark refunded'], refund_due: ['refunded', 'Mark refunded'] }

export default function AdminAppointments() {
  const { showToast } = useToast()
  const [status, setStatus] = useState('')
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setItems(null)
    api.adminListAppointments(status).then(setItems).catch((err) => setError(err.message))
  }, [status])

  const setPayment = async (appointment, next) => {
    try {
      const updated = await api.adminSetAppointmentPayment(appointment.id, next)
      setItems((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <AdminLayout title="Appointments">
      <div className="mb-4 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f || 'all'}
            onClick={() => setStatus(f)}
            className={`rounded-full border px-3 py-1 text-xs ${status === f ? 'border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900' : 'border-neutral-300 text-neutral-700 dark:border-white/15 dark:text-neutral-300'}`}
          >
            {f ? label(f) : 'All'}
          </button>
        ))}
      </div>
      {error && <Alert className="mb-4">{error}</Alert>}
      {items === null && !error ? (
        <p className="muted text-sm">Loading…</p>
      ) : items?.length === 0 ? (
        <Empty title="No appointments" />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs text-neutral-500 dark:border-white/10">
              <tr>{['When', 'Patient', 'Doctor', 'Status', 'Fee', 'Payment', ''].map((h) => <th key={h} className="px-4 py-2.5 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {(items || []).map((a) => (
                <tr key={a.id} className="border-b border-neutral-100 last:border-0 dark:border-white/5">
                  <td className="whitespace-nowrap px-4 py-3">{dateTime(a.starts_at)}</td>
                  <td className="px-4 py-3">{a.patient_name}<span className="muted block text-xs">{a.patient_email}</span></td>
                  <td className="px-4 py-3">{a.doctor_name}</td>
                  <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  <td className="whitespace-nowrap px-4 py-3">{a.fee > 0 ? money(a.fee, a.currency) : 'Free'}</td>
                  <td className="px-4 py-3"><StatusBadge status={a.payment_status} />{a.payment_method && <span className="muted ml-1 text-xs">{label(a.payment_method)}</span>}</td>
                  <td className="px-4 py-3 text-right">
                    {NEXT_PAYMENT[a.payment_status] && (
                      <Button size="sm" variant="outline" onClick={() => setPayment(a, NEXT_PAYMENT[a.payment_status][0])}>{NEXT_PAYMENT[a.payment_status][1]}</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <p className="muted mt-3 text-xs">Reasons for a visit, messages and doctors' notes are not shown here. Refunds are made in the Stripe or PayPal dashboard, then marked here.</p>
    </AdminLayout>
  )
}
