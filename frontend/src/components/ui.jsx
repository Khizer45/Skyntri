// Small shared building blocks used across pages.

const TONES = {
  neutral: 'bg-neutral-100 text-neutral-700 dark:bg-white/10 dark:text-neutral-300',
  green: 'bg-brand-100 text-brand-800 dark:bg-brand-900/50 dark:text-brand-200',
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  red: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200',
  blue: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
}

const STATUS_TONE = {
  requested: 'amber', pending: 'amber', unpaid: 'amber', draft: 'amber', refund_due: 'amber', created: 'amber',
  confirmed: 'blue', shipped: 'blue', running: 'blue',
  completed: 'green', approved: 'green', paid: 'green', published: 'green', delivered: 'green', ok: 'green',
  succeeded: 'green',
  cancelled: 'neutral', rejected: 'red', suspended: 'red', no_show: 'red', failed: 'red', refunded: 'neutral',
  not_required: 'neutral',
}

const STATUS_LABEL = {
  no_show: 'No-show', refund_due: 'Refund due', not_required: 'Free', ok: 'Done', in_person: 'In person',
}

export function label(value) {
  if (!value) return ''
  return STATUS_LABEL[value] || value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ')
}

export function Badge({ tone = 'neutral', children }) {
  return <span className={`badge ${TONES[tone] || TONES.neutral}`}>{children}</span>
}

export function StatusBadge({ status }) {
  return <Badge tone={STATUS_TONE[status] || 'neutral'}>{label(status)}</Badge>
}

export function Field({ label: text, hint, error, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      {text && <span className="label">{text}</span>}
      {children}
      {error ? <span className="mt-1 block text-xs text-red-600 dark:text-red-400">{error}</span> : hint && <span className="hint block">{hint}</span>}
    </label>
  )
}

export function Alert({ tone = 'red', children, className = '' }) {
  const styles = {
    red: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-200',
    amber: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-100',
    green: 'border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-800 dark:bg-brand-900/30 dark:text-brand-100',
    neutral: 'border-neutral-200 bg-neutral-50 text-neutral-700 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300',
  }
  return (
    <div role={tone === 'red' ? 'alert' : undefined} className={`rounded-lg border px-3 py-2.5 text-sm ${styles[tone]} ${className}`}>
      {children}
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="no-scrollbar -mx-1 mb-5 flex gap-1 overflow-x-auto border-b border-neutral-200 px-1 dark:border-white/10" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={value === tab.id}
          onClick={() => onChange(tab.id)}
          className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
            value === tab.id
              ? 'border-neutral-900 text-neutral-900 dark:border-white dark:text-white'
              : 'border-transparent text-neutral-500 hover:text-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-200'
          }`}
        >
          {tab.label}
          {tab.count > 0 && <span className="ml-1.5 rounded-full bg-accent-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">{tab.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Section({ title, description, action, children, className = '' }) {
  return (
    <section className={className}>
      {(title || action) && (
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold text-neutral-900 dark:text-white">{title}</h2>}
            {description && <p className="muted mt-0.5 text-sm">{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="rounded-xl border border-dashed border-neutral-300 px-6 py-10 text-center dark:border-white/15">
      <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100">{title}</p>
      {children && <div className="muted mx-auto mt-1 max-w-md text-sm">{children}</div>}
    </div>
  )
}

export function Toggle({ checked, onChange, disabled, label: text }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={text}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
        checked ? 'bg-brand-600' : 'bg-neutral-300 dark:bg-white/20'
      }`}
    >
      <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-[1.375rem]' : 'translate-x-0.5'}`} />
    </button>
  )
}

export function money(amount, currency) {
  if (amount === null || amount === undefined) return ''
  const value = Number(amount)
  return `${currency || ''} ${value.toLocaleString(undefined, { minimumFractionDigits: value % 1 ? 2 : 0, maximumFractionDigits: 2 })}`.trim()
}

export function dateTime(value, timeZone) {
  if (!value) return ''
  return new Date(value).toLocaleString(undefined, {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone,
  })
}

export function dateOnly(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}
