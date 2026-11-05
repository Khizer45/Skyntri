import { FlaskConical, Search, ShoppingBag, ShoppingCart, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import ProductCard from '../components/ProductCard.jsx'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const inputClass =
  'w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100'

const QUICK_INGREDIENTS = [
  'Niacinamide',
  'Salicylic Acid',
  'Hyaluronic Acid',
  'Ceramides',
  'Vitamin C',
  'Azelaic Acid',
  'Retinol',
  'Zinc Oxide',
]

export default function Shop() {
  const [params, setParams] = useSearchParams()
  const [meta, setMeta] = useState({ categories: [], skin_types: [], disclaimer: '' })
  const [form, setForm] = useState({
    q: params.get('q') || '',
    ingredients: params.get('ingredients') || '',
    avoid: params.get('avoid') || '',
    match: params.get('match') || 'any',
    category: params.get('category') || '',
    skin_type: params.get('skin_type') || '',
    max_price: params.get('max_price') || '',
    in_stock: params.get('in_stock') === 'true',
    sort: params.get('sort') || 'relevance',
  })
  const [results, setResults] = useState(null)
  const [recommended, setRecommended] = useState(null)
  const [loading, setLoading] = useState(false)
  const [addingId, setAddingId] = useState(null)
  const [cartCount, setCartCount] = useState(0)
  const { showToast } = useToast()

  const runSearch = useCallback(async (values) => {
    setLoading(true)
    try {
      setResults(await api.searchProducts(values))
    } catch (err) {
      showToast(err.message || 'Search failed.', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    api.getProductMeta().then(setMeta).catch(() => {})
    api.getRecommendedProducts().then(setRecommended).catch(() => setRecommended(null))
    api.getCart().then((c) => setCartCount(c.item_count)).catch(() => {})
    runSearch(form)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const update = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const submit = (e) => {
    e?.preventDefault()
    const clean = Object.fromEntries(
      Object.entries(form).filter(([, v]) => v !== '' && v !== false)
    )
    setParams(clean)
    runSearch(form)
  }

  const addIngredient = (name) => {
    const current = form.ingredients
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    if (current.some((c) => c.toLowerCase() === name.toLowerCase())) return
    const next = { ...form, ingredients: [...current, name].join(', ') }
    setForm(next)
    runSearch(next)
  }

  const addToCart = async (product) => {
    setAddingId(product.id)
    try {
      const cart = await api.addToCart(product.id, 1)
      setCartCount(cart.item_count)
      showToast(`${product.name} added to cart.`, 'success')
    } catch (err) {
      showToast(err.message || 'Could not add to cart.', 'error')
    } finally {
      setAddingId(null)
    }
  }

  return (
    <DashboardLayout title="Shop">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          Find affordable skincare by the ingredients it contains.
        </p>
        <Link to="/cart">
          <Button variant="outline" icon={ShoppingCart}>
            Cart {cartCount > 0 && `(${cartCount})`}
          </Button>
        </Link>
      </div>

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300">
                Ingredients you want (comma separated)
              </label>
              <input
                className={inputClass}
                value={form.ingredients}
                onChange={update('ingredients')}
                placeholder="e.g. niacinamide, salicylic acid"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300">
                Ingredients to avoid
              </label>
              <input
                className={inputClass}
                value={form.avoid}
                onChange={update('avoid')}
                placeholder="e.g. fragrance, alcohol denat"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {QUICK_INGREDIENTS.map((name) => (
              <button
                type="button"
                key={name}
                onClick={() => addIngredient(name)}
                className="rounded-full border border-neutral-200 px-2.5 py-1 text-xs text-neutral-600 hover:border-brand-400 hover:text-brand-700 dark:border-neutral-700 dark:text-neutral-300"
              >
                + {name}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <input className={`${inputClass} col-span-2`} value={form.q} onChange={update('q')} placeholder="Product or brand" />
            <select className={inputClass} value={form.category} onChange={update('category')}>
              <option value="">All categories</option>
              {meta.categories.map((c) => <option key={c}>{c}</option>)}
            </select>
            <select className={inputClass} value={form.skin_type} onChange={update('skin_type')}>
              <option value="">Any skin type</option>
              {meta.skin_types.map((c) => <option key={c}>{c}</option>)}
            </select>
            <input
              className={inputClass}
              type="number"
              min="1"
              value={form.max_price}
              onChange={update('max_price')}
              placeholder={`Max price (${meta.currency || 'PKR'})`}
            />
            <select className={inputClass} value={form.sort} onChange={update('sort')}>
              <option value="relevance">Best ingredient match</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
              <option value="newest">Newest</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-4 text-xs text-neutral-600 dark:text-neutral-300">
              <label className="flex items-center gap-1.5">
                <input type="checkbox" checked={form.match === 'all'} onChange={(e) => setForm((f) => ({ ...f, match: e.target.checked ? 'all' : 'any' }))} />
                Must contain all listed ingredients
              </label>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" checked={form.in_stock} onChange={update('in_stock')} />
                In stock only
              </label>
            </div>
            <Button type="submit" icon={Search} loading={loading}>
              Search
            </Button>
          </div>
        </form>
      </Card>

      {recommended?.items?.length > 0 && (
        <section className="mt-6">
          <div className="mb-2 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Suggested for your latest analysis ({recommended.based_on.join(', ')})
            </h2>
          </div>
          <p className="mb-3 text-xs text-neutral-500 dark:text-neutral-400">{recommended.message}</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {recommended.items.slice(0, 4).map((p) => (
              <ProductCard key={`rec-${p.id}`} product={p} onAdd={addToCart} adding={addingId === p.id} />
            ))}
          </div>
        </section>
      )}

      {recommended && !recommended.items?.length && recommended.message && (
        <p className="mt-4 flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <FlaskConical className="h-4 w-4" /> {recommended.message}
        </p>
      )}

      <section className="mt-6">
        {loading && !results && <Spinner label="Loading products…" />}

        {results && (
          <>
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
                {results.total} product{results.total === 1 ? '' : 's'}
              </h2>
              <p className="text-[11px] text-neutral-400">{results.ranking}</p>
            </div>

            {results.items.length === 0 ? (
              <EmptyState
                icon={ShoppingBag}
                title="No matching products"
                description="Try fewer ingredients, a higher budget, or turn off 'must contain all'."
              />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {results.items.map((p) => (
                  <ProductCard key={p.id} product={p} onAdd={addToCart} adding={addingId === p.id} />
                ))}
              </div>
            )}

            <p className="mt-6 rounded-lg bg-neutral-50 px-3 py-2 text-xs text-neutral-500 dark:bg-neutral-800/60 dark:text-neutral-400">
              {results.disclaimer}
            </p>
          </>
        )}
      </section>
    </DashboardLayout>
  )
}
