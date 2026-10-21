import { Mail, MapPin, Phone } from 'lucide-react'
import { useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

export default function Contact() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [form, setForm] = useState({
    name: user?.fullName || '',
    email: user?.email || '',
    subject: '',
    message: '',
  })
  const [sending, setSending] = useState(false)

  const update = (key) => (e) => setForm((current) => ({
    ...current,
    [key]: e.target.value,
  }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSending(true)

    try {
      await api.sendContactMessage(form)
      setForm((current) => ({
        ...current,
        subject: '',
        message: '',
      }))
      showToast('Message sent successfully.', 'success')
    } catch (err) {
      showToast(err.message || 'Unable to send your message.', 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <DashboardLayout title="Contact & Help">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-1">
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Get in touch
          </h2>
          <div className="mt-4 space-y-3 text-sm text-neutral-600 dark:text-neutral-300">
            <div className="flex items-start gap-2.5">
              <Mail className="mt-0.5 h-4 w-4 text-brand-500" />
              <span>Use the form to contact the Skyntri team.</span>
            </div>
            <div className="flex items-start gap-2.5">
              <Phone className="mt-0.5 h-4 w-4 text-brand-500" />
              <span>Support contact details can be configured before deployment.</span>
            </div>
            <div className="flex items-start gap-2.5">
              <MapPin className="mt-0.5 h-4 w-4 text-brand-500" />
              <span>Skyntri project support.</span>
            </div>
          </div>
        </Card>

        <Card className="p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Send a message
          </h2>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Name">
                <input required value={form.name} onChange={update('name')} className={inputClass} />
              </Field>
              <Field label="Email">
                <input type="email" required value={form.email} onChange={update('email')} className={inputClass} />
              </Field>
            </div>

            <Field label="Subject">
              <input required value={form.subject} onChange={update('subject')} className={inputClass} />
            </Field>

            <Field label="Message">
              <textarea required rows={4} value={form.message} onChange={update('message')} className={inputClass} />
            </Field>

            <Button type="submit" loading={sending}>
              Send Message
            </Button>
          </form>
        </Card>
      </div>
    </DashboardLayout>
  )
}

const inputClass = 'w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100'

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {label}
      </label>
      {children}
    </div>
  )
}
