import { useEffect, useState } from 'react'
import Card from '../components/Card.jsx'
import { Alert, Badge, Section, Toggle, dateTime } from '../components/ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

const TITLES = {
  disease_screening_enabled: 'Skin disease screening',
  agent_posts_auto_publish: 'Publish daily posts automatically',
}
const INTEGRATIONS = [
  ['google_sign_in', 'Sign in with Google', 'GOOGLE_CLIENT_ID'],
  ['card_payments', 'Card payments (Stripe)', 'STRIPE_SECRET_KEY'],
  ['paypal', 'PayPal', 'PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET'],
  ['email', 'E-mail (reminders, password reset)', 'SMTP_HOST, SMTP_FROM'],
  ['assistant_llm', 'Assistant language model', 'LLM_ENABLED, GEMINI_API_KEY'],
  ['assistant_images', 'Assistant illustrations', 'LLM_IMAGE_ENABLED'],
  ['agent_scheduler', 'Built-in agent scheduler', 'AGENTS_SCHEDULER_ENABLED'],
]

export default function AdminSettings() {
  const { showToast } = useToast()
  const [data, setData] = useState(null)
  const [audit, setAudit] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  const loadAudit = () => api.adminAuditLog().then(setAudit).catch(() => {})

  useEffect(() => {
    api.adminGetSettings().then(setData).catch((err) => setError(err.message))
    loadAudit()
  }, [])

  const change = async (setting, value) => {
    if (setting.key === 'disease_screening_enabled' && value &&
      !window.confirm('Turn on skin disease screening for all users?\n\nDo this only after a dermatologist has reviewed the model results. The screening never gives a diagnosis and always advises a doctor for suspicious lesions.')) return
    setBusy(setting.key)
    try {
      setData(await api.adminUpdateSetting(setting.key, value))
      loadAudit()
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  return (
    <AdminLayout title="Settings">
      {error && <Alert className="mb-4">{error}</Alert>}
      {!data && !error && <p className="muted text-sm">Loading…</p>}
      {data && (
        <div className="space-y-8">
          <Section title="Switches">
            <Card className="divide-soft">
              {data.settings.map((setting) => (
                <div key={setting.key} className="flex items-start justify-between gap-4 p-4">
                  <div>
                    <p className="text-sm font-medium text-neutral-900 dark:text-white">{TITLES[setting.key] || setting.key}</p>
                    <p className="muted mt-0.5 text-sm">{setting.description}</p>
                    {setting.key === 'disease_screening_enabled' && !data.disease_model_installed && (
                      <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">The model files are not in backend/models/ yet, so this cannot be turned on.</p>
                    )}
                  </div>
                  <Toggle
                    label={TITLES[setting.key] || setting.key}
                    checked={Boolean(setting.value)}
                    disabled={busy === setting.key || (setting.key === 'disease_screening_enabled' && !data.disease_model_installed && !setting.value)}
                    onChange={(value) => change(setting, value)}
                  />
                </div>
              ))}
            </Card>
          </Section>

          <Section title="Connections" description="Keys are set on the server in the .env file. Only whether each one is set is shown here.">
            <Card className="divide-soft">
              {INTEGRATIONS.map(([key, name, env]) => (
                <div key={key} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div>
                    <p className="text-sm text-neutral-900 dark:text-white">{name}</p>
                    <p className="muted text-xs">{env}</p>
                  </div>
                  <Badge tone={data.integrations[key] ? 'green' : 'neutral'}>{data.integrations[key] ? 'Connected' : 'Not set up'}</Badge>
                </div>
              ))}
            </Card>
          </Section>

          <Section title="Recent admin and doctor actions">
            {audit.length === 0 ? (
              <p className="muted text-sm">Nothing recorded yet.</p>
            ) : (
              <Card className="divide-soft">
                {audit.slice(0, 20).map((event) => (
                  <div key={event.id} className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-2.5 text-sm">
                    <p className="text-neutral-800 dark:text-neutral-200"><span className="font-medium">{event.action}</span>{event.detail ? ` · ${event.detail}` : ''}</p>
                    <p className="muted text-xs">{event.actor} · {dateTime(event.created_at)}</p>
                  </div>
                ))}
              </Card>
            )}
          </Section>
        </div>
      )}
    </AdminLayout>
  )
}
