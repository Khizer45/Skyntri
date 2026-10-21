import { ImagePlus, RotateCcw, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'

export default function ImageUploader({ label = 'Upload image', onChange, hint, className = '' }) {
  const [preview, setPreview] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const acceptFile = (file) => {
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
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

  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    acceptFile(e.dataTransfer.files?.[0])
  }

  const clear = () => {
    setPreview(null)
    setError('')
    onChange?.(null, null)
    if (inputRef.current) inputRef.current.value = ''
  }

  if (preview) {
    return (
      <div className={className}>
        <div className="relative overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
          <img src={preview} alt="Uploaded preview" className="max-h-72 w-full object-contain bg-neutral-50 dark:bg-neutral-900" />
          <div className="absolute right-2 top-2 flex gap-1.5">
            <button
              onClick={() => inputRef.current?.click()}
              className="rounded-md bg-white/90 p-1.5 text-neutral-700 shadow-subtle hover:bg-white dark:bg-neutral-900/90 dark:text-neutral-200"
              aria-label="Replace image"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={clear}
              className="rounded-md bg-white/90 p-1.5 text-neutral-700 shadow-subtle hover:bg-white dark:bg-neutral-900/90 dark:text-neutral-200"
              aria-label="Remove image"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => acceptFile(e.target.files?.[0])}
        />
      </div>
    )
  }

  return (
    <div className={className}>
      <label
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors ${
          dragActive
            ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
            : 'border-neutral-300 hover:border-brand-300 dark:border-neutral-700 dark:hover:border-brand-700'
        }`}
      >
        <div className="rounded-full bg-brand-50 p-2.5 dark:bg-brand-900/30">
          <UploadCloud className="h-5 w-5 text-brand-600 dark:text-brand-400" />
        </div>
        <p className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{label}</p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {hint || 'Drag & drop or click to upload — JPEG, PNG, WebP up to 10MB'}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => acceptFile(e.target.files?.[0])}
        />
      </label>
      {error && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
          <ImagePlus className="h-3.5 w-3.5" /> {error}
        </p>
      )}
    </div>
  )
}
