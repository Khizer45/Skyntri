import { CalendarDays, FlaskConical, MessageCircle, Moon, ScanFace, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext.jsx'

const FEATURES = [
  {
    icon: ScanFace,
    title: 'Skin analysis',
    text: 'Take a photo and see which visible concerns the AI notices, with simple care advice.',
  },
  {
    icon: CalendarDays,
    title: 'Dermatologists',
    text: 'Book a licensed doctor online, message them and get your prescription as a PDF.',
  },
  {
    icon: MessageCircle,
    title: 'Assistant',
    text: 'Ask about routines and ingredients in English or Urdu, by typing or by voice.',
  },
  {
    icon: FlaskConical,
    title: 'Ingredients and shop',
    text: 'Scan a product label, then find affordable products with the ingredients you need.',
  },
]

const STEPS = [
  ['Create a free account', 'Use your e-mail address or your Google account.'],
  ['Analyse your skin', 'Use your camera or upload a clear, well-lit photo.'],
  ['Get care or see a doctor', 'Follow the advice, or share the result with a dermatologist.'],
]

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-5">
        <span className="text-lg font-semibold tracking-tight text-neutral-900 dark:text-white">Skyntri</span>
        <nav className="flex items-center gap-1.5">
          <button
            onClick={toggleTheme}
            className="rounded-md p-2 text-neutral-600 hover:bg-neutral-900/5 dark:text-neutral-300 dark:hover:bg-white/10"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-900/5 dark:text-neutral-200 dark:hover:bg-white/10">
            Log in
          </Link>
          <Link to="/signup" className="rounded-lg bg-neutral-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200">
            Get started
          </Link>
        </nav>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-3xl px-5 pb-16 pt-16 text-center sm:pt-24">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-neutral-900 dark:text-white sm:text-5xl">
            Your online skin clinic
          </h1>
          <p className="muted mx-auto mt-5 max-w-xl text-lg">
            Understand your skin with AI, then talk to a dermatologist when you need one.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/signup" className="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200">
              Create a free account
            </Link>
            <Link to="/login" className="rounded-lg border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-800 hover:bg-neutral-100 dark:border-white/15 dark:text-neutral-200 dark:hover:bg-white/5">
              I already have an account
            </Link>
          </div>
        </section>

        <section className="mx-auto grid max-w-5xl grid-cols-1 gap-3 px-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-xl border border-neutral-200 bg-white p-5 dark:border-white/10 dark:bg-panel-dark">
              <Icon className="h-5 w-5 text-brand-600 dark:text-brand-300" strokeWidth={1.75} />
              <h2 className="mt-3 text-sm font-semibold text-neutral-900 dark:text-white">{title}</h2>
              <p className="muted mt-1 text-sm">{text}</p>
            </div>
          ))}
        </section>

        <section className="mx-auto max-w-5xl px-5 py-16">
          <h2 className="text-center text-2xl font-semibold text-neutral-900 dark:text-white">How it works</h2>
          <ol className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {STEPS.map(([title, text], index) => (
              <li key={title} className="text-center">
                <span className="mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-sm font-semibold text-white dark:bg-white dark:text-neutral-900">
                  {index + 1}
                </span>
                <p className="mt-3 text-sm font-semibold text-neutral-900 dark:text-white">{title}</p>
                <p className="muted mt-1 text-sm">{text}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-neutral-200 px-5 py-6 text-center text-xs text-neutral-500 dark:border-white/10 dark:text-neutral-400">
        <p>AI results are estimates for information only. They do not replace a doctor's examination.</p>
        <p className="mt-1">© {new Date().getFullYear()} Skyntri</p>
      </footer>
    </div>
  )
}
