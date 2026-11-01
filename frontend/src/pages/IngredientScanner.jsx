import { AlertOctagon, AlertTriangle, CheckCircle2, FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import ImageUploader from '../components/ImageUploader.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import * as api from '../services/api.js'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

const statusConfig = {
  Beneficial: { icon: CheckCircle2, classes: 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/30' },
  Caution: { icon: AlertTriangle, classes: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30' },
  'Potential Irritant': { icon: AlertOctagon, classes: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30' },
}

export default function IngredientScanner() {
  const [file, setFile] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState(null)
  const { showToast } = useToast()

  const handleScan = async () => {
    if (!file) return
    setScanning(true)

    try {
      const res = await api.scanIngredients(file)
      setResult(res)
      showToast('Ingredient scan complete.', 'success')
    } catch (err) {
      showToast(err.message || 'Scan failed. Please try again.', 'error')
    } finally {
      setScanning(false)
    }
  }

  return (
    <DashboardLayout title="Ingredient Scanner">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-4 flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Upload a product label
            </h2>
          </div>

          <ImageUploader
            label="Upload a photo of the ingredient label"
            hint="Make sure the ingredient text is clearly visible"
            onChange={(f) => {
              setFile(f)
              setResult(null)
            }}
          />

          <Button
            onClick={handleScan}
            disabled={!file}
            loading={scanning}
            className="mt-4 w-full"
          >
            Scan Ingredients
          </Button>
        </Card>

        {result && (
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Product summary
            </h3>

            <div className="mt-3 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
              <Summary value={result.summary.total} label="Detected" />
              <Summary value={result.summary.beneficial} label="Beneficial" positive />
              <Summary value={result.summary.caution} label="Need caution" warning />
              <Summary
                value={result.safety_score ?? '—'}
                label={result.safety_label || 'Safety'}
              />
            </div>

            {result.unmatched?.length > 0 && (
              <p className="mt-4 text-xs text-neutral-500 dark:text-neutral-400">
                {result.unmatched.length} ingredient name(s) could not be confidently matched.
              </p>
            )}
          </Card>
        )}
      </div>

      {scanning && (
        <Card className="mt-6 p-5">
          <Spinner label="Reading ingredient list (OCR)…" />
        </Card>
      )}

      {!scanning && result && (
        <section className="mt-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Detected ingredients
            </h3>
            {result.ingredients.some((i) => i.status === 'Beneficial') && (
              <Link
                to={`/shop?ingredients=${encodeURIComponent(
                  result.ingredients
                    .filter((i) => i.status === 'Beneficial')
                    .slice(0, 5)
                    .map((i) => i.name)
                    .join(', ')
                )}`}
                className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300"
              >
                Find products with these beneficial ingredients →
              </Link>
            )}
          </div>

          {result.ingredients.length === 0 ? (
            <Card className="p-5 text-sm text-neutral-500">
              No database-matched ingredients were found.
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {result.ingredients.map((ing, index) => {
                const cfg = statusConfig[ing.status] || statusConfig.Caution
                const Icon = cfg.icon

                return (
                  <Card key={`${ing.name}-${index}`} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
                          {ing.name}
                        </p>
                        {ing.function && (
                          <p className="text-xs text-neutral-500 dark:text-neutral-400">
                            Function: {ing.function}
                          </p>
                        )}
                      </div>

                      <span className={`flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium ${cfg.classes}`}>
                        <Icon className="h-3 w-3" />
                        {ing.status}
                      </span>
                    </div>

                    <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                      {ing.note}
                    </p>

                    {ing.when_to_use && (
                      <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                        Use: {ing.when_to_use}
                      </p>
                    )}
                  </Card>
                )
              })}
            </div>
          )}
        </section>
      )}
    </DashboardLayout>
  )
}

function Summary({ value, label, positive, warning }) {
  const valueClass = positive
    ? 'text-brand-600 dark:text-brand-400'
    : warning
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-neutral-900 dark:text-neutral-100'

  return (
    <div>
      <p className={`text-xl font-semibold ${valueClass}`}>{value}</p>
      <p className="text-xs text-neutral-500 dark:text-neutral-400">{label}</p>
    </div>
  )
}
