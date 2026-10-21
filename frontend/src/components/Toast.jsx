import { CheckCircle2, Info, X, XCircle } from 'lucide-react'

const styles = {
  success: {
    icon: CheckCircle2,
    classes: 'border-brand-200 bg-brand-50 text-brand-800 dark:border-brand-800 dark:bg-brand-900/40 dark:text-brand-200',
  },
  error: {
    icon: XCircle,
    classes: 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-900/30 dark:text-red-300',
  },
  info: {
    icon: Info,
    classes: 'border-neutral-200 bg-white text-neutral-700 dark:border-neutral-800 dark:bg-panel-dark dark:text-neutral-200',
  },
}

export default function Toast({ message, type = 'info', onClose }) {
  const { icon: Icon, classes } = styles[type] || styles.info
  return (
    <div
      role="status"
      className={`flex items-start gap-2 rounded-lg border px-3.5 py-3 text-sm shadow-subtle animate-in fade-in slide-in-from-bottom-2 duration-200 ${classes}`}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <p className="flex-1">{message}</p>
      <button onClick={onClose} aria-label="Dismiss notification" className="shrink-0 opacity-60 hover:opacity-100">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
