import { ClipboardList } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'
import { OrderSummary } from './Orders.jsx'

const NEXT = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['shipped', 'cancelled'],
  shipped: ['delivered'],
  delivered: [],
  cancelled: [],
}

export default function AdminOrders() {
  const [filter, setFilter] = useState('')
  const [orders, setOrders] = useState(null)
  const { showToast } = useToast()

  const load = useCallback(() => {
    setOrders(null)
    api.adminListOrders(filter).then(setOrders).catch((err) => showToast(err.message, 'error'))
  }, [filter, showToast])

  useEffect(load, [load])

  const change = async (order, status) => {
    try {
      const updated = await api.adminUpdateOrderStatus(order.id, status)
      setOrders((list) => list.map((o) => (o.id === order.id ? updated : o)))
      showToast(`Order marked ${status}.`, 'success')
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  const pay = async (order, paymentStatus) => {
    try {
      const updated = await api.adminUpdatePayment(order.id, paymentStatus)
      setOrders((list) => list.map((o) => (o.id === order.id ? updated : o)))
      showToast(`Payment marked ${paymentStatus}.`, 'success')
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <DashboardLayout title="Orders & Payments" subtitle="Confirm, ship and deliver orders; record cash payments">
      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm text-neutral-600 dark:text-neutral-300">Status</label>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-panel-dark"
        >
          <option value="">All</option>
          {Object.keys(NEXT).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {!orders && <Spinner label="Loading orders…" />}
      {orders && orders.length === 0 && <EmptyState icon={ClipboardList} title="No orders" />}

      <div className="space-y-4">
        {orders?.map((order) => (
          <OrderSummary key={order.id} order={order}>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-neutral-500">Payment (cash on delivery):</span>
              <span className={`badge ${order.payment_status === 'paid' ? 'bg-brand-50 text-brand-700' : order.payment_status === 'refunded' ? 'bg-amber-50 text-amber-700' : 'bg-neutral-100 text-neutral-600'}`}>
                {order.payment_status}
              </span>
              {order.payment_status === 'unpaid' && order.status !== 'cancelled' && (
                <button onClick={() => pay(order, 'paid')} className="rounded-lg border border-brand-300 px-2.5 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50">
                  Mark cash received
                </button>
              )}
              {order.payment_status === 'paid' && (
                <button onClick={() => pay(order, 'refunded')} className="rounded-lg border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50">
                  Mark refunded
                </button>
              )}
            </div>
            {NEXT[order.status].length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {NEXT[order.status].map((s) => (
                  <button
                    key={s}
                    onClick={() => change(order, s)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize ${
                      s === 'cancelled'
                        ? 'border border-red-200 text-red-600 hover:bg-red-50'
                        : 'bg-brand-600 text-white hover:bg-brand-700'
                    }`}
                  >
                    Mark {s}
                  </button>
                ))}
              </div>
            )}
          </OrderSummary>
        ))}
      </div>
    </DashboardLayout>
  )
}
