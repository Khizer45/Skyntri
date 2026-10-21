import { Mail } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button.jsx'
import AuthLayout from '../layouts/AuthLayout.jsx'
import * as api from '../services/api.js'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [devToken, setDevToken] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await api.forgotPassword(email)
      setDevToken(result?.dev_reset_token || '')
      setSent(true)
    } catch (err) {
      setError(err.message || 'Unable to process the request.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Reset your password" subtitle="We'll help you reset your account password">
      {sent ? (
        <div className="space-y-4">
          <p className="rounded-lg bg-brand-50 px-3 py-2.5 text-sm text-brand-800 dark:bg-brand-900/20 dark:text-brand-200">
            If an account exists for {email}, a password reset request has been created.
          </p>

          {devToken && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-900/20">
              <p className="text-xs text-amber-800 dark:text-amber-200">
                Local development mode: email delivery is not configured yet.
              </p>
              <button
                type="button"
                onClick={() => navigate(`/reset-password?token=${encodeURIComponent(devToken)}`)}
                className="mt-2 text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
              >
                Continue to password reset
              </button>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
            />
          </div>

          {error && (
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          )}

          <Button type="submit" icon={Mail} loading={loading} className="w-full">
            Create reset request
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
        <Link to="/login" className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  )
}
