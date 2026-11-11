import { Download, ExternalLink, Plus, Send, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import PaymentOptions from '../components/PaymentOptions.jsx'
import { Alert, Field, StatusBadge, dateOnly, dateTime, label, money } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const KINDS = [
  { id: 'medicine', label: 'Medicine' },
  { id: 'treatment', label: 'Treatment' },
  { id: 'skincare', label: 'Skin care' },
]
const EMPTY_ITEM = { kind: 'medicine', name: '', dosage: '', frequency: '', duration: '', instructions: '' }

function Row({ name, children }) {
  return (
    <div className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:gap-4">
      <dt className="muted w-32 shrink-0 text-sm">{name}</dt>
      <dd className="min-w-0 flex-1 text-sm text-neutral-900 dark:text-neutral-100">{children}</dd>
    </div>
  )
}

function Messages({ appointment }) {
  const [messages, setMessages] = useState([])
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef(null)
  const closed = ['cancelled', 'no_show'].includes(appointment.status)

  const load = useCallback(() => {
    api.listAppointmentMessages(appointment.id).then(setMessages).catch(() => {})
  }, [appointment.id])

  useEffect(() => {
    load()
    const timer = setInterval(load, 15000)
    return () => clearInterval(timer)
  }, [load])

  useEffect(() => {
    // Scroll the message list, not the whole page.
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages.length])

  const send = async (e) => {
    e.preventDefault()
    if (!body.trim()) return
    setSending(true)
    setError('')
    try {
      const message = await api.sendAppointmentMessage(appointment.id, body.trim())
      setMessages((prev) => [...prev, message])
      setBody('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <Card className="p-5">
      <h2 className="text-base font-semibold text-neutral-900 dark:text-white">Messages</h2>
      <p className="muted text-xs">Only you and the other person in this appointment can read these.</p>
      <div ref={listRef} className="thin-scrollbar mt-4 max-h-80 space-y-2.5 overflow-y-auto">
        {messages.length === 0 && <p className="muted text-sm">No messages yet.</p>}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.mine ? 'justify-end' : ''}`}>
            <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${m.mine ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900' : 'bg-neutral-100 text-neutral-900 dark:bg-white/10 dark:text-neutral-100'}`}>
              {!m.mine && <p className="mb-0.5 text-xs font-medium opacity-70">{m.sender_name}</p>}
              <p className="whitespace-pre-wrap">{m.body}</p>
              <p className="mt-0.5 text-[10px] opacity-60">{dateTime(m.created_at)}</p>
            </div>
          </div>
        ))}
      </div>
      {error && <Alert className="mt-3">{error}</Alert>}
      {!closed && (
        <form onSubmit={send} className="mt-3 flex gap-2">
          <input className="field" maxLength={2000} placeholder="Write a message" value={body} onChange={(e) => setBody(e.target.value)} aria-label="Message" />
          <Button type="submit" icon={Send} loading={sending} disabled={!body.trim()} aria-label="Send message" />
        </form>
      )}
    </Card>
  )
}

function PrescriptionView({ appointment }) {
  const { showToast } = useToast()
  const rx = appointment.prescription
  if (!rx && !appointment.assessment) return null

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold text-neutral-900 dark:text-white">Doctor's summary</h2>
        <Button variant="outline" size="sm" icon={Download} onClick={() => api.downloadPrescription(appointment.id).catch((e) => showToast(e.message, 'error'))}>
          PDF
        </Button>
      </div>
      {appointment.assessment && <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-800 dark:text-neutral-200">{appointment.assessment}</p>}
      {rx?.items?.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-neutral-200 dark:border-white/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-neutral-50 text-xs text-neutral-600 dark:bg-white/5 dark:text-neutral-300">
              <tr>{['Type', 'Name', 'Dose', 'How often', 'For how long', 'Instructions'].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rx.items.map((item, i) => (
                <tr key={i} className="border-t border-neutral-200 align-top dark:border-white/10">
                  <td className="px-3 py-2">{label(item.kind)}</td>
                  <td className="px-3 py-2 font-medium text-neutral-900 dark:text-white">{item.name}</td>
                  <td className="px-3 py-2">{item.dosage || '–'}</td>
                  <td className="px-3 py-2">{item.frequency || '–'}</td>
                  <td className="px-3 py-2">{item.duration || '–'}</td>
                  <td className="px-3 py-2">{item.instructions || '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rx?.advice && <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-800 dark:text-neutral-200"><span className="font-medium">Advice: </span>{rx.advice}</p>}
      {appointment.follow_up_on && <p className="muted mt-3 text-sm">Follow-up: {dateOnly(appointment.follow_up_on)}</p>}
    </Card>
  )
}

function DoctorTools({ appointment, onChange }) {
  const { showToast } = useToast()
  const [notes, setNotes] = useState({
    assessment: appointment.assessment || '',
    private_notes: appointment.private_notes || '',
    meeting_url: appointment.meeting_url || '',
    follow_up_on: appointment.follow_up_on ? appointment.follow_up_on.slice(0, 10) : '',
  })
  const [items, setItems] = useState(appointment.prescription?.items?.length ? appointment.prescription.items.map((i) => ({ ...EMPTY_ITEM, ...i })) : [])
  const [advice, setAdvice] = useState(appointment.prescription?.advice || '')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const started = new Date(appointment.starts_at) <= new Date()
  const canPrescribe = ['confirmed', 'completed'].includes(appointment.status)

  const run = async (key, action, done) => {
    setBusy(key)
    setError('')
    try {
      await action()
      if (done) showToast(done, 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const setStatus = (status) => {
    let cancel_reason
    if (status === 'cancelled') {
      cancel_reason = window.prompt('Reason for cancelling (the patient will see it):') ?? null
      if (cancel_reason === null) return
    }
    run(status, async () => onChange(await api.doctorUpdateAppointment(appointment.id, { status, cancel_reason })), 'Appointment updated.')
  }

  const saveNotes = () =>
    run('notes', async () =>
      onChange(await api.doctorUpdateAppointment(appointment.id, {
        assessment: notes.assessment,
        private_notes: notes.private_notes,
        meeting_url: notes.meeting_url || null,
        follow_up_on: notes.follow_up_on ? new Date(`${notes.follow_up_on}T00:00:00Z`).toISOString() : null,
      })), 'Notes saved.')

  const savePrescription = () =>
    run('rx', async () => {
      const clean = items.filter((i) => i.name.trim()).map((i) => Object.fromEntries(Object.entries(i).map(([k, v]) => [k, v === '' ? null : v])))
      await api.doctorSavePrescription(appointment.id, { advice: advice || null, items: clean })
      onChange(await api.getAppointment(appointment.id))
    }, 'Prescription saved.')

  const setItem = (index, key, value) => setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [key]: value } : item)))

  return (
    <Card className="space-y-5 border-brand-300 p-5 dark:border-brand-800">
      <div>
        <h2 className="text-base font-semibold text-neutral-900 dark:text-white">Doctor's tools</h2>
        <p className="muted text-xs">Patient: {appointment.patient_name} · {appointment.patient_email}{appointment.patient_phone ? ` · ${appointment.patient_phone}` : ''}</p>
      </div>
      {error && <Alert>{error}</Alert>}

      <div className="flex flex-wrap gap-2">
        {appointment.status === 'requested' && <Button loading={busy === 'confirmed'} onClick={() => setStatus('confirmed')}>Confirm</Button>}
        {appointment.status === 'confirmed' && (
          <>
            <Button loading={busy === 'completed'} disabled={!started} onClick={() => setStatus('completed')}>Mark completed</Button>
            <Button variant="outline" loading={busy === 'no_show'} disabled={!started} onClick={() => setStatus('no_show')}>Patient did not come</Button>
          </>
        )}
        {['requested', 'confirmed'].includes(appointment.status) && (
          <Button variant="outline" loading={busy === 'cancelled'} onClick={() => setStatus('cancelled')}>Cancel</Button>
        )}
      </div>
      {appointment.status === 'confirmed' && !started && <p className="muted -mt-3 text-xs">You can complete the visit after it has started.</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Meeting link" hint="For video visits. Must start with https://">
          <input className="field" type="url" placeholder="https://meet.google.com/…" value={notes.meeting_url} onChange={(e) => setNotes({ ...notes, meeting_url: e.target.value })} />
        </Field>
        <Field label="Follow-up date">
          <input className="field" type="date" value={notes.follow_up_on} onChange={(e) => setNotes({ ...notes, follow_up_on: e.target.value })} />
        </Field>
        <Field label="Assessment" hint="The patient can read this." className="sm:col-span-2">
          <textarea className="field" rows={3} maxLength={4000} value={notes.assessment} onChange={(e) => setNotes({ ...notes, assessment: e.target.value })} />
        </Field>
        <Field label="Private notes" hint="Only you can read these." className="sm:col-span-2">
          <textarea className="field" rows={2} maxLength={4000} value={notes.private_notes} onChange={(e) => setNotes({ ...notes, private_notes: e.target.value })} />
        </Field>
      </div>
      <Button variant="outline" loading={busy === 'notes'} onClick={saveNotes}>Save notes</Button>

      <div className="border-t border-neutral-200 pt-5 dark:border-white/10">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">Prescription</h3>
        {!canPrescribe ? (
          <p className="muted mt-1 text-sm">Confirm the appointment to write a prescription.</p>
        ) : (
          <div className="mt-3 space-y-3">
            {items.map((item, index) => (
              <div key={index} className="space-y-2 rounded-lg border border-neutral-200 p-3 dark:border-white/10">
                <div className="flex flex-col gap-2 sm:flex-row">
                  <select className="field sm:w-36" aria-label="Type" value={item.kind} onChange={(e) => setItem(index, 'kind', e.target.value)}>
                    {KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
                  </select>
                  <input className="field flex-1" placeholder="Name, e.g. Adapalene 0.1% gel" aria-label="Name" maxLength={160} value={item.name} onChange={(e) => setItem(index, 'name', e.target.value)} />
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <input className="field" placeholder="Dose" aria-label="Dose" maxLength={120} value={item.dosage || ''} onChange={(e) => setItem(index, 'dosage', e.target.value)} />
                  <input className="field" placeholder="How often" aria-label="How often" maxLength={120} value={item.frequency || ''} onChange={(e) => setItem(index, 'frequency', e.target.value)} />
                  <input className="field" placeholder="For how long" aria-label="For how long" maxLength={120} value={item.duration || ''} onChange={(e) => setItem(index, 'duration', e.target.value)} />
                </div>
                <div className="flex gap-2">
                  <input className="field flex-1" placeholder="Instructions" aria-label="Instructions" maxLength={600} value={item.instructions || ''} onChange={(e) => setItem(index, 'instructions', e.target.value)} />
                  <Button variant="ghost" size="sm" icon={Trash2} onClick={() => setItems((prev) => prev.filter((_, i) => i !== index))}>Remove</Button>
                </div>
              </div>
            ))}
            <Button variant="outline" size="sm" icon={Plus} onClick={() => setItems((prev) => [...prev, { ...EMPTY_ITEM }])}>Add item</Button>
            <Field label="Advice">
              <textarea className="field" rows={2} maxLength={3000} value={advice} onChange={(e) => setAdvice(e.target.value)} />
            </Field>
            <Button loading={busy === 'rx'} onClick={savePrescription}>Save prescription</Button>
          </div>
        )}
      </div>
    </Card>
  )
}

export default function AppointmentDetail() {
  const { appointmentId } = useParams()
  const { user } = useAuth()
  const { showToast } = useToast()
  const [appointment, setAppointment] = useState(null)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    setAppointment(null)
    api.getAppointment(appointmentId).then(setAppointment).catch((err) => setError(err.message))
  }, [appointmentId])

  if (error || !appointment) {
    return (
      <DashboardLayout title="Appointment" width="md">
        {error ? <Alert>{error}</Alert> : <p className="muted text-sm">Loading…</p>}
      </DashboardLayout>
    )
  }

  const isDoctor = appointment.patient_id !== user?.id
  const active = ['requested', 'confirmed'].includes(appointment.status)
  const future = new Date(appointment.starts_at) > new Date()

  const cancel = async () => {
    if (!window.confirm('Cancel this appointment?')) return
    setCancelling(true)
    try {
      setAppointment(await api.cancelAppointment(appointment.id))
      showToast('Appointment cancelled.', 'success')
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <DashboardLayout title="Appointment" width="md">
      <Link to={isDoctor ? '/doctor' : '/appointments'} className="link text-sm">← {isDoctor ? 'Doctor portal' : 'All appointments'}</Link>

      <div className="mt-4 space-y-5">
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
                {isDoctor ? appointment.patient_name : appointment.doctor_name}
              </h2>
              <p className="muted text-sm">{isDoctor ? 'Patient' : appointment.doctor_specialty}</p>
            </div>
            <StatusBadge status={appointment.status} />
          </div>

          <dl className="divide-soft mt-3">
            <Row name="When">{dateTime(appointment.starts_at)}</Row>
            <Row name="Type">{label(appointment.mode)}</Row>
            <Row name="Reason"><span className="whitespace-pre-wrap">{appointment.reason}</span></Row>
            {appointment.cancel_reason && <Row name="Cancelled because">{appointment.cancel_reason}</Row>}
            {appointment.meeting_url && (
              <Row name="Meeting link">
                <a href={appointment.meeting_url} target="_blank" rel="noopener noreferrer" className="link inline-flex items-center gap-1">
                  Join the call <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </Row>
            )}
            <Row name="Fee">
              {appointment.fee > 0 ? money(appointment.fee, appointment.currency) : 'Free'}{' '}
              <StatusBadge status={appointment.payment_status} />
            </Row>
          </dl>

          {appointment.status === 'requested' && !isDoctor && (
            <Alert tone="neutral" className="mt-3">The doctor has not confirmed this time yet. You will see the status change here.</Alert>
          )}

          {!isDoctor && active && future && (
            <Button variant="outline" className="mt-4" loading={cancelling} onClick={cancel}>Cancel appointment</Button>
          )}
        </Card>

        {!isDoctor && active && appointment.payment_status === 'unpaid' && (
          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-neutral-900 dark:text-white">Pay the fee</h2>
            <PaymentOptions purpose="appointment" referenceId={appointment.id} offlineLabel="pay at the clinic" />
          </Card>
        )}

        {appointment.analysis && (
          <Card className="p-5">
            <h2 className="text-base font-semibold text-neutral-900 dark:text-white">Shared skin analysis</h2>
            <p className="muted text-xs">{isDoctor ? 'The patient shared this AI estimate. It is not a diagnosis.' : 'You shared this with the doctor.'}</p>
            <div className="mt-3 flex flex-col gap-4 sm:flex-row">
              {appointment.analysis.imageUrl && <img src={appointment.analysis.imageUrl} alt="Shared skin photo" className="max-h-56 rounded-lg border border-neutral-200 object-contain dark:border-white/10" />}
              <div className="text-sm text-neutral-800 dark:text-neutral-200">
                <p className="font-medium">{appointment.analysis.predicted_condition}</p>
                <p className="muted mt-1">Estimated severity: {appointment.analysis.severity_level} · {dateOnly(appointment.analysis.created_at)}</p>
              </div>
            </div>
          </Card>
        )}

        {isDoctor ? <DoctorTools appointment={appointment} onChange={setAppointment} /> : <PrescriptionView appointment={appointment} />}

        <Messages appointment={appointment} />
      </div>
    </DashboardLayout>
  )
}
