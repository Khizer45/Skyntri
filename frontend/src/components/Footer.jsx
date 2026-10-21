import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="border-t border-neutral-200 px-4 py-6 text-xs text-neutral-500 dark:border-neutral-800 dark:text-neutral-400 sm:px-6">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 sm:flex-row">
        <p>Skyntri — AI-Based Skin Health Assistant</p>
        <div className="flex items-center gap-4">
          <Link to="/contact" className="hover:text-neutral-700 dark:hover:text-neutral-200">
            About
          </Link>
          <Link to="/contact" className="hover:text-neutral-700 dark:hover:text-neutral-200">
            Contact
          </Link>
          <Link to="/contact" className="hover:text-neutral-700 dark:hover:text-neutral-200">
            Privacy
          </Link>
          <Link to="/contact" className="hover:text-neutral-700 dark:hover:text-neutral-200">
            Terms
          </Link>
        </div>
      </div>
      <p className="mx-auto mt-4 max-w-6xl">
        AI-generated results are for informational purposes and do not replace professional medical advice.
      </p>
    </footer>
  )
}
