import { Check, Copy, Volume2, VolumeX } from 'lucide-react'
import { useState } from 'react'
import Markdown from './Markdown.jsx'

function plainText(markdown) {
  return (markdown || '').replace(/[|*_#>`]/g, ' ').replace(/-{3,}/g, ' ').replace(/\s+/g, ' ').trim()
}

export default function ChatMessage({ role, content, imageUrl, speaking, onSpeak }) {
  const [copied, setCopied] = useState(false)

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-neutral-900/[0.06] px-4 py-2.5 text-[0.9375rem] leading-7 text-neutral-900 dark:bg-white/10 dark:text-neutral-100">
          {content}
        </div>
      </div>
    )
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard not available */
    }
  }

  return (
    <div className="group">
      <Markdown>{content}</Markdown>
      {imageUrl && (
        <img src={imageUrl} alt="Illustration created by the assistant" className="mt-3 max-h-96 rounded-xl border border-neutral-200 dark:border-white/10" />
      )}
      <div className="mt-1.5 flex gap-1 opacity-60 transition-opacity group-hover:opacity-100">
        <button onClick={copy} className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-900/5 dark:hover:bg-white/10" aria-label="Copy answer">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
        {onSpeak && (
          <button
            onClick={() => onSpeak(plainText(content))}
            className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-900/5 dark:hover:bg-white/10"
            aria-label={speaking ? 'Stop reading' : 'Read aloud'}
          >
            {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
    </div>
  )
}
