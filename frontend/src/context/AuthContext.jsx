import { createContext, useContext, useEffect, useState } from 'react'

import * as api from '../services/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function restoreSession() {
      const token = api.getAuthToken()

      if (!token) {
        if (mounted) {
          setLoading(false)
        }
        return
      }

      try {
        const currentUser = await api.getCurrentUser()

        if (mounted) {
          setUser(currentUser)
          localStorage.setItem(
            'skyntri-user',
            JSON.stringify(currentUser)
          )
        }
      } catch (error) {
        api.clearAuthToken()
        localStorage.removeItem('skyntri-user')

        if (mounted) {
          setUser(null)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      mounted = false
    }
  }, [])

  const login = async (email, password) => {
    const result = await api.loginUser(email, password)

    setUser(result.user)

    localStorage.setItem(
      'skyntri-user',
      JSON.stringify(result.user)
    )

    return result
  }

  const register = async (fullName, email, password) => {
    const result = await api.registerUser(
      fullName,
      email,
      password
    )

    setUser(result.user)

    localStorage.setItem(
      'skyntri-user',
      JSON.stringify(result.user)
    )

    return result
  }

  const loginWithGoogle = async (credential) => {
    const result = await api.loginWithGoogle(credential)
    setUser(result.user)
    localStorage.setItem('skyntri-user', JSON.stringify(result.user))
    return result
  }

  const refreshUser = async () => {
    const current = await api.getCurrentUser()
    setUser(current)
    localStorage.setItem('skyntri-user', JSON.stringify(current))
    return current
  }

  const updateUser = (updates) => {
    setUser((previous) => {
      const next = {
        ...previous,
        ...updates,
      }

      localStorage.setItem(
        'skyntri-user',
        JSON.stringify(next)
      )

      return next
    })
  }

  const logout = () => {
    api.clearAuthToken()
    setUser(null)
    localStorage.removeItem('skyntri-user')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        loginWithGoogle,
        refreshUser,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error(
      'useAuth must be used within AuthProvider'
    )
  }

  return context
}