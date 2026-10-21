import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface-light px-4 text-center dark:bg-surface-dark">
      <p className="text-4xl font-semibold text-neutral-300 dark:text-neutral-700">404</p>
      <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Page not found</h1>
      <p className="max-w-xs text-sm text-neutral-500 dark:text-neutral-400">
        The page you're looking for doesn't exist or has moved.
      </p>
      <Link to="/dashboard">
        <Button className="mt-2">Back to Dashboard</Button>
      </Link>
    </div>
  )
}
