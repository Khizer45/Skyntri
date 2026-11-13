import { AlertTriangle, Camera, CheckCircle2, Info, ScanFace, Sparkles, Stethoscope, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
  const [abstention, setAbstention] = useState(null)
  const [track, setTrack] = useState('facial_concerns')
  const [tracks, setTracks] = useState(api.ANALYSIS_TRACKS)
  const { showToast } = useToast()

  useEffect(() => {
    api.getAnalysisTracks().then((list) => {
      setTracks(list)
      const firstAvailable = list.find((t) => t.available)
      if (firstAvailable) setTrack(firstAvailable.id)
    })
  }, [])

  const handleAnalyze = async () => {
    if (!file) return
    setAnalyzing(true)
    setError('')
    setAbstention(null)

    try {
      const res = await api.analyzeSkin(file, track)
      setResult(res)
      showToast('Skin analysis complete.', 'success')
    } catch (err) {
      if (err.status === 422 && err.code) {
        // The image was not analyzed (not skin, poor quality, uncertain,
        // or the analysis type is not available). No labels are shown.
        setResult(null)
        setAbstention({
          code: err.code,
          message: err.message,
          guidance: err.guidance || [],
        })
      } else {
        setError(err.message || 'Analysis failed. Please try again.')
      }
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <DashboardLayout title="Skin analysis" subtitle="AI estimate of visible skin concerns, not a diagnosis">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-4 flex items-center gap-2">
            <ScanFace className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
              Upload a skin image
            </h2>
          </div>

          <fieldset className="mb-4">
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-400">
              What would you like to analyze?
            </legend>
            <div className="space-y-2">
              {tracks.map((option) => (
                <label
                  key={option.id}
                  className={`flex gap-3 rounded-lg border p-3 text-sm ${
                    option.available
                      ? 'cursor-pointer border-neutral-200 dark:border-neutral-700'
                      : 'cursor-not-allowed border-dashed border-neutral-200 opacity-70 dark:border-neutral-700'
                  } ${
                    track === option.id
                      ? 'border-brand-500 bg-brand-50/60 dark:bg-brand-900/20'
                      : ''
                  }`}
                >
                  <input
                    type="radio"
                    name="analysis-track"
                    value={option.id}
                    checked={track === option.id}
                    disabled={!option.available}
                    onChange={() => setTrack(option.id)}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium text-neutral-800 dark:text-neutral-100">
                      {option.label}
                      {!option.available && (
                        <span className="ml-2 rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
                          Not available yet
                        </span>
                      )}
                    </span>
                    <span className="mt-0.5 block text-xs text-neutral-500 dark:text-neutral-400">
                      {option.description}
                    </span>
                    {!option.available && option.reason && (
                      <span className="mt-1 block text-[11px] text-amber-700 dark:text-amber-300">{option.reason}</span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <ImageUploader
            label="Take or upload a clear photo"
            hint="Front-facing or close-up, good light, in focus. JPEG/PNG/WebP up to 10MB"
            onChange={(f) => {
              setFile(f)
              setResult(null)
              setError('')
              setAbstention(null)
            }}
          />

          <div className="mt-3 flex gap-2 rounded-lg bg-neutral-50 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-800/60 dark:text-neutral-300">
            <Camera className="mt-0.5 h-4 w-4 shrink-0" />
            <p>
              Use natural, even light without filters. Keep the skin in focus and
              make it fill most of the photo. Photos that are not skin, or are too
              dark or blurry, will not be analyzed.
            </p>
          </div>

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

          {!analyzing && abstention && (
            <Card className="p-5">
              <div className="flex gap-3">
                <Info className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    {abstention.code === 'track_not_available' || abstention.code === 'model_not_installed'
                      ? 'Not available yet'
                      : 'This image was not analyzed'}
                  </h3>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
                    {abstention.message}
                  </p>
                  {abstention.guidance.length > 0 && (
                    <ul className="mt-3 space-y-1.5 text-sm text-neutral-600 dark:text-neutral-300">
                      {abstention.guidance.map((tip) => (
                        <li key={tip} className="flex gap-2">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
                          {tip}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </Card>
          )}

          {!analyzing && !result && !abstention && (
            <Card className="flex h-full min-h-64 items-center justify-center p-8 text-center">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Upload an image and run analysis to see your results here.
              </p>
            </Card>
          )}

          {!analyzing && result && (
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-400">
              {result.trackLabel} · AI estimate, not a diagnosis
            </p>
          )}

          {!analyzing && result?.referral && (
            <div className="mb-3 flex gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-200">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <p>{result.summary}</p>
            </div>
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

            {result.track === 'facial_concerns' && (
              <Link
                to="/shop"
                className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
              >
                <Sparkles className="h-4 w-4" /> See affordable products with these ingredients
              </Link>
            )}

            <Link
              to="/doctors"
              className="mt-3 flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
            >
              <Stethoscope className="h-4 w-4" /> Want a doctor's opinion? Book a dermatologist
            </Link>

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