import { TrendingUp } from 'lucide-react'
import Card from './Card.jsx'

export default function ProgressCard({ status, score, observations, timeline }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">Progress</p>
          <div className="mt-1 flex items-center gap-2">
            <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{status}</h3>
            <TrendingUp className="h-4 w-4 text-brand-500" />
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-brand-600 dark:text-brand-400">{score}%</p>
          <p className="text-xs text-neutral-400">improvement score</p>
        </div>
      </div>

      {timeline?.length > 0 && (
        <div className="mt-5 flex items-end gap-2.5">
          {timeline.map((point) => (
            <div key={point.label} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="flex h-24 w-full items-end rounded-md bg-neutral-100 dark:bg-neutral-800">
                <div
                  className="w-full rounded-md bg-brand-500 transition-all duration-500"
                  style={{ height: `${point.score}%` }}
                />
              </div>
              <span className="text-[11px] text-neutral-400">{point.label}</span>
            </div>
          ))}
        </div>
      )}

      {observations?.length > 0 && (
        <ul className="mt-5 space-y-1.5 border-t border-neutral-100 pt-4 text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-300">
          {observations.map((obs) => (
            <li key={obs} className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
              {obs}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
