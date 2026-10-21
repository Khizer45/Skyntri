import { Loader2 } from 'lucide-react'

export function Spinner({ label = 'Loading…', className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2.5 py-10 text-center ${className}`}>
      <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
      <p className="text-sm text-neutral-500 dark:text-neutral-400">{label}</p>
    </div>
  )
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`animate-pulse rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-panel-dark ${className}`}>
      <div className="h-3 w-24 rounded bg-neutral-200 dark:bg-neutral-700" />
      <div className="mt-3 h-5 w-40 rounded bg-neutral-200 dark:bg-neutral-700" />
      <div className="mt-4 h-2 w-full rounded bg-neutral-100 dark:bg-neutral-800" />
      <div className="mt-2 h-2 w-3/4 rounded bg-neutral-100 dark:bg-neutral-800" />
    </div>
  )
}

export default function LoadingState({ label, className }) {
  return <Spinner label={label} className={className} />
}
