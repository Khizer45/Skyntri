import Card from './Card.jsx'

const severityStyles = {
  Low: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
  Moderate: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  Medium: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  High: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

export default function PredictionCard({
  conditions = [],
  confidence,
  severity,
  explanation,
}) {
  const safeConfidence =
    typeof confidence === 'number'
      ? Math.min(100, Math.max(0, confidence))
      : null

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
            Detected skin patterns
          </p>

          {conditions.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {conditions.map((condition) => (
                <span
                  key={condition}
                  className="rounded-lg bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
                >
                  {condition}
                </span>
              ))}
            </div>
          ) : (
            <h3 className="mt-1 text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              No supported facial concern detected
            </h3>
          )}
        </div>

        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            severityStyles[severity] || severityStyles.Low
          }`}
        >
          {severity} severity
        </span>
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
          <span>Confidence</span>

          <span className="font-medium text-neutral-700 dark:text-neutral-200">
            {safeConfidence !== null
              ? `${Math.round(safeConfidence)}%`
              : '—'}
          </span>
        </div>

        <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-500"
            style={{
              width:
                safeConfidence !== null
                  ? `${safeConfidence}%`
                  : '0%',
            }}
          />
        </div>
      </div>

      {explanation && (
        <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-300">
          {explanation}
        </p>
      )}
    </Card>
  )
}