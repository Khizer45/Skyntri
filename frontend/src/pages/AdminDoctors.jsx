import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Alert, Empty, StatusBadge, dateOnly, money } from '../components/ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

const ACTIONS = {
  pending: [{ status: 'approved', label: 'Approve' }, { status: 'rejected', label: 'Reject', variant: 'outline' }],
  approved: [{ status: 'suspended', label: 'Suspend', variant: 'outline' }],
  suspended: [{ status: 'approved', label: 'Reactivate' }],
  rejected: [{ status: 'approved', label: 'Approve' }],
}

export default function AdminDoctors() {
  const { showToast } = useToast()
  const [doctors, setDoctors] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    api.adminListDoctors().then(setDoctors).catch((err) => setError(err.message))
  }, [])

  const review = async (doctor, status) => {
    if (status === 'approved' && !window.confirm(`Approve ${doctor.name}? Check licence ${doctor.license_number} with the medical council first.`)) return
    setBusy(doctor.id)
    try {
      const updated = await api.adminReviewDoctor(doctor.id, status)
      setDoctors((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
      showToast(`Doctor ${status}.`, 'success')
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  return (
    <AdminLayout title="Doctors">
      {error && <Alert className="mb-4">{error}</Alert>}
      {doctors === null && !error ? (
        <p className="muted text-sm">Loading…</p>
      ) : doctors?.length === 0 ? (
        <Empty title="No doctor applications yet">A dermatologist signs up, then applies under Settings → “Are you a dermatologist?”.</Empty>
      ) : (
        <div className="space-y-3">
          {(doctors || []).map((doctor) => (
            <Card key={doctor.id} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-900 dark:text-white">{doctor.name} <StatusBadge status={doctor.status} /></p>
                  <p className="muted text-sm">{doctor.specialty} · {doctor.qualifications}</p>
                  <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">Licence: <span className="font-medium">{doctor.license_number}</span></p>
                  <p className="muted mt-1 text-xs">
                    {doctor.email}{doctor.phone ? ` · ${doctor.phone}` : ''} · applied {dateOnly(doctor.created_at)} · fee {money(doctor.consultation_fee, doctor.currency)} · {doctor.appointments} appointment(s)
                  </p>
                </div>
                <div className="flex gap-2">
                  {(ACTIONS[doctor.status] || []).map((action) => (
                    <Button key={action.status} size="sm" variant={action.variant || 'primary'} loading={busy === doctor.id} onClick={() => review(doctor, action.status)}>
                      {action.label}
                    </Button>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </AdminLayout>
  )
}
