import {
  AlertTriangle,
  Banknote,
  Boxes,
  ClipboardList,
  Clock,
  MessageSquare,
  PackageCheck,
  ScanFace,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Card from '../components/Card.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { formatPrice } from '../components/ProductCard.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'
import { STATUS_STYLES } from './Orders.jsx'

function Stat({ icon: Icon, label, value, hint, tone = 'brand', to }) {
  const tones = {
    brand: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
    accent: 'bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300',
    amber: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  }
  const body = (
    <Card className="h-full p-5 transition-shadow hover:shadow-card-hover">
      <div className={`inline-flex rounded-xl p-2.5 ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-3 text-xs font-medium uppercase tracking-wide text-neutral-400">{label}</p>
      <p className="mt-1 font-display text-2xl font-bold text-neutral-900 dark:text-white">{value}</p>
      {hint && <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{hint}</p>}
    </Card>
  )
  return to ? <Link to={to}>{body}</Link> : body
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const { showToast } = useToast()

  useEffect(() => {
    api.adminStats().then(setStats).catch((err) => showToast(err.message, 'error'))
  }, [showToast])

  return (
    <AdminLayout title="Overview">
      {!stats && <Spinner label="Loading statistics…" />}
      {stats && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat icon={Banknote} label="Payments collected" value={formatPrice(stats.payments.collected, stats.currency)}
              hint={`${formatPrice(stats.payments.outstanding, stats.currency)} still to collect`} to="/admin/orders" />
            <Stat icon={ClipboardList} label="Orders" value={stats.orders.total} tone="blue"
              hint={`${stats.orders.by_status.pending} pending · ${stats.orders.by_status.shipped} shipped`} to="/admin/orders" />
            <Stat icon={Boxes} label="Products" value={`${stats.products.active}/${stats.products.total}`} tone="accent"
              hint={`${stats.products.out_of_stock} out of stock · ${stats.products.low_stock} low`} to="/admin/products" />
            <Stat icon={Users} label="Users" value={stats.users.total} tone="amber"
              hint={`${stats.users.new_7d} new this week · ${stats.users.admins} admin(s)`} to="/admin/users" />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-2">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-bold text-neutral-900 dark:text-white">Recent orders</h2>
                <Link to="/admin/orders" className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300">Manage all</Link>
              </div>
              {stats.recent_orders.length === 0 ? (
                <p className="text-sm text-neutral-500">No orders yet.</p>
              ) : (
                <ul className="divide-y divide-neutral-100 dark:divide-white/5">
                  {stats.recent_orders.map((o) => (
                    <li key={o.id} className="flex items-center justify-between py-2.5 text-sm">
                      <div>
                        <p className="font-medium text-neutral-800 dark:text-neutral-100">{o.shipping_name}</p>
                        <p className="text-xs text-neutral-400">#{o.id.slice(0, 8)} · {new Date(o.created_at).toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`badge capitalize ${STATUS_STYLES[o.status]}`}>{o.status}</span>
                        <span className={`badge ${o.payment_status === 'paid' ? 'bg-brand-50 text-brand-700' : 'bg-neutral-100 text-neutral-600'} dark:bg-white/5 dark:text-neutral-300`}>
                          {o.payment_status}
                        </span>
                        <span className="w-24 text-right font-semibold">{formatPrice(o.subtotal, o.currency)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <div className="space-y-4">
              <Card className="p-5">
                <h2 className="mb-3 text-base font-bold text-neutral-900 dark:text-white">Order pipeline</h2>
                {Object.entries(stats.orders.by_status).map(([s, n]) => {
                  const max = Math.max(1, ...Object.values(stats.orders.by_status))
                  return (
                    <div key={s} className="mb-2">
                      <div className="flex justify-between text-xs capitalize text-neutral-500"><span>{s}</span><span>{n}</span></div>
                      <div className="mt-1 h-2 rounded-full bg-neutral-100 dark:bg-white/5">
                        <div className="h-2 rounded-full bg-brand-gradient" style={{ width: `${(n / max) * 100}%` }} />
                      </div>
                    </div>
                  )
                })}
              </Card>
              <Card className="space-y-3 p-5 text-sm">
                {stats.clinic && (
                  <>
                    <p className="flex items-center gap-2"><Users className="h-4 w-4 text-brand-600" /> {stats.clinic.doctors} doctor(s) · {stats.clinic.appointments_upcoming} upcoming appointment(s)</p>
                    {stats.clinic.doctors_pending > 0 && (
                      <Link to="/admin/doctors" className="flex items-center gap-2 text-amber-700 hover:underline dark:text-amber-300">
                        <Clock className="h-4 w-4" /> {stats.clinic.doctors_pending} doctor application(s) to review
                      </Link>
                    )}
                  </>
                )}
                <p className="flex items-center gap-2"><ScanFace className="h-4 w-4 text-brand-600" /> {stats.analyses.total} skin analyses ({stats.analyses.last_7d} this week)</p>
                <p className="flex items-center gap-2"><MessageSquare className="h-4 w-4 text-brand-600" /> {stats.contact_messages} contact messages</p>
                <p className="flex items-center gap-2"><PackageCheck className="h-4 w-4 text-brand-600" /> {formatPrice(stats.payments.refunded, stats.currency)} refunded</p>
                {stats.products.stale_prices > 0 && (
                  <p className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
                    <AlertTriangle className="h-4 w-4" /> {stats.products.stale_prices} product price(s) need re-checking
                  </p>
                )}
                {stats.orders.by_status.pending > 0 && (
                  <p className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <Clock className="h-4 w-4" /> {stats.orders.by_status.pending} order(s) waiting for confirmation
                  </p>
                )}
              </Card>
            </div>
          </div>
        </>
      )}
    </AdminLayout>
  )
}
