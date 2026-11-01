import { AlertTriangle, ArrowLeft, ImageOff, ShoppingCart } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { PriceSource, formatPrice } from '../components/ProductCard.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

export default function ProductDetail() {
  const { productId } = useParams()
  const [product, setProduct] = useState(null)
  const [error, setError] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const { showToast } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    api.getProduct(productId).then(setProduct).catch((err) => setError(err.message || 'Product not found.'))
  }, [productId])

  const add = async () => {
    setAdding(true)
    try {
      await api.addToCart(product.id, quantity)
      showToast('Added to cart.', 'success')
      navigate('/cart')
    } catch (err) {
      showToast(err.message || 'Could not add to cart.', 'error')
    } finally {
      setAdding(false)
    }
  }

  return (
    <DashboardLayout title="Product">
      <Link to="/shop" className="mb-4 inline-flex items-center gap-1 text-sm text-brand-700 hover:underline dark:text-brand-300">
        <ArrowLeft className="h-4 w-4" /> Back to shop
      </Link>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!product && !error && <Spinner label="Loading product…" />}

      {product && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="flex aspect-square items-center justify-center overflow-hidden">
            {product.imageUrl ? (
              <img src={product.imageUrl} alt={product.name} className="h-full w-full object-cover" />
            ) : (
              <ImageOff className="h-10 w-10 text-neutral-300" />
            )}
          </Card>

          <Card className="space-y-4 p-6">
            <div>
              <p className="text-sm text-neutral-500">{product.brand} · {product.category}{product.size ? ` · ${product.size}` : ''}</p>
              <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{product.name}</h1>
              {product.is_sponsored && (
                <span className="mt-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-800">
                  Sponsored
                </span>
              )}
            </div>

            <div>
              <p className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
                {formatPrice(product.price, product.currency)}
              </p>
              <PriceSource product={product} />
            </div>

            {product.description && (
              <p className="text-sm text-neutral-600 dark:text-neutral-300">{product.description}</p>
            )}

            {(product.skin_types.length > 0 || product.concerns.length > 0) && (
              <div className="flex flex-wrap gap-1.5 text-xs">
                {product.skin_types.map((t) => (
                  <span key={t} className="rounded-full bg-neutral-100 px-2 py-0.5 dark:bg-neutral-800">{t} skin</span>
                ))}
                {product.concerns.map((c) => (
                  <span key={c} className="rounded-full bg-brand-50 px-2 py-0.5 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">{c}</span>
                ))}
              </div>
            )}

            <div>
              <h2 className="mb-1 text-sm font-semibold text-neutral-800 dark:text-neutral-100">Ingredients</h2>
              <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-300">
                {product.ingredients.length ? product.ingredients.join(', ') : 'Not provided.'}
              </p>
            </div>

            <ul className="space-y-1">
              {product.cautions.map((c) => (
                <li key={c} className="flex gap-1.5 text-xs text-amber-700 dark:text-amber-300">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {c}
                </li>
              ))}
            </ul>

            <div className="flex items-center gap-3">
              <input
                type="number"
                min="1"
                max={Math.max(1, Math.min(10, product.stock))}
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
                className="w-20 rounded-lg border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-panel-dark"
              />
              <Button icon={ShoppingCart} onClick={add} loading={adding} disabled={!product.in_stock}>
                {product.in_stock ? 'Add to cart' : 'Out of stock'}
              </Button>
            </div>
            <p className="text-[11px] text-neutral-400">
              Cosmetic products do not treat skin diseases. For a worrying or changing spot, see a doctor first.
            </p>
          </Card>
        </div>
      )}
    </DashboardLayout>
  )
}
