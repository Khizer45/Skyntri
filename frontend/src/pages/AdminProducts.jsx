import { ImagePlus, Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import Modal from '../components/Modal.jsx'
import { formatPrice } from '../components/ProductCard.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

const inputClass =
  'w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100'

const EMPTY = {
  name: '',
  brand: '',
  category: 'Cleanser',
  description: '',
  size: '',
  ingredients: '',
  skin_types: [],
  concerns: '',
  price: '',
  currency: 'PKR',
  price_source: '',
  price_checked_at: new Date().toISOString().slice(0, 10),
  stock: 0,
  is_active: true,
  is_sponsored: false,
}

function toForm(p) {
  return {
    name: p.name,
    brand: p.brand,
    category: p.category,
    description: p.description || '',
    size: p.size || '',
    ingredients: p.ingredients.join(', '),
    skin_types: p.skin_types,
    concerns: p.concerns.join(', '),
    price: p.price,
    currency: p.currency,
    price_source: p.price_source || '',
    price_checked_at: p.price_checked_at ? p.price_checked_at.slice(0, 10) : '',
    stock: p.stock,
    is_active: p.is_active,
    is_sponsored: p.is_sponsored,
  }
}

function toPayload(f) {
  return {
    ...f,
    price: Number(f.price),
    stock: Number(f.stock),
    description: f.description || null,
    size: f.size || null,
    price_source: f.price_source || null,
    price_checked_at: f.price_checked_at ? new Date(f.price_checked_at).toISOString() : null,
    concerns: f.concerns.split(',').map((s) => s.trim()).filter(Boolean),
  }
}

function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300">{label}</span>
      {children}
      {hint && <span className="mt-0.5 block text-[11px] text-neutral-400">{hint}</span>}
    </label>
  )
}

export default function AdminProducts() {
  const [products, setProducts] = useState(null)
  const [meta, setMeta] = useState({ categories: [], skin_types: [] })
  const [editing, setEditing] = useState(null) // null | 'new' | product
  const [form, setForm] = useState(EMPTY)
  const [imageFile, setImageFile] = useState(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const { showToast } = useToast()

  const load = () => api.adminListProducts().then(setProducts).catch((err) => showToast(err.message, 'error'))

  useEffect(() => {
    load()
    api.getProductMeta().then(setMeta).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const open = (product) => {
    setEditing(product || 'new')
    setForm(product ? toForm(product) : EMPTY)
    setImageFile(null)
  }

  const set = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const toggleSkinType = (t) =>
    setForm((f) => ({
      ...f,
      skin_types: f.skin_types.includes(t) ? f.skin_types.filter((x) => x !== t) : [...f.skin_types, t],
    }))

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      let saved =
        editing === 'new'
          ? await api.adminCreateProduct(toPayload(form))
          : await api.adminUpdateProduct(editing.id, toPayload(form))
      if (imageFile) {
        saved = await api.adminUploadProductImage(saved.id, imageFile)
      }
      showToast('Product saved.', 'success')
      setEditing(null)
      load()
    } catch (err) {
      showToast(err.message || 'Could not save the product.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    try {
      await api.adminDeleteProduct(deleting.id)
      showToast('Product deleted.', 'success')
      setDeleting(null)
      load()
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  return (
    <AdminLayout title="Products">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          Add products with their full ingredient list, real price and where the price came from.
        </p>
        <Button icon={Plus} onClick={() => open(null)}>Add product</Button>
      </div>

      {!products && <Spinner label="Loading products…" />}
      {products && products.length === 0 && (
        <EmptyState icon={ImagePlus} title="No products yet" description="Add your first product." />
      )}

      {products && products.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-800">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {products.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 shrink-0 overflow-hidden rounded bg-neutral-100 dark:bg-neutral-800">
                        {p.imageUrl && <img src={p.imageUrl} alt="" className="h-full w-full object-cover" />}
                      </div>
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-neutral-100">{p.name}</p>
                        <p className="text-xs text-neutral-500">{p.brand} · {p.ingredients.length} ingredients</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-neutral-600 dark:text-neutral-300">{p.category}</td>
                  <td className="px-4 py-3">
                    {formatPrice(p.price, p.currency)}
                    {p.price_is_stale && <p className="text-[11px] text-amber-600">price needs re-checking</p>}
                  </td>
                  <td className="px-4 py-3">{p.stock}</td>
                  <td className="px-4 py-3 text-xs">
                    {p.is_active ? 'Active' : 'Hidden'}{p.is_sponsored ? ' · Sponsored' : ''}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" icon={Pencil} onClick={() => open(p)}>Edit</Button>
                      <Button size="sm" variant="ghost" icon={Trash2} onClick={() => setDeleting(p)}>Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal wide open={!!editing} onClose={() => setEditing(null)} title={editing === 'new' ? 'Add product' : 'Edit product'}>
        <form onSubmit={save} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Name"><input className={inputClass} required value={form.name} onChange={set('name')} /></Field>
            <Field label="Brand"><input className={inputClass} required value={form.brand} onChange={set('brand')} /></Field>
            <Field label="Category">
              <select className={inputClass} value={form.category} onChange={set('category')}>
                {(meta.categories.length ? meta.categories : ['Cleanser']).map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Size"><input className={inputClass} placeholder="e.g. 100 ml" value={form.size} onChange={set('size')} /></Field>
          </div>

          <Field label="Full ingredient list" hint="Comma separated, as printed on the label (INCI). Used for ingredient search.">
            <textarea className={inputClass} rows={3} required value={form.ingredients} onChange={set('ingredients')} />
          </Field>

          <Field label="Description"><textarea className={inputClass} rows={2} value={form.description} onChange={set('description')} /></Field>

          <div>
            <span className="mb-1 block text-xs font-medium text-neutral-600 dark:text-neutral-300">Suitable skin types</span>
            <div className="flex flex-wrap gap-3 text-sm">
              {meta.skin_types.map((t) => (
                <label key={t} className="flex items-center gap-1.5">
                  <input type="checkbox" checked={form.skin_types.includes(t)} onChange={() => toggleSkinType(t)} /> {t}
                </label>
              ))}
            </div>
          </div>

          <Field label="Concerns it targets" hint="Comma separated, e.g. Acne, Dark Spots, Dry Skin. Do not list diseases.">
            <input className={inputClass} value={form.concerns} onChange={set('concerns')} />
          </Field>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field label="Price"><input className={inputClass} type="number" min="0.01" step="0.01" required value={form.price} onChange={set('price')} /></Field>
            <Field label="Currency"><input className={inputClass} maxLength={3} required value={form.currency} onChange={set('currency')} /></Field>
            <Field label="Stock"><input className={inputClass} type="number" min="0" required value={form.stock} onChange={set('stock')} /></Field>
            <Field label="Price checked on"><input className={inputClass} type="date" value={form.price_checked_at} onChange={set('price_checked_at')} /></Field>
          </div>

          <Field label="Price source" hint="Where the price came from (store name or link). Shown to customers.">
            <input className={inputClass} value={form.price_source} onChange={set('price_source')} />
          </Field>

          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Visible in shop</label>
            <label className="flex items-center gap-1.5"><input type="checkbox" checked={form.is_sponsored} onChange={set('is_sponsored')} /> Sponsored (shown with a label)</label>
          </div>

          <Field label="Product image (JPEG/PNG/WebP)">
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setImageFile(e.target.files?.[0] || null)} className="text-sm" />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button type="submit" loading={saving}>Save</Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Delete product?"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleting(null)}>Cancel</Button>
            <Button variant="danger" onClick={remove}>Delete</Button>
          </>
        }
      >
        {deleting && <p>“{deleting.name}” will be removed from the shop and from carts. Past orders keep their details.</p>}
      </Modal>
    </AdminLayout>
  )
}
