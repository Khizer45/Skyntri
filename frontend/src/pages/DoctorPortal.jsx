import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Alert, Empty, Field, StatusBadge, Tabs, dateOnly } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'
import { AppointmentRow } from './Appointments.jsx'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const BLANK = {
  specialty: 'Dermatology', qualifications: '', license_number: '', bio: '', languages: '',
  years_experience: 0, consultation_fee: 0, slot_minutes: 30,
}

function ProfileFields({ form, setForm, withLicence }) {
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === 'number' ? Number(e.target.value) : e.target.value })
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Field label="Speciality"><input className="field" required maxLength={80} value={form.specialty} onChange={set('specialty')} /></Field>
      <Field label="Qualifications" hint="For example: MBBS, FCPS (Dermatology)">
        <input className="field" required maxLength={200} value={form.qualifications} onChange={set('qualifications')} />
      </Field>
      {withLicence && (
        <Field label="Medical licence number" hint="The clinic checks this before approving you.">
          <input className="field" required minLength={3} maxLength={60} value={form.license_number} onChange={set('license_number')} />
        </Field>
      )}
      <Field label="Languages"><input className="field" maxLength={120} placeholder="English, Urdu" value={form.languages || ''} onChange={set('languages')} /></Field>
      <Field label="Years of experience"><input className="field" type="number" min={0} max={70} value={form.years_experience} onChange={set('years_experience')} /></Field>
      <Field label="Consultation fee" hint="0 means free."><input className="field" type="number" min={0} step="any" value={form.consultation_fee} onChange={set('consultation_fee')} /></Field>
      <Field label="Length of one visit (minutes)"><input className="field" type="number" min={10} max={120} step={5} value={form.slot_minutes} onChange={set('slot_minutes')} /></Field>
      <Field label="About you" className="sm:col-span-2"><textarea className="field" rows={3} maxLength={1500} value={form.bio || ''} onChange={set('bio')} /></Field>
    </div>
  )
}

function Application({ existing, onDone }) {
  const [form, setForm] = useState(existing ? { ...BLANK, ...existing } : BLANK)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const { specialty, qualifications, license_number, bio, languages, years_experience, consultation_fee, slot_minutes } = form
      onDone(await api.applyAsDoctor({
        specialty, qualifications, license_number, bio: bio || null, languages: languages || null,
        years_experience, consultation_fee, slot_minutes,
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="p-5">
      <h2 className="text-base font-semibold text-neutral-900 dark:text-white">Apply as a dermatologist</h2>
      <p className="muted mb-4 mt-0.5 text-sm">Patients can book you after the clinic has checked your licence and approved your profile.</p>
      {existing?.status === 'rejected' && <Alert className="mb-4">Your earlier application was not approved. You can correct it and apply again.</Alert>}
      <form onSubmit={submit} className="space-y-4">
        <ProfileFields form={form} setForm={setForm} withLicence />
        {error && <Alert>{error}</Alert>}
        <Button type="submit" loading={saving}>Send application</Button>
      </form>
    </Card>
  )
}

function Hours({ profile, onSaved }) {
  const { showToast } = useToast()
  const [windows, setWindows] = useState(profile.availability)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const update = (index, key, value) => setWindows((prev) => prev.map((w, i) => (i === index ? { ...w, [key]: value } : w)))
  const save = async () => {
    setSaving(true)
    setError('')
    try {
      onSaved(await api.setMyAvailability(windows))
      showToast('Working hours saved.', 'success')
    } catch (err) {
      setError(err.message?.includes('end_time') ? 'Each end time must be after its start time.' : err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="p-5">
      <p className="muted mb-4 text-sm">Patients can book inside these hours. Times are in the clinic's time zone.</p>
      <div className="space-y-2">
        {windows.length === 0 && <p className="muted text-sm">No working hours yet, so patients cannot book you.</p>}
        {windows.map((w, index) => (
          <div key={index} className="flex flex-wrap items-center gap-2">
            <select className="field w-36" aria-label="Day" value={w.weekday} onChange={(e) => update(index, 'weekday', Number(e.target.value))}>
              {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
            </select>
            <input className="field w-32" type="time" aria-label="From" value={w.start_time} onChange={(e) => update(index, 'start_time', e.target.value)} />
            <span className="muted text-sm">to</span>
            <input className="field w-32" type="time" aria-label="To" value={w.end_time} onChange={(e) => update(index, 'end_time', e.target.value)} />
            <Button variant="ghost" size="sm" icon={Trash2} aria-label="Remove" onClick={() => setWindows((prev) => prev.filter((_, i) => i !== index))} />
          </div>
        ))}
      </div>
      {error && <Alert className="mt-3">{error}</Alert>}
      <div className="mt-4 flex gap-2">
        <Button variant="outline" icon={Plus} onClick={() => setWindows((prev) => [...prev, { weekday: 0, start_time: '09:00', end_time: '13:00' }])}>Add hours</Button>
        <Button loading={saving} onClick={save}>Save</Button>
      </div>
    </Card>
  )
}

function ProfileEditor({ profile, onSaved }) {
  const { showToast } = useToast()
  const [form, setForm] = useState({ ...BLANK, ...profile })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const { specialty, qualifications, bio, languages, years_experience, consultation_fee, slot_minutes } = form
      onSaved(await api.updateMyDoctorProfile({ specialty, qualifications, bio, languages, years_experience, consultation_fee, slot_minutes }))
      showToast('Profile saved.', 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="p-5">
      <form onSubmit={save} className="space-y-4">
        <ProfileFields form={form} setForm={setForm} />
        <p className="muted text-xs">Licence number: {profile.license_number}. To change it, contact the clinic.</p>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" loading={saving}>Save profile</Button>
      </form>
    </Card>
  )
}

function AppointmentList({ scope }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setItems(null)
    api.doctorListAppointments(scope).then(setItems).catch((err) => setError(err.message))
  }, [scope])

  if (error) return <Alert>{error}</Alert>
  if (items === null) return <p className="muted text-sm">Loading…</p>
  if (items.length === 0) return <Empty title={scope === 'upcoming' ? 'No upcoming appointments' : 'No past appointments'} />
  return (
    <Card className="divide-soft overflow-hidden">
      {items.map((a) => <AppointmentRow key={a.id} appointment={a} to={`/appointments/${a.id}`} who={a.patient_name} />)}
    </Card>
  )
}

function Patients() {
  const [items, setItems] = useState(null)
  useEffect(() => {
    api.doctorListPatients().then(setItems).catch(() => setItems([]))
  }, [])
  if (items === null) return <p className="muted text-sm">Loading…</p>
  if (items.length === 0) return <Empty title="No patients yet" />
  return (
    <Card className="divide-soft overflow-hidden">
      {items.map((p) => (
        <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">{p.name}</p>
            <p className="muted truncate text-xs">{p.email}{p.phone ? ` · ${p.phone}` : ''}</p>
          </div>
          <p className="muted text-xs">{p.visits} visit{p.visits === 1 ? '' : 's'} · last {dateOnly(p.last_visit)}</p>
        </div>
      ))}
    </Card>
  )
}

export default function DoctorPortal() {
  const { refreshUser } = useAuth()
  const [profile, setProfile] = useState(undefined)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('upcoming')

  useEffect(() => {
    api.getMyDoctorProfile().then((p) => {
      setProfile(p)
      // The "doctor" role appears as soon as the clinic approves.
      if (p?.status === 'approved') refreshUser().catch(() => {})
    }).catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  let body
  if (error) body = <Alert>{error}</Alert>
  else if (profile === undefined) body = <p className="muted text-sm">Loading…</p>
  else if (profile === null || profile.status === 'rejected') body = <Application existing={profile} onDone={setProfile} />
  else if (profile.status === 'pending') {
    body = (
      <Alert tone="amber">
        <p className="font-medium">Your application is being reviewed.</p>
        <p className="mt-1">The clinic checks your licence ({profile.license_number}) before patients can book you. You can already set your working hours below.</p>
      </Alert>
    )
  } else if (profile.status === 'suspended') {
    body = <Alert>Your doctor profile is paused by the clinic. Please contact the administrator.</Alert>
  }

  const approved = profile?.status === 'approved'

  return (
    <DashboardLayout title="Doctor portal" actions={profile && <StatusBadge status={profile.status} />}>
      {body}
      {profile?.status === 'pending' && <div className="mt-5"><Hours profile={profile} onSaved={setProfile} /></div>}
      {approved && (
        <>
          <Tabs
            value={tab}
            onChange={setTab}
            tabs={[
              { id: 'upcoming', label: 'Upcoming' }, { id: 'past', label: 'Past' }, { id: 'patients', label: 'Patients' },
              { id: 'hours', label: 'Working hours' }, { id: 'profile', label: 'Profile' },
            ]}
          />
          {(tab === 'upcoming' || tab === 'past') && <AppointmentList scope={tab} />}
          {tab === 'patients' && <Patients />}
          {tab === 'hours' && <Hours profile={profile} onSaved={setProfile} />}
          {tab === 'profile' && <ProfileEditor profile={profile} onSaved={setProfile} />}
        </>
      )}
    </DashboardLayout>
  )
}
