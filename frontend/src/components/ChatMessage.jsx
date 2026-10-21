import { Sparkles, User } from 'lucide-react'

export default function ChatMessage({ role, content, timestamp }) {
  const isUser = role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isUser ? 'bg-neutral-200 dark:bg-neutral-700' : 'bg-brand-100 dark:bg-brand-900/40'
        }`}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-neutral-600 dark:text-neutral-300" />
        ) : (
          <Sparkles className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
        )}
      </div>
      <div className={`flex max-w-[80%] flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-brand-600 text-white'
              : 'bg-neutral-100 text-neutral-800 dark:bg-panel-dark dark:text-neutral-200'
          }`}
        >
          {content}
        </div>
        {timestamp && (
          <span className="px-1 text-[11px] text-neutral-400">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}
