import { Camera, ImagePlus, RotateCcw, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'
import CameraCapture from './CameraCapture.jsx'

const TYPES = ['image/jpeg', 'image/png', 'image/webp']

export default function ImageUploader({ label = 'Upload image', onChange, hint, className = '', camera = true }) {
  const [preview, setPreview] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const acceptFile = (file) => {
    if (!file) return
    if (!TYPES.includes(file.type)) {
      setError('Unsupported format. Please use JPEG, PNG, or WebP.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Image is larger than 10MB.')
      return
    }
    setError('')
    const url = URL.createObjectURL(file)
    setPreview(url)
    onChange?.(file, url)
  }

  const clear = () => {
    setPreview(null)
    setError('')
    onChange?.(null, null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const fileInput = (
    <input
      ref={inputRef}
      type="file"
      accept={TYPES.join(',')}
      className="hidden"
      onChange={(e) => acceptFile(e.target.files?.[0])}
    />
  )

  const cameraDialog = cameraOpen && (
    <CameraCapture
      onClose={() => setCameraOpen(false)}
      onCapture={(file) => {
        setCameraOpen(false)
        acceptFile(file)
      }}
    />
  )

  if (preview) {
    return (
      <div className={className}>
        <div className="relative overflow-hidden rounded-xl border border-neutral-200 dark:border-white/10">
          <img src={preview} alt="Selected photo" className="max-h-72 w-full bg-neutral-50 object-contain dark:bg-neutral-900" />
          <div className="absolute right-2 top-2 flex gap-1.5">
            {camera && (
              <button onClick={() => setCameraOpen(true)} className="rounded-md bg-white/90 p-1.5 text-neutral-700 hover:bg-white dark:bg-neutral-900/90 dark:text-neutral-200" aria-label="Retake with camera">
                <Camera className="h-3.5 w-3.5" />
              </button>
            )}
            <button onClick={() => inputRef.current?.click()} className="rounded-md bg-white/90 p-1.5 text-neutral-700 hover:bg-white dark:bg-neutral-900/90 dark:text-neutral-200" aria-label="Replace image">
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
            <button onClick={clear} className="rounded-md bg-white/90 p-1.5 text-neutral-700 hover:bg-white dark:bg-neutral-900/90 dark:text-neutral-200" aria-label="Remove image">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        {fileInput}
        {cameraDialog}
      </div>
    )
  }

  return (
    <div className={className}>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragActive(false)
          acceptFile(e.dataTransfer.files?.[0])
        }}
        className={`flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-4 py-8 text-center transition-colors ${
          dragActive ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-neutral-300 dark:border-white/15'
        }`}
      >
        <div>
          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100">{label}</p>
          <p className="muted mt-1 text-xs">{hint || 'JPEG, PNG or WebP, up to 10MB. You can also drop a file here.'}</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          {camera && (
            <button
              type="button"
              onClick={() => setCameraOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
            >
              <Camera className="h-4 w-4" /> Use camera
            </button>
          )}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-100 dark:border-white/15 dark:text-neutral-200 dark:hover:bg-white/5"
          >
            <UploadCloud className="h-4 w-4" /> Upload photo
          </button>
        </div>
        {fileInput}
      </div>
      {error && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
          <ImagePlus className="h-3.5 w-3.5" /> {error}
        </p>
      )}
      {cameraDialog}
    </div>
  )
}
