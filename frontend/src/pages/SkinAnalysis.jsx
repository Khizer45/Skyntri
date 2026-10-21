import { AlertTriangle, CheckCircle2, ScanFace, Sparkles, XCircle } from 'lucide-react'
import { useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import ImageUploader from '../components/ImageUploader.jsx'
import PredictionCard from '../components/PredictionCard.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import * as api from '../services/api.js'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

export default function SkinAnalysis() {
  const [file, setFile] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const { showToast } = useToast()

  const handleAnalyze = async () => {
    if (!file) return
    setAnalyzing(true)
    setError('')

    try {
      const res = await api.analyzeSkin(file)
      setResult(res)
      showToast('Skin analysis complete.', 'success')
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <DashboardLayout title="Skin Analysis">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-4 flex items-center gap-2">
            <ScanFace className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Upload a skin image
            </h2>
          </div>

          <ImageUploader
            label="Upload a clear photo of the affected area"
            hint="Good lighting, in-focus, JPEG/PNG/WebP up to 10MB"
            onChange={(f) => {
              setFile(f)
              setResult(null)
              setError('')
            }}
          />

          {error && (
            <p className="mt-3 text-xs text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <Button
            onClick={handleAnalyze}
            disabled={!file}
            loading={analyzing}
            className="mt-4 w-full"
          >
            Analyze Skin
          </Button>
        </Card>

        <div>
          {analyzing && (
            <Card className="p-5">
              <Spinner label="Analyzing your skin image…" />
            </Card>
          )}

          {!analyzing && !result && (
            <Card className="flex h-full min-h-64 items-center justify-center p-8 text-center">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Upload an image and run analysis to see your results here.
              </p>
            </Card>
          )}

          {!analyzing && result && (
            <PredictionCard
              conditions={result.conditions}
              confidence={result.confidence}
              severity={result.severity}
              explanation={result.explanation}
            />
          )}
        </div>
      </div>

      {!analyzing && result && (
        <section className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Recommended care
            </h3>
          </div>

          <Card className="p-5">
            <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-800 dark:bg-brand-900/20 dark:text-brand-200">
              {result.explanation}
            </p>

            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <RecommendationList
                title="Skincare"
                items={result.recommendations?.skincare}
              />

              <RecommendationList
                title="Ingredients"
                items={result.recommendations?.ingredients}
              />

              <RecommendationList
                title="Sun protection"
                items={result.recommendations?.sun_protection}
                icon={<CheckCircle2 className="h-4 w-4" />}
              />

              <RecommendationList
                title="Lifestyle"
                items={result.recommendations?.lifestyle}
                icon={<CheckCircle2 className="h-4 w-4" />}
              />

              <RecommendationList
                title="Things to avoid"
                items={result.recommendations?.avoid}
                danger
                icon={<XCircle className="h-4 w-4" />}
              />
            </div>

            {result.disclaimer && (
              <div className="mt-5 flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <p>{result.disclaimer}</p>
              </div>
            )}
          </Card>
        </section>
      )}
    </DashboardLayout>
  )
}

function RecommendationList({ title, items = [], danger = false, icon }) {
  return (
    <div>
      <h4
        className={`flex items-center gap-1.5 text-sm font-medium ${
          danger
            ? 'text-red-600 dark:text-red-400'
            : 'text-neutral-800 dark:text-neutral-100'
        }`}
      >
        {icon}
        {title}
      </h4>

      {items.length > 0 ? (
        <ul className="mt-2 space-y-1.5 text-sm text-neutral-600 dark:text-neutral-300">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-neutral-400">
          No additional guidance.
        </p>
      )}
    </div>
  )
}