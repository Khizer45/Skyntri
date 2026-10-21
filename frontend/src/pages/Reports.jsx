import { Download, FileText, Printer, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import { Spinner } from '../components/LoadingState.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

export default function Reports() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [generating, setGenerating] = useState(false)
  const [report, setReport] = useState(null)
  const [latestAnalysis, setLatestAnalysis] = useState(null)

  useEffect(() => {
    api.getHistory()
      .then((history) => setLatestAnalysis(history.analyses?.[0] || null))
      .catch(() => {})
  }, [])

  const handleGenerate = async () => {
    setGenerating(true)

    try {
      const res = await api.generateReport({
        analysis_id: latestAnalysis?.id,
        title: 'Skyntri Health Report',
      })
      setReport({
        ...res,
        user: user?.fullName || 'Skyntri member',
        condition: latestAnalysis?.result || 'Latest skin analysis',
        confidence: latestAnalysis?.confidence ?? null,
      })
      showToast('Report generated.', 'success')
    } catch (err) {
      showToast(err.message || 'Report generation failed.', 'error')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <DashboardLayout title="Reports">
      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Generate a health report
          </h2>
        </div>

        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Create a professional summary from your latest available Skyntri analysis and progress data.
        </p>

        {!latestAnalysis && (
          <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
            Run a skin analysis first to generate a report with analysis details.
          </p>
        )}

        <Button
          onClick={handleGenerate}
          loading={generating}
          className="mt-4"
        >
          Generate Report
        </Button>
      </Card>

      {generating && (
        <Card className="mt-6 p-5">
          <Spinner label="Compiling your report…" />
        </Card>
      )}

      {!generating && report && (
        <Card className="mt-6 overflow-hidden">
          <div className="border-b border-neutral-200 bg-brand-50 p-5 dark:border-neutral-800 dark:bg-brand-900/20">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              <span className="text-sm font-semibold text-brand-800 dark:text-brand-200">
                Skyntri Health Report
              </span>
            </div>
          </div>

          <div className="space-y-4 p-5">
            <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <div>
                <p className="text-xs text-neutral-400">Member</p>
                <p className="font-medium text-neutral-800 dark:text-neutral-100">
                  {report.user}
                </p>
              </div>
              <div>
                <p className="text-xs text-neutral-400">Generated</p>
                <p className="font-medium text-neutral-800 dark:text-neutral-100">
                  {new Date(report.generatedAt).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-neutral-400">Confidence</p>
                <p className="font-medium text-neutral-800 dark:text-neutral-100">
                  {report.confidence != null ? `${report.confidence.toFixed(1)}%` : 'Included in report'}
                </p>
              </div>
            </div>

            <div>
              <p className="text-xs text-neutral-400">Latest analysis</p>
              <p className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                {report.condition}
              </p>
            </div>

            <p className="rounded-lg bg-neutral-50 px-3 py-2 text-xs text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
              This report reflects AI-based visible-pattern analysis and does not replace professional medical advice.
            </p>

            <div className="flex flex-wrap gap-2 pt-2">
              <Button
                icon={Download}
                variant="secondary"
                onClick={async () => {
                  try {
                    await api.downloadReport(report.id)
                  } catch (err) {
                    showToast(err.message || 'Unable to download report.', 'error')
                  }
                }}
              >
                Download PDF
              </Button>

              <Button icon={Printer} variant="outline" onClick={() => window.print()}>
                Print
              </Button>
            </div>
          </div>
        </Card>
      )}
    </DashboardLayout>
  )
}
