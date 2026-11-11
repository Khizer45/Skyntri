import { Camera, RefreshCw, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import Button from './Button.jsx'

/**
 * Live camera preview with a capture button.
 * Calls onCapture(file) with a JPEG File. The stream is always stopped
 * when the dialog closes, so the camera light goes off.
 */
export default function CameraCapture({ onCapture, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [facing, setFacing] = useState('user')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  useEffect(() => {
    let cancelled = false
    setReady(false)
    setError('')

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('This browser cannot open the camera. Please upload a photo instead.')
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 960 } },
          audio: false,
        })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        stop()
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
        setReady(true)
      } catch (err) {
        if (cancelled) return
        setError(
          err?.name === 'NotAllowedError'
            ? 'Camera access was blocked. Allow the camera for this site in your browser, then try again.'
            : err?.name === 'NotFoundError'
              ? 'No camera was found on this device.'
              : 'The camera could not be started. Please upload a photo instead.'
        )
      }
    }

    start()
    return () => {
      cancelled = true
    }
  }, [facing, stop])

  useEffect(() => stop, [stop])

  useEffect(() => {
    const onKey = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const capture = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob) return
        stop()
        onCapture(new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
      },
      'image/jpeg',
      0.92
    )
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Take a photo">
      <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-white dark:bg-panel-dark">
        <div className="flex items-center justify-between px-4 py-3">
          <p className="text-sm font-semibold text-neutral-900 dark:text-white">Take a photo</p>
          <button onClick={onClose} className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-white/10" aria-label="Close camera">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="relative aspect-[4/3] bg-neutral-950">
          <video
            ref={videoRef}
            playsInline
            muted
            className={`h-full w-full object-cover ${facing === 'user' ? '-scale-x-100' : ''}`}
          />
          {!ready && !error && (
            <p className="absolute inset-0 flex items-center justify-center text-sm text-neutral-400">Starting camera…</p>
          )}
          {error && (
            <p className="absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-neutral-200">{error}</p>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 px-4 py-3">
          <Button variant="ghost" size="sm" icon={RefreshCw} onClick={() => setFacing((f) => (f === 'user' ? 'environment' : 'user'))}>
            Switch camera
          </Button>
          <Button icon={Camera} onClick={capture} disabled={!ready}>
            Capture
          </Button>
        </div>
        <p className="muted px-4 pb-3 text-xs">Use even light, no filter. The photo is only uploaded when you start the analysis.</p>
      </div>
    </div>
  )
}
