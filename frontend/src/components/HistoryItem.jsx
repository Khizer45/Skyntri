import { ChevronRight } from 'lucide-react'

export default function HistoryItem({ type, result, date, status, confidence, onView }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-neutral-100 px-4 py-3.5 last:border-0 dark:border-neutral-800">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">{result}</p>
          {confidence != null && (
            <span className="rounded-full bg-brand-50 px-1.5 py-0.5 text-[11px] font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
              {confidence}%
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-neutral-400">
          {type} · {new Date(date).toLocaleDateString()}
        </p>
      </div>
      <span className="hidden shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 sm:inline-block">
        {status}
      </span>
      <button
        onClick={onView}
        className="flex shrink-0 items-center gap-0.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
      >
        View <ChevronRight className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
