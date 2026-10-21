import { Laptop, Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center justify-between py-2.5">
      <span className="text-sm text-neutral-700 dark:text-neutral-300">{label}</span>
      <button
        type="button"
        aria-pressed={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${checked ? 'bg-brand-600' : 'bg-neutral-300 dark:bg-neutral-700'}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
      </button>
    </label>
  )
}

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { user, updateUser, logout } = useAuth()
  const { showToast } = useToast()
  const [analysisNotif, setAnalysisNotif] = useState(Boolean(user?.notifyAnalysis))
  const [reportNotif, setReportNotif] = useState(Boolean(user?.notifyReports))
  const [savingNotifications, setSavingNotifications] = useState(false)

  useEffect(() => {
    setAnalysisNotif(Boolean(user?.notifyAnalysis))
    setReportNotif(Boolean(user?.notifyReports))
  }, [user])

  const saveNotifications = async (nextAnalysis, nextReports) => {
    setAnalysisNotif(nextAnalysis)
    setReportNotif(nextReports)
    setSavingNotifications(true)

    try {
      const updated = await api.updateNotificationSettings({
        notifyAnalysis: nextAnalysis,
        notifyReports: nextReports,
      })
      updateUser(updated)
      showToast('Notification settings updated.', 'success')
    } catch (err) {
      setAnalysisNotif(Boolean(user?.notifyAnalysis))
      setReportNotif(Boolean(user?.notifyReports))
      showToast(err.message || 'Unable to update notifications.', 'error')
    } finally {
      setSavingNotifications(false)
    }
  }

  return (
    <DashboardLayout title="Settings">
      <div className="mx-auto max-w-lg space-y-6">
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Appearance</h2>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {[
              { key: 'light', label: 'Light', icon: Sun },
              { key: 'dark', label: 'Dark', icon: Moon },
              { key: 'system', label: 'System', icon: Laptop },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTheme(key)}
                className={`flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-xs font-medium transition-colors ${
                  theme === key
                    ? 'border-brand-400 bg-brand-50 text-brand-700 dark:border-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                    : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Notifications</h2>
          <div className="mt-1 divide-y divide-neutral-100 dark:divide-neutral-800">
            <Toggle
              checked={analysisNotif}
              onChange={(value) => saveNotifications(value, reportNotif)}
              label="Analysis notifications"
            />
            <Toggle
              checked={reportNotif}
              onChange={(value) => saveNotifications(analysisNotif, value)}
              label="Report notifications"
            />
          </div>
          {savingNotifications && (
            <p className="mt-2 text-xs text-neutral-400">Saving…</p>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Account</h2>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <Button
              variant="outline"
              onClick={() => showToast('Use the password-change option when connected to your account security flow.', 'info')}
            >
              Change password
            </Button>
            <Button variant="danger" onClick={logout}>
              Logout
            </Button>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  )
}
