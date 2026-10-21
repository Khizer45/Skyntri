export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2.5 rounded-xl border border-dashed border-neutral-200 px-6 py-12 text-center dark:border-neutral-800">
      {Icon && (
        <div className="rounded-full bg-neutral-100 p-2.5 dark:bg-neutral-800">
          <Icon className="h-5 w-5 text-neutral-400" />
        </div>
      )}
      <p className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{title}</p>
      {description && <p className="max-w-xs text-xs text-neutral-500 dark:text-neutral-400">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
