import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Spinner } from './LoadingState.jsx'

// UI convenience only: the server enforces the admin role on every admin API.
export default function AdminRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return <Spinner label="Loading Skyntri…" className="min-h-screen" />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}
