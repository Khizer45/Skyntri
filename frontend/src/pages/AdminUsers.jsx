import { Search, ShieldCheck, UserX } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [q, setQ] = useState('')
  const { showToast } = useToast()

  const load = useCallback((query = '') => {
    api.adminListUsers(query).then(setUsers).catch((err) => showToast(err.message, 'error'))
  }, [showToast])

  useEffect(() => load(), [load])

  const update = async (u, payload, msg) => {
    try {
      const updated = await api.adminUpdateUser(u.id, payload)
      setUsers((list) => list.map((x) => (x.id === u.id ? updated : x)))
      showToast(msg, 'success')
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <AdminLayout title="Users">
      <form onSubmit={(e) => { e.preventDefault(); load(q) }} className="mb-4 flex max-w-md gap-2">
        <input className="field" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or e-mail" />
        <Button type="submit" icon={Search}>Search</Button>
      </form>

      {!users && <Spinner label="Loading users…" />}
      {users && (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-white/5">
              <tr>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Joined</th>
                <th className="px-4 py-3">Orders</th>
                <th className="px-4 py-3">Analyses</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-white/5">
              {users.map((u) => (
                <tr key={u.id} className={u.is_active ? '' : 'opacity-60'}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-neutral-900 dark:text-neutral-100">{u.full_name}</p>
                    <p className="text-xs text-neutral-500">{u.email}</p>
                  </td>
                  <td className="px-4 py-3 text-neutral-500">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">{u.orders}</td>
                  <td className="px-4 py-3">{u.analyses}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${u.role === 'admin' ? 'bg-accent-100 text-accent-700' : 'bg-neutral-100 text-neutral-600'} dark:bg-white/5 dark:text-neutral-300`}>
                      {u.role}
                    </span>
                    {!u.is_active && <span className="badge ml-1 bg-red-50 text-red-600">inactive</span>}
                  </td>
                  <td className="px-4 py-3">
                    {u.id !== me?.id && (
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost" icon={ShieldCheck}
                          onClick={() => update(u, { role: u.role === 'admin' ? 'user' : 'admin' }, u.role === 'admin' ? 'Admin access removed.' : 'User is now an admin.')}>
                          {u.role === 'admin' ? 'Remove admin' : 'Make admin'}
                        </Button>
                        <Button size="sm" variant="ghost" icon={UserX}
                          onClick={() => update(u, { is_active: !u.is_active }, u.is_active ? 'Account deactivated.' : 'Account activated.')}>
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </div>
                    )}
                    {u.id === me?.id && <p className="text-right text-xs text-neutral-400">you</p>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </AdminLayout>
  )
}
