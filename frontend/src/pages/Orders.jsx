import { Package } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { formatPrice } from '../components/ProductCard.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

export const STATUS_STYLES = {
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  confirmed: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  shipped: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  delivered: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
  cancelled: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
}

export function OrderSummary({ order, children }) {
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-neutral-500">
            Order {order.id.slice(0, 8)} · {new Date(order.created_at).toLocaleString()}
            {order.user_email ? ` · ${order.user_email}` : ''}
          </p>
          <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            {formatPrice(order.subtotal, order.currency)}
          </p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_STYLES[order.status] || ''}`}>
          {order.status}
        </span>
      </div>
      <ul className="mt-3 divide-y divide-neutral-100 text-sm dark:divide-neutral-800">
        {order.items.map((i) => (
          <li key={i.id} className="flex justify-between py-1.5">
            <span className="text-neutral-700 dark:text-neutral-200">
              {i.quantity} × {i.product_name} <span className="text-xs text-neutral-400">({i.brand})</span>
            </span>
            <span className="text-neutral-600 dark:text-neutral-300">{formatPrice(i.line_total, order.currency)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-neutral-500">
        Deliver to {order.shipping_name}, {order.shipping_address}, {order.shipping_city} · {order.shipping_phone} · cash on delivery
      </p>
      {children}
    </Card>
  )
}

export default function Orders() {
  const [orders, setOrders] = useState(null)
  const [busy, setBusy] = useState(null)
  const { showToast } = useToast()

  useEffect(() => {
    api.getOrders().then(setOrders).catch((err) => showToast(err.message, 'error'))
  }, [showToast])

  const cancel = async (orderId) => {
    setBusy(orderId)
    try {
      const updated = await api.cancelOrder(orderId)
      setOrders((list) => list.map((o) => (o.id === orderId ? updated : o)))
      showToast('Order cancelled.', 'success')
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setBusy(null)
    }
  }

  return (
    <DashboardLayout title="My Orders">
      {!orders && <Spinner label="Loading orders…" />}
      {orders && orders.length === 0 && (
        <EmptyState
          icon={Package}
          title="No orders yet"
          action={<Link to="/shop"><Button>Browse products</Button></Link>}
        />
      )}
      <div className="space-y-4">
        {orders?.map((order) => (
          <OrderSummary key={order.id} order={order}>
            {order.status === 'pending' && (
              <Button size="sm" variant="outline" className="mt-3" loading={busy === order.id} onClick={() => cancel(order.id)}>
                Cancel order
              </Button>
            )}
          </OrderSummary>
        ))}
      </div>
    </DashboardLayout>
  )
}
