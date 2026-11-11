import { Laptop, Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Alert, Badge, Field, Toggle } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const SKIN_TYPES = ['Not set', 'Normal', 'Dry', 'Oily', 'Combination', 'Sensitive']
const THEMES = [
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'system', label: 'System', icon: Laptop },
]

function Block({ title, description, children }) {
  return (
    <Card className="p-5">
      <h2 className="text-base font-semibold text-neutral-900 dark:text-white">{title}</h2>
      {description && <p className="muted mt-0.5 text-sm">{description}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  )
}

function ProfileForm() {
  const { user, updateUser } = useAuth()
  const { showToast } = useToast()
  const [form, setForm] = useState({ fullName: '', phone: '', skinType: 'Not set' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setForm({ fullName: user?.fullName || '', phone: user?.phone || '', skinType: user?.skinType || 'Not set' })
  }, [user])

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      updateUser(await api.updateProfile(form))
      showToast('Profile saved.', 'success')
    } catch (err) {
      setError(err.message?.includes('pattern') ? 'Enter a valid phone number, for example +92 300 1234567.' : err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Field label="Full name">
        <input className="field" required maxLength={120} value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} autoComplete="name" />
      </Field>
      <Field label="Mobile number" hint="Used by the clinic for appointment reminders.">
        <input className="field" type="tel" maxLength={20} placeholder="+92 300 1234567" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} autoComplete="tel" />
      </Field>
      <Field label="Skin type">
        <select className="field" value={form.skinType} onChange={(e) => setForm({ ...form, skinType: e.target.value })}>
          {SKIN_TYPES.map((type) => <option key={type}>{type}</option>)}
        </select>
      </Field>
      <div className="sm:col-span-2">
        {error && <Alert className="mb-3">{error}</Alert>}
        <Button type="submit" loading={saving}>Save profile</Button>
      </div>
    </form>
  )
}

function EmailForm() {
  const { user, updateUser } = useAuth()
  const { showToast } = useToast()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (user?.google_linked) {
    return (
      <p className="text-sm text-neutral-700 dark:text-neutral-300">
        {user.email} <Badge tone="green">Google</Badge>
        <span className="muted mt-1 block text-xs">This account signs in with Google, so the address is managed in your Google account.</span>
      </p>
    )
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      updateUser(await api.changeEmail(email, password))
      setEmail('')
      setPassword('')
      showToast('E-mail address changed.', 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <p className="muted text-sm sm:col-span-2">Current address: <span className="font-medium text-neutral-800 dark:text-neutral-100">{user?.email}</span></p>
      <Field label="New e-mail address">
        <input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      </Field>
      <Field label="Current password">
        <input className="field" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
      </Field>
      <div className="sm:col-span-2">
        {error && <Alert className="mb-3">{error}</Alert>}
        <Button type="submit" variant="outline" loading={saving}>Change e-mail</Button>
      </div>
    </form>
  )
}

function PasswordForm() {
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const first = user && user.password_set === false

  const save = async (e) => {
    e.preventDefault()
    setError('')
    if (next.length < 8) return setError('Use at least 8 characters.')
    if (next !== repeat) return setError('The two new passwords are not the same.')
    setSaving(true)
    try {
      if (first) await api.setPassword(next)
      else await api.changePassword(current, next)
      await refreshUser()
      setCurrent('')
      setNext('')
      setRepeat('')
      showToast(first ? 'Password saved.' : 'Password changed.', 'success')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
    return undefined
  }

  return (
    <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {first ? (
        <p className="muted text-sm sm:col-span-2">You sign in with Google. Add a password if you also want to sign in with your e-mail address.</p>
      ) : (
        <Field label="Current password" className="sm:col-span-2 sm:max-w-sm">
          <input className="field" type="password" required value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
        </Field>
      )}
      <Field label="New password" hint="At least 8 characters.">
        <input className="field" type="password" required value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
      </Field>
      <Field label="Repeat new password">
        <input className="field" type="password" required value={repeat} onChange={(e) => setRepeat(e.target.value)} autoComplete="new-password" />
      </Field>
      <div className="sm:col-span-2">
        {error && <Alert className="mb-3">{error}</Alert>}
        <Button type="submit" variant="outline" loading={saving}>{first ? 'Save password' : 'Change password'}</Button>
      </div>
    </form>
  )
}

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { user, updateUser, logout } = useAuth()
  const { showToast } = useToast()
  const [deleting, setDeleting] = useState(false)

  const saveNotification = async (key, value) => {
    const next = { notifyAnalysis: Boolean(user?.notifyAnalysis), notifyReports: Boolean(user?.notifyReports), [key]: value }
    try {
      updateUser(await api.updateNotificationSettings(next))
    } catch (err) {
      showToast(err.message || 'Unable to update notifications.', 'error')
    }
  }

  const deleteAccount = async () => {
    if (!window.confirm('Delete your account, photos, results and appointments for good? This cannot be undone.')) return
    setDeleting(true)
    try {
      await api.deleteAccount()
      logout()
    } catch (err) {
      showToast(err.message || 'The account could not be deleted.', 'error')
      setDeleting(false)
    }
  }

  return (
    <DashboardLayout title="Settings" width="md">
      <div className="space-y-5">
        <Block title="Profile">
          <ProfileForm />
        </Block>

        <Block title="E-mail address" description="You sign in with this address.">
          <EmailForm />
        </Block>

        <Block title="Password">
          <PasswordForm />
        </Block>

        <Block title="Appearance">
          <div className="inline-flex rounded-lg border border-neutral-300 p-0.5 dark:border-white/15">
            {THEMES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTheme(id)}
                aria-pressed={theme === id}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
                  theme === id ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900' : 'text-neutral-600 dark:text-neutral-300'
                }`}
              >
                <Icon className="h-3.5 w-3.5" /> {label}
              </button>
            ))}
          </div>
        </Block>

        <Block title="Notifications">
          <div className="divide-soft">
            <div className="flex items-center justify-between py-2.5">
              <span className="text-sm text-neutral-700 dark:text-neutral-300">Tell me when an analysis is ready</span>
              <Toggle label="Analysis notifications" checked={Boolean(user?.notifyAnalysis)} onChange={(v) => saveNotification('notifyAnalysis', v)} />
            </div>
            <div className="flex items-center justify-between py-2.5">
              <span className="text-sm text-neutral-700 dark:text-neutral-300">Tell me when a report is ready</span>
              <Toggle label="Report notifications" checked={Boolean(user?.notifyReports)} onChange={(v) => saveNotification('notifyReports', v)} />
            </div>
          </div>
        </Block>

        {user?.role !== 'doctor' && (
          <Block title="Are you a dermatologist?" description="Apply to see patients through Skyntri. The clinic checks your licence first.">
            <Link to="/doctor" className="link text-sm">Open the doctor application</Link>
          </Block>
        )}

        <Block title="Account">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={logout}>Log out</Button>
            <Button variant="danger" loading={deleting} onClick={deleteAccount}>Delete my account</Button>
          </div>
          <p className="muted mt-3 text-xs">
            Deleting removes your photos, results, messages and appointments. Need help? <Link to="/contact" className="link">Contact the clinic</Link>.
          </p>
        </Block>
      </div>
    </DashboardLayout>
  )
}
