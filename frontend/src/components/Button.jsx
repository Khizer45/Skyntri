import { Loader2 } from 'lucide-react'

const variants = {
  primary:
    'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-300 dark:disabled:bg-brand-900',
  secondary:
    'bg-neutral-100 text-neutral-800 hover:bg-neutral-200 dark:bg-panel-dark dark:text-neutral-200 dark:hover:bg-neutral-800',
  outline:
    'border border-neutral-300 text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-panel-dark',
  ghost:
    'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-panel-dark',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
}

const sizes = {
  sm: 'text-xs px-2.5 py-1.5 rounded-md gap-1.5',
  md: 'text-sm px-3.5 py-2 rounded-lg gap-2',
  lg: 'text-sm px-4 py-2.5 rounded-lg gap-2',
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon: Icon,
  className = '',
  disabled,
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1 dark:focus-visible:ring-offset-surface-dark ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        Icon && <Icon className="h-4 w-4" />
      )}
      {children}
    </button>
  )
}
