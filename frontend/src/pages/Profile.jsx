import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

export default function Profile() {
  const { user, updateUser } = useAuth()
  const { showToast } = useToast()
  const [fullName, setFullName] = useState('')
  const [skinType, setSkinType] = useState('Not set')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setFullName(user?.fullName || '')
    setSkinType(user?.skinType || 'Not set')
  }, [user])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)

    try {
      const updated = await api.updateProfile({ fullName, skinType })
      updateUser(updated)
      showToast('Profile updated.', 'success')
    } catch (err) {
      showToast(err.message || 'Unable to update profile.', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <DashboardLayout title="Profile">
      <Card className="mx-auto max-w-lg p-5">
        <div className="mb-5 flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-full bg-brand-100 text-lg font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              (user?.fullName || 'S').charAt(0).toUpperCase()
            )}
          </div>

          <div>
            <p className="font-medium text-neutral-800 dark:text-neutral-100">
              {user?.fullName}
            </p>
            <p className="text-xs text-neutral-400">
              Member since {user?.memberSince || '—'}
            </p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Full name
            </label>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Email
            </label>
            <input
              value={user?.email || ''}
              disabled
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Skin type
            </label>
            <select
              value={skinType}
              onChange={(e) => setSkinType(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
            >
              <option>Not set</option>
              <option>Normal</option>
              <option>Dry</option>
              <option>Oily</option>
              <option>Combination</option>
              <option>Sensitive</option>
            </select>
          </div>

          <Button type="submit" loading={saving}>
            Save changes
          </Button>
        </form>
      </Card>
    </DashboardLayout>
  )
}
