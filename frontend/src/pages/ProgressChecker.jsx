import { TrendingUp } from 'lucide-react'
import { useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import ImageUploader from '../components/ImageUploader.jsx'
import ProgressCard from '../components/ProgressCard.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import * as api from '../services/api.js'
import { useToast } from '../context/ToastContext.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

export default function ProgressChecker() {
  const [beforeFile, setBeforeFile] = useState(null)
  const [afterFile, setAfterFile] = useState(null)
  const [comparing, setComparing] = useState(false)
  const [result, setResult] = useState(null)
  const { showToast } = useToast()

  const handleCompare = async () => {
    if (!beforeFile || !afterFile) return
    setComparing(true)

    try {
      const res = await api.checkProgress(beforeFile, afterFile)
      setResult(res)
      showToast('Progress comparison complete.', 'success')
    } catch (err) {
      showToast(err.message || 'Comparison failed. Please try again.', 'error')
    } finally {
      setComparing(false)
    }
  }

  return (
    <DashboardLayout title="Progress Checker">
      <Card className="p-5">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Compare before & after images
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-medium text-neutral-500 dark:text-neutral-400">
              Before image
            </p>
            <ImageUploader
              label="Upload earlier photo"
              onChange={(f) => {
                setBeforeFile(f)
                setResult(null)
              }}
            />
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-neutral-500 dark:text-neutral-400">
              After image
            </p>
            <ImageUploader
              label="Upload recent photo"
              onChange={(f) => {
                setAfterFile(f)
                setResult(null)
              }}
            />
          </div>
        </div>

        <p className="mt-4 rounded-lg bg-neutral-50 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-800/60 dark:text-neutral-300">
          This is an approximate visual comparison, not a clinical measurement.
          For a fair comparison, take both photos in the same lighting, at the
          same distance and angle, without filters or make-up.
        </p>

        <Button
          onClick={handleCompare}
          disabled={!beforeFile || !afterFile}
          loading={comparing}
          className="mt-4 w-full sm:w-auto"
        >
          Compare Progress
        </Button>

        <p className="mt-3 text-xs text-neutral-400">
          This comparison is a visual estimate and does not constitute medical accuracy.
        </p>
      </Card>

      {comparing && (
        <Card className="mt-6 p-5">
          <Spinner label="Comparing images…" />
        </Card>
      )}

      {!comparing && result && (
        <div className="mt-6">
          <ProgressCard {...result} />
        </div>
      )}
    </DashboardLayout>
  )
}
