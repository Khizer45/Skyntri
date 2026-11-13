import { ArrowUp, Mic, Square, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import ChatMessage from '../components/ChatMessage.jsx'
import { Alert } from '../components/ui.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

const suggestions = [
  'Make a morning and evening routine table for oily skin',
  'How can I fade dark spots safely?',
  'Compare niacinamide and vitamin C in a table',
  'Mujhe acne ke liye simple routine batao',
]

// Speech recognition / speech output languages per reply language.
const SPEECH_LANG = { auto: '', en: 'en-US', ur: 'ur-PK', roman_ur: 'ur-PK' }
const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window

export default function AIAssistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [language, setLanguage] = useState(() => localStorage.getItem('skyntri-chat-language') || 'auto')
  const [caps, setCaps] = useState({ llm: false, images: false, languages: [{ id: 'auto', label: 'Auto' }] })
  const [listening, setListening] = useState(false)
  const [speakingId, setSpeakingId] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    let active = true
    api.getChatHistory()
      .then((history) => active && setMessages(history))
      .catch((err) => active && setError(err.message || 'Unable to load the conversation.'))
      .finally(() => active && setLoading(false))
    api.getChatCapabilities().then((data) => active && setCaps(data)).catch(() => {})
    return () => {
      active = false
      recognitionRef.current?.abort?.()
      if (canSpeak) window.speechSynthesis.cancel()
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  useEffect(() => {
    localStorage.setItem('skyntri-chat-language', language)
  }, [language])

  // Grow the input with its content, up to a limit.
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }, [input])

  const send = async (text) => {
    const content = (text ?? input).trim()
    if (!content || sending) return

    const pending = { id: `pending-${Date.now()}`, role: 'user', content }
    setMessages((prev) => [...prev, pending])
    setInput('')
    setError('')
    setSending(true)

    try {
      const reply = await api.sendChatMessage(content, language)
      setMessages((prev) => [...prev, reply])
    } catch (err) {
      setMessages((prev) => prev.filter((item) => item.id !== pending.id))
      setInput(content)
      setError(err.message || 'The assistant could not respond.')
    } finally {
      setSending(false)
    }
  }

  const clearChat = async () => {
    if (!window.confirm('Delete this whole conversation?')) return
    try {
      await api.clearChatHistory()
      setMessages([])
      setError('')
    } catch (err) {
      setError(err.message || 'Unable to clear the conversation.')
    }
  }

  const toggleMic = () => {
    if (listening) {
      recognitionRef.current?.stop()
      return
    }
    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition
    recognition.lang = SPEECH_LANG[language] || navigator.language || 'en-US'
    recognition.interimResults = true
    recognition.continuous = false
    const base = input ? `${input.trim()} ` : ''

    recognition.onresult = (event) => {
      const spoken = Array.from(event.results).map((r) => r[0].transcript).join('')
      setInput(base + spoken)
    }
    recognition.onerror = (event) => {
      setListening(false)
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setError('Microphone access was blocked. Allow the microphone for this site in your browser.')
      } else if (event.error !== 'aborted' && event.error !== 'no-speech') {
        setError('Voice input did not work. Please type your question.')
      }
    }
    recognition.onend = () => {
      setListening(false)
      inputRef.current?.focus()
    }
    setError('')
    setListening(true)
    recognition.start()
  }

  const speak = (id, text) => {
    if (!canSpeak) return
    window.speechSynthesis.cancel()
    if (speakingId === id) {
      setSpeakingId(null)
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    // Urdu script is read with an Urdu voice when the device has one.
    utterance.lang = /[؀-ۿ]/.test(text) ? 'ur-PK' : SPEECH_LANG[language] || 'en-US'
    utterance.onend = () => setSpeakingId(null)
    utterance.onerror = () => setSpeakingId(null)
    setSpeakingId(id)
    window.speechSynthesis.speak(utterance)
  }

  const empty = !loading && messages.length === 0

  return (
    <DashboardLayout
      title="Assistant"
      fill
      actions={
        <>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            aria-label="Reply language"
            className="rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-xs text-neutral-700 dark:border-white/15 dark:text-neutral-200"
          >
            {caps.languages.map((option) => (
              <option key={option.id} value={option.id} className="text-neutral-900">
                {option.id === 'auto' ? 'Language: auto' : option.label}
              </option>
            ))}
          </select>
          {messages.length > 0 && (
            <button onClick={clearChat} className="rounded-md p-2 text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10" aria-label="Delete conversation">
              <Trash2 className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </button>
          )}
        </>
      }
    >
      <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 py-6 sm:px-6">
          {loading ? (
            <p className="muted m-auto text-sm">Loading conversation…</p>
          ) : empty ? (
            <div className="m-auto w-full text-center">
              <h2 className="text-2xl font-semibold text-neutral-900 dark:text-white">How can I help your skin today?</h2>
              <p className="muted mt-2 text-sm">
                Ask in English, Urdu or Roman Urdu. I can answer with tables{caps.images ? ' and simple illustrations' : ''}.
              </p>
              <div className="mx-auto mt-6 grid max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
                {suggestions.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="rounded-xl border border-neutral-200 px-3.5 py-3 text-left text-sm text-neutral-700 transition-colors hover:border-neutral-400 hover:bg-white dark:border-white/10 dark:text-neutral-300 dark:hover:border-white/30 dark:hover:bg-white/5"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  {...message}
                  speaking={speakingId === message.id}
                  onSpeak={canSpeak ? (text) => speak(message.id, text) : null}
                />
              ))}
              {sending && (
                <div className="flex gap-1.5 py-2" aria-label="The assistant is writing">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400" />
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 px-4 pb-4 sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          {error && <Alert className="mb-2">{error}</Alert>}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              send()
            }}
            className="flex items-end gap-2 rounded-2xl border border-neutral-300 bg-white p-2 shadow-subtle focus-within:border-neutral-500 dark:border-white/15 dark:bg-panel-dark dark:focus-within:border-white/40"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault()
                  send()
                }
              }}
              maxLength={2000}
              placeholder={listening ? 'Listening…' : 'Ask about your skin, a product or a routine'}
              aria-label="Message"
              className="max-h-44 min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-[0.9375rem] text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-0 dark:text-neutral-100"
            />
            {SpeechRecognition && (
              <button
                type="button"
                onClick={toggleMic}
                aria-label={listening ? 'Stop voice input' : 'Speak your question'}
                aria-pressed={listening}
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors ${
                  listening ? 'bg-red-600 text-white' : 'text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10'
                }`}
              >
                {listening ? <Square className="h-3.5 w-3.5" fill="currentColor" /> : <Mic className="h-[18px] w-[18px]" strokeWidth={1.75} />}
              </button>
            )}
            <button
              type="submit"
              disabled={!input.trim() || sending}
              aria-label="Send"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white transition-colors hover:bg-neutral-700 disabled:opacity-30 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
            >
              <ArrowUp className="h-[18px] w-[18px]" />
            </button>
          </form>
          <p className="muted mt-2 text-center text-xs">
            General skin-care information, not a diagnosis. For a medical opinion, book a dermatologist under Doctors.
          </p>
        </div>
      </div>
    </DashboardLayout>
  )
}
