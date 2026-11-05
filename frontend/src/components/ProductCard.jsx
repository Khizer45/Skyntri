import { AlertTriangle, ImageOff, ShoppingCart } from 'lucide-react'
import { Link } from 'react-router-dom'
import Button from './Button.jsx'
import Card from './Card.jsx'

export function formatPrice(value, currency = 'PKR') {
  const amount = Number(value || 0)
  return `${currency} ${amount.toLocaleString(undefined, {
    minimumFractionDigits: amount % 1 ? 2 : 0,
    maximumFractionDigits: 2,
  })}`
}

export function PriceSource({ product }) {
  return (
    <p className="text-[11px] text-neutral-400">
      {product.price_source ? `Source: ${product.price_source}` : 'Source not provided'}
      {product.priceCheckedAt ? ` · checked ${product.priceCheckedAt}` : ''}
      {product.price_is_stale && (
        <span className="ml-1 font-medium text-amber-600 dark:text-amber-400">
          · price may be outdated
        </span>
      )}
    </p>
  )
}

export default function ProductCard({ product, onAdd, adding }) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <Link to={`/shop/${product.id}`} className="block">
        <div className="flex aspect-[4/3] items-center justify-center bg-neutral-50 dark:bg-neutral-800/50">
          {product.imageUrl ? (
            <img src={product.imageUrl} alt={product.name} className="h-full w-full object-cover" />
          ) : (
            <ImageOff className="h-8 w-8 text-neutral-300" />
          )}
        </div>
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {product.brand} · {product.category}
            </p>
            <Link
              to={`/shop/${product.id}`}
              className="line-clamp-2 text-sm font-semibold text-neutral-900 hover:text-brand-700 dark:text-neutral-100"
            >
              {product.name}
            </Link>
          </div>
          {product.is_sponsored && (
            <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
              Sponsored
            </span>
          )}
        </div>

        {(product.matched_ingredients?.length > 0 || product.missing_ingredients?.length > 0) && (
          <div className="flex flex-wrap gap-1">
            {product.matched_ingredients.map((name) => (
              <span
                key={`m-${name}`}
                className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
              >
                ✓ {name}
              </span>
            ))}
            {product.missing_ingredients.map((name) => (
              <span
                key={`x-${name}`}
                className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] text-neutral-500 line-through dark:bg-neutral-800"
              >
                {name}
              </span>
            ))}
          </div>
        )}

        {product.why?.length > 0 && (
          <p className="text-xs text-neutral-600 dark:text-neutral-300">{product.why[0]}</p>
        )}

        {product.cautions?.length > 1 && (
          <p className="flex gap-1 text-[11px] text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            {product.cautions[0]}
          </p>
        )}

        <div className="mt-auto pt-2">
          <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
            {formatPrice(product.price, product.currency)}
            {product.size && (
              <span className="ml-1 text-xs font-normal text-neutral-500">/ {product.size}</span>
            )}
          </p>
          <PriceSource product={product} />
          <Button
            size="sm"
            icon={ShoppingCart}
            className="mt-3 w-full"
            disabled={!product.in_stock}
            loading={adding}
            onClick={() => onAdd?.(product)}
          >
            {product.in_stock ? 'Add to cart' : 'Out of stock'}
          </Button>
        </div>
      </div>
    </Card>
  )
}
