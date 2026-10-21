import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Spinner } from './LoadingState.jsx'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return <Spinner label="Loading Skyntri…" className="min-h-screen" />
  if (!user) return <Navigate to="/login" replace />
  return children
}
