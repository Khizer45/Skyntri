import { RotateCcw, Send, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import ChatMessage from '../components/ChatMessage.jsx'
import Button from '../components/Button.jsx'
import * as api from '../services/api.js'
import DashboardLayout from '../layouts/DashboardLayout.jsx'

const suggestedPrompts = [
  'What skincare routine should I follow?',
  'What does this skin condition mean?',
  'How can I reduce acne?',
  'What ingredients should I avoid?',
]

export default function AIAssistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    let mounted = true

    api.getChatHistory()
      .then((history) => {
        if (mounted) setMessages(history)
      })
      .catch((err) => {
        if (mounted) setError(err.message || 'Unable to load chat history.')
      })
      .finally(() => {
        if (mounted) setLoadingHistory(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const send = async (text) => {
    const content = (text ?? input).trim()
    if (!content || sending) return

    const userMsg = {
      id: `pending-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setError('')
    setSending(true)

    try {
      const reply = await api.sendChatMessage(content)
      setMessages((prev) => [
        ...prev.filter((item) => item.id !== userMsg.id),
        userMsg,
        reply,
      ])
    } catch (err) {
      setMessages((prev) => prev.filter((item) => item.id !== userMsg.id))
      setError(err.message || 'The assistant could not respond.')
    } finally {
      setSending(false)
    }
  }

  const clearChat = async () => {
    try {
      await api.clearChatHistory()
      setMessages([])
      setError('')
    } catch (err) {
      setError(err.message || 'Unable to clear conversation.')
    }
  }

  return (
    <DashboardLayout title="AI Skin Assistant">
      <div className="mx-auto flex h-[calc(100vh-11rem)] max-w-2xl flex-col">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs text-neutral-400">
            Skyntri AI · informational guidance, not a medical diagnosis
          </p>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1 text-xs font-medium text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            >
              <RotateCcw className="h-3 w-3" />
              Clear conversation
            </button>
          )}
        </div>

        {error && (
          <p className="mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
            {error}
          </p>
        )}

        <div className="flex-1 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-panel-dark">
          {loadingHistory ? (
            <div className="flex h-full items-center justify-center text-xs text-neutral-400">
              Loading conversation…
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <div className="rounded-full bg-brand-50 p-3 dark:bg-brand-900/30">
                <Sparkles className="h-5 w-5 text-brand-600 dark:text-brand-400" />
              </div>

              <div>
                <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
                  Ask Skyntri anything about your skin
                </p>
                <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                  Try one of these to get started
                </p>
              </div>

              <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
                {suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="rounded-lg border border-neutral-200 px-3 py-2 text-left text-xs text-neutral-600 hover:border-brand-300 hover:bg-brand-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:border-brand-700 dark:hover:bg-brand-900/20"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <ChatMessage key={message.id} {...message} />
              ))}

              {sending && (
                <div className="flex items-center gap-2 text-xs text-neutral-400">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" />
                  </span>
                  Skyntri is typing…
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
          className="mt-3 flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={2000}
            placeholder="Ask about your skin, ingredients, or routines…"
            className="flex-1 rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-panel-dark dark:text-neutral-100"
          />
          <Button
            type="submit"
            icon={Send}
            disabled={!input.trim()}
            loading={sending}
            aria-label="Send message"
          />
        </form>
      </div>
    </DashboardLayout>
  )
}
