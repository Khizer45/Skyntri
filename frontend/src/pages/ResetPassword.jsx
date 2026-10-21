import { LockKeyhole } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import AuthLayout from '../layouts/AuthLayout.jsx'
import * as api from '../services/api.js'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = useMemo(() => searchParams.get('token') || '', [searchParams])
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!token) {
      setError('This reset link is missing its token.')
      return
    }

    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)

    try {
      await api.resetPassword(token, password)
      setSuccess(true)
    } catch (err) {
      setError(err.message || 'Unable to reset your password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Set a new password" subtitle="Choose a new password for your Skyntri account">
      {success ? (
        <div className="space-y-4">
          <p className="rounded-lg bg-brand-50 px-3 py-2.5 text-sm text-brand-800 dark:bg-brand-900/20 dark:text-brand-200">
            Your password has been reset successfully.
          </p>
          <Button onClick={() => navigate('/login')} className="w-full">
            Continue to login
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              New password
            </label>
            <input
              id="password"
              type="password"
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
            />
          </div>

          <div>
            <label htmlFor="confirm" className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Confirm new password
            </label>
            <input
              id="confirm"
              type="password"
              minLength={8}
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
            />
          </div>

          {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

          <Button type="submit" icon={LockKeyhole} loading={loading} className="w-full">
            Reset password
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
