import { Minus, Plus, ShoppingCart, Trash2, Truck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { formatPrice } from '../components/ProductCard.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const inputClass =
  'w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100'

export default function Cart() {
  const { user } = useAuth()
  const [cart, setCart] = useState(null)
  const [busy, setBusy] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [shipping, setShipping] = useState({
    shipping_name: user?.fullName || '',
    shipping_phone: '',
    shipping_address: '',
    shipping_city: '',
    notes: '',
  })
  const { showToast } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    api.getCart().then(setCart).catch((err) => showToast(err.message, 'error'))
  }, [showToast])

  const run = async (fn) => {
    setBusy(true)
    try {
      setCart(await fn())
    } catch (err) {
      showToast(err.message || 'Could not update the cart.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const placeOrder = async (e) => {
    e.preventDefault()
    setPlacing(true)
    try {
      await api.placeOrder(shipping)
      showToast('Order placed. Pay cash on delivery.', 'success')
      navigate('/orders')
    } catch (err) {
      showToast(err.message || 'Could not place the order.', 'error')
      api.getCart().then(setCart).catch(() => {})
    } finally {
      setPlacing(false)
    }
  }

  const field = (key) => (e) => setShipping((s) => ({ ...s, [key]: e.target.value }))

  return (
    <DashboardLayout title="Cart">
      {!cart && <Spinner label="Loading cart…" />}

      {cart && cart.items.length === 0 && (
        <EmptyState
          icon={ShoppingCart}
          title="Your cart is empty"
          description="Search products by ingredient in the shop."
          action={<Link to="/shop"><Button>Go to shop</Button></Link>}
        />
      )}

      {cart && cart.items.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            {cart.items.map((item) => (
              <Card key={item.id} className="flex gap-4 p-4">
                <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-neutral-50 dark:bg-neutral-800">
                  {item.product.imageUrl && (
                    <img src={item.product.imageUrl} alt="" className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-neutral-500">{item.product.brand}</p>
                  <Link to={`/shop/${item.product.id}`} className="text-sm font-medium text-neutral-900 hover:underline dark:text-neutral-100">
                    {item.product.name}
                  </Link>
                  <p className="text-xs text-neutral-500">
                    {formatPrice(item.product.price, item.product.currency)} each
                  </p>
                  {item.problem && <p className="mt-1 text-xs text-red-600">{item.problem}</p>}
                  <div className="mt-2 flex items-center gap-2">
                    <Button size="sm" variant="outline" icon={Minus} disabled={busy || item.quantity <= 1}
                      onClick={() => run(() => api.updateCartItem(item.id, item.quantity - 1))} aria-label="Decrease" />
                    <span className="w-6 text-center text-sm">{item.quantity}</span>
                    <Button size="sm" variant="outline" icon={Plus} disabled={busy || item.quantity >= Math.min(10, item.product.stock)}
                      onClick={() => run(() => api.updateCartItem(item.id, item.quantity + 1))} aria-label="Increase" />
                    <Button size="sm" variant="ghost" icon={Trash2} disabled={busy}
                      onClick={() => run(() => api.removeCartItem(item.id))}>
                      Remove
                    </Button>
                  </div>
                </div>
                <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {formatPrice(item.line_total, item.product.currency)}
                </p>
              </Card>
            ))}
          </div>

          <Card className="h-fit p-5">
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Checkout</h2>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
              {formatPrice(cart.subtotal, cart.currency)}
            </p>
            <p className="text-xs text-neutral-500">{cart.item_count} item(s) · delivery charges confirmed by phone</p>

            <form onSubmit={placeOrder} className="mt-4 space-y-3">
              <input className={inputClass} required minLength={2} placeholder="Full name" value={shipping.shipping_name} onChange={field('shipping_name')} />
              <input className={inputClass} required type="tel" minLength={7} maxLength={20} placeholder="Phone (e.g. 0300 1234567)" value={shipping.shipping_phone} onChange={field('shipping_phone')} />
              <textarea className={inputClass} required minLength={5} rows={2} placeholder="Delivery address" value={shipping.shipping_address} onChange={field('shipping_address')} />
              <input className={inputClass} required minLength={2} placeholder="City" value={shipping.shipping_city} onChange={field('shipping_city')} />
              <textarea className={inputClass} rows={2} placeholder="Notes (optional)" value={shipping.notes} onChange={field('notes')} />
              <p className="flex items-center gap-1.5 text-xs text-neutral-500">
                <Truck className="h-4 w-4" /> Payment: cash on delivery
              </p>
              <Button type="submit" className="w-full" loading={placing} disabled={!cart.can_checkout}>
                Place order
              </Button>
              {!cart.can_checkout && (
                <p className="text-xs text-red-600">Remove unavailable items before checking out.</p>
              )}
            </form>
          </Card>
        </div>
      )}
    </DashboardLayout>
  )
}
