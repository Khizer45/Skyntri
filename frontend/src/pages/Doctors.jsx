import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Modal from '../components/Modal.jsx'
import { Alert, Empty, Field, money } from '../components/ui.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const MODES = [
  { id: 'video', label: 'Video call' },
  { id: 'chat', label: 'Chat' },
  { id: 'in_person', label: 'At the clinic' },
]

function isoDay(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function nextDays(count) {
  const today = new Date()
  return Array.from({ length: count }, (_, i) => new Date(today.getFullYear(), today.getMonth(), today.getDate() + i))
}

function BookingDialog({ doctor, timezone, onClose }) {
  const navigate = useNavigate()
  const days = useMemo(() => nextDays(14), [])
  const [day, setDay] = useState(isoDay(days[0]))
  const [slots, setSlots] = useState(null)
  const [slot, setSlot] = useState('')
  const [mode, setMode] = useState('video')
  const [reason, setReason] = useState('')
  const [analyses, setAnalyses] = useState([])
  const [analysisId, setAnalysisId] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const skipped = useRef(false)

  useEffect(() => {
    api.getHistory().then((h) => setAnalyses((h?.analyses || []).slice(0, 10))).catch(() => {})
  }, [])

  useEffect(() => {
    let active = true
    setSlots(null)
    setSlot('')
    api.getDoctorSlots(doctor.id, day)
      .then((data) => {
        if (!active) return
        // Today is often over already: start on the first day with a free time.
        const index = days.findIndex((d) => isoDay(d) === day)
        if (!skipped.current && index < 6 && !data.some((s) => s.available)) {
          setDay(isoDay(days[index + 1]))
          return
        }
        skipped.current = true
        setSlots(data)
      })
      .catch((err) => active && setError(err.message))
    return () => {
      active = false
    }
  }, [doctor.id, day, days])

  const time = (value) => new Date(value).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', timeZone: timezone })
  const free = (slots || []).filter((s) => s.available)

  const book = async (e) => {
    e.preventDefault()
    if (!slot) return setError('Please choose a time.')
    setSaving(true)
    setError('')
    try {
      const appointment = await api.bookAppointment({
        doctor_id: doctor.id, starts_at: slot, mode, reason, analysis_id: analysisId || null,
      })
      navigate(`/appointments/${appointment.id}`)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
    return undefined
  }

  return (
    <Modal open onClose={onClose} title={`Book ${doctor.name}`}>
      <form onSubmit={book} className="space-y-4">
        <div>
          <span className="label">Day</span>
          <div className="no-scrollbar flex gap-1.5 overflow-x-auto pb-1">
            {days.map((date) => {
              const value = isoDay(date)
              return (
                <button
                  type="button"
                  key={value}
                  onClick={() => {
                    skipped.current = true
                    setDay(value)
                  }}
                  className={`shrink-0 rounded-lg border px-3 py-1.5 text-center text-xs ${
                    day === value
                      ? 'border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900'
                      : 'border-neutral-300 text-neutral-700 dark:border-white/15 dark:text-neutral-300'
                  }`}
                >
                  <span className="block">{date.toLocaleDateString(undefined, { weekday: 'short' })}</span>
                  <span className="block font-semibold">{date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <span className="label">Time <span className="muted font-normal">({timezone})</span></span>
          {slots === null ? (
            <p className="muted text-sm">Loading times…</p>
          ) : free.length === 0 ? (
            <p className="muted text-sm">No free time on this day. Please try another day.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {free.map((s) => (
                <button
                  type="button"
                  key={s.starts_at}
                  onClick={() => setSlot(s.starts_at)}
                  className={`rounded-lg border px-3 py-1.5 text-sm ${
                    slot === s.starts_at
                      ? 'border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900'
                      : 'border-neutral-300 text-neutral-700 hover:border-neutral-500 dark:border-white/15 dark:text-neutral-300'
                  }`}
                >
                  {time(s.starts_at)}
                </button>
              ))}
            </div>
          )}
        </div>

        <Field label="Type of visit">
          <select className="field" value={mode} onChange={(e) => setMode(e.target.value)}>
            {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
        </Field>

        <Field label="What would you like help with?" hint="Only you and the doctor can read this.">
          <textarea className="field" rows={3} required minLength={5} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>

        {analyses.length > 0 && (
          <Field label="Share a skin analysis with the doctor (optional)" hint="The doctor will see the photo and the result of that analysis.">
            <select className="field" value={analysisId} onChange={(e) => setAnalysisId(e.target.value)}>
              <option value="">Do not share</option>
              {analyses.map((a) => (
                <option key={a.id} value={a.id}>{new Date(a.date).toLocaleDateString()} · {a.result}</option>
              ))}
            </select>
          </Field>
        )}

        {error && <Alert>{error}</Alert>}

        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-neutral-700 dark:text-neutral-300">
            Fee: <span className="font-semibold">{doctor.consultation_fee > 0 ? money(doctor.consultation_fee, doctor.currency) : 'Free'}</span>
          </p>
          <Button type="submit" loading={saving} disabled={!slot}>Request appointment</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function Doctors() {
  const [doctors, setDoctors] = useState(null)
  const [timezone, setTimezone] = useState(undefined)
  const [error, setError] = useState('')
  const [booking, setBooking] = useState(null)

  useEffect(() => {
    api.listDoctors().then(setDoctors).catch((err) => setError(err.message))
    api.getPublicConfig().then((c) => setTimezone(c?.timezone)).catch(() => {})
  }, [])

  return (
    <DashboardLayout title="Doctors" subtitle="Book a dermatologist">
      {error && <Alert className="mb-4">{error}</Alert>}
      {doctors === null && !error ? (
        <p className="muted text-sm">Loading doctors…</p>
      ) : doctors?.length === 0 ? (
        <Empty title="No doctors are available yet">The clinic is still adding its dermatologists. Please check again soon.</Empty>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {(doctors || []).map((doctor) => (
            <Card key={doctor.id} className="flex flex-col p-5">
              <div className="flex items-start gap-3">
                {doctor.avatarUrl ? (
                  <img src={doctor.avatarUrl} alt="" className="h-12 w-12 rounded-full object-cover" />
                ) : (
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-base font-semibold text-white dark:bg-white dark:text-neutral-900">
                    {doctor.name.replace(/^Dr\.?\s*/i, '').charAt(0).toUpperCase()}
                  </span>
                )}
                <div className="min-w-0">
                  <p className="text-base font-semibold text-neutral-900 dark:text-white">{doctor.name}</p>
                  <p className="muted text-sm">{doctor.specialty} · {doctor.qualifications}</p>
                </div>
              </div>
              {doctor.bio && <p className="mt-3 text-sm text-neutral-700 dark:text-neutral-300">{doctor.bio}</p>}
              <p className="muted mt-3 text-xs">
                {doctor.years_experience > 0 && `${doctor.years_experience} years of experience`}
                {doctor.years_experience > 0 && doctor.languages && ' · '}
                {doctor.languages}
              </p>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-neutral-200 pt-4 dark:border-white/10">
                <p className="text-sm text-neutral-700 dark:text-neutral-300">
                  {doctor.consultation_fee > 0 ? money(doctor.consultation_fee, doctor.currency) : 'Free'}
                  <span className="muted"> · {doctor.slot_minutes} min</span>
                </p>
                <Button onClick={() => setBooking(doctor)} disabled={doctor.availability.length === 0}>
                  {doctor.availability.length === 0 ? 'No times set' : 'Book'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      {booking && <BookingDialog doctor={booking} timezone={timezone} onClose={() => setBooking(null)} />}
    </DashboardLayout>
  )
}
