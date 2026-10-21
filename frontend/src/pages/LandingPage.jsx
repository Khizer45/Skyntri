import { Link } from "react-router-dom";
import {
  Sparkles,
  ScanFace,
  ShieldCheck,
  MessageCircle,
  TrendingUp,
  FileText,
  Camera,
  ArrowRight,
  CheckCircle2,
  Moon,
  Sun,
  ChevronRight,
  Lock,
  Activity,
} from "lucide-react";
import { useTheme } from "../context/ThemeContext.jsx";

const FEATURES = [
  {
    icon: ScanFace,
    title: "AI Skin Analysis",
    description:
      "Upload a skin image and receive AI-assisted insights across common visible skin concerns such as acne, dark spots, dryness, redness, pores, and wrinkles.",
  },
  {
    icon: Camera,
    title: "Ingredient Scanner",
    description:
      "Scan a product ingredient label with OCR and get ingredient information, safety guidance, and skin-suitability insights.",
  },
  {
    icon: MessageCircle,
    title: "AI Skin Assistant",
    description:
      "Ask skincare questions and receive personalized guidance through an AI-powered conversational assistant.",
  },
  {
    icon: TrendingUp,
    title: "Progress Tracking",
    description:
      "Record regular check-ins and monitor changes in your skin over time through your personal progress history.",
  },
  {
    icon: FileText,
    title: "Health Reports",
    description:
      "Generate organized PDF reports containing your analysis results, recommendations, and relevant skin history.",
  },
  {
    icon: ShieldCheck,
    title: "Personalized Guidance",
    description:
      "Receive recommendations based on your skin analysis, profile, ingredient information, and tracked progress.",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Create your profile",
    description:
      "Create your account and provide basic information about your skin and skincare concerns.",
  },
  {
    number: "02",
    title: "Analyze your skin",
    description:
      "Upload an image or scan a product label to receive AI-assisted skincare insights.",
  },
  {
    number: "03",
    title: "Track your progress",
    description:
      "Review recommendations, save your results, and monitor your skin journey over time.",
  },
];

const HIGHLIGHTS = [
  "AI-assisted skin insights",
  "Ingredient safety information",
  "Personalized recommendations",
  "Progress history",
];

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-surface-light text-neutral-900 dark:bg-surface-dark dark:text-neutral-100">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-neutral-200 bg-surface-light/90 backdrop-blur-md dark:border-neutral-800 dark:bg-surface-dark/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>

            <div>
              <span className="text-base font-semibold">Skyntri</span>
              <span className="ml-2 hidden text-xs text-neutral-400 dark:text-neutral-500 sm:inline">
                AI Skin Health Assistant
              </span>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 text-sm text-neutral-600 dark:text-neutral-400 md:flex">
            <a href="#features" className="transition-colors hover:text-neutral-900 dark:hover:text-neutral-100">
              Features
            </a>
            <a href="#how-it-works" className="transition-colors hover:text-neutral-900 dark:hover:text-neutral-100">
              How it works
            </a>
            <a href="#security" className="transition-colors hover:text-neutral-900 dark:hover:text-neutral-100">
              Privacy & Safety
            </a>
          </nav>

          <div className="flex items-center gap-1.5 sm:gap-2.5">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="rounded-md p-1.5 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>

            <Link
              to="/login"
              className="hidden rounded-lg px-3.5 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800 sm:block"
            >
              Log in
            </Link>

            <Link
              to="/signup"
              className="rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main>
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 -z-10">
            <div className="absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-brand-100 opacity-40 blur-3xl dark:bg-brand-900/30" />
          </div>

          <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-2 lg:gap-14">
            {/* Hero copy */}
            <div className="max-w-xl">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 shadow-subtle dark:border-neutral-800 dark:bg-panel-dark dark:text-neutral-400">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-brand-50 dark:bg-brand-900/40">
                  <Sparkles className="h-2.5 w-2.5 text-brand-600 dark:text-brand-400" />
                </span>
                AI-powered skin health assistance
              </div>

              <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl lg:text-5xl">
                Understand your skin.
                <span className="mt-1.5 block text-brand-600 dark:text-brand-400">
                  Make informed decisions.
                </span>
              </h1>

              <p className="mt-5 max-w-md text-sm leading-6 text-neutral-600 dark:text-neutral-400 sm:text-base sm:leading-7">
                Skyntri brings skin analysis, ingredient scanning, AI-powered
                guidance, and progress tracking together in one simple
                platform.
              </p>

              <div className="mt-7 flex flex-col gap-2.5 sm:flex-row">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
                >
                  Start your skin journey
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <a
                  href="#how-it-works"
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-panel-dark"
                >
                  See how it works
                  <ChevronRight className="h-4 w-4" />
                </a>
              </div>

              {/* Trust points */}
              <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-xs text-neutral-500 dark:text-neutral-400">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
                  Simple to use
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
                  Personalized insights
                </span>
                <span className="flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
                  Privacy-focused
                </span>
              </div>
            </div>

            {/* Hero visual */}
            <div className="relative mx-auto w-full max-w-lg">
              <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-subtle dark:border-neutral-800 dark:bg-panel-dark sm:p-5">
                {/* Mock dashboard header */}
                <div className="flex items-center justify-between border-b border-neutral-100 pb-3.5 dark:border-neutral-800">
                  <div>
                    <p className="text-xs font-medium text-neutral-400 dark:text-neutral-500">SKYNTRI AI</p>
                    <h2 className="mt-1 text-base font-semibold">Skin Overview</h2>
                  </div>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-900/30">
                    <Activity className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  </div>
                </div>

                {/* Mock analysis card */}
                <div className="mt-4 rounded-lg border border-neutral-200 bg-surface-light p-4 dark:border-neutral-800 dark:bg-surface-dark">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-neutral-400 dark:text-neutral-500">Latest AI analysis</p>
                      <p className="mt-0.5 text-sm font-semibold">Skin insights</p>
                    </div>
                    <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                      Completed
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                    {["Acne", "Dark Spots", "Dry Skin", "Pores", "Redness", "Wrinkles"].map((item) => (
                      <div key={item} className="rounded-lg border border-neutral-200 bg-white px-2.5 py-2.5 dark:border-neutral-800 dark:bg-panel-dark">
                        <div className="mb-1.5 h-1.5 rounded-full bg-brand-100 dark:bg-brand-900/40">
                          <div className="h-1.5 w-2/3 rounded-full bg-brand-500" />
                        </div>
                        <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300">{item}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Mock recommendation */}
                <div className="mt-3.5 rounded-lg bg-brand-600 p-4 text-white">
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/15">
                      <Sparkles className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Personalized guidance</p>
                      <p className="mt-0.5 text-xs leading-5 text-white/75">
                        Review your skin insights and follow a consistent skincare routine.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Decorative card */}
              <div className="absolute -bottom-4 -left-4 hidden rounded-lg border border-neutral-200 bg-white p-3.5 shadow-subtle dark:border-neutral-800 dark:bg-panel-dark sm:block">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-900/30">
                    <ShieldCheck className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold">Privacy-focused</p>
                    <p className="mt-0.5 text-[11px] text-neutral-400 dark:text-neutral-500">Your data stays protected</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Highlights */}
        <section className="border-y border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/40">
          <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-neutral-200 dark:divide-neutral-800 sm:grid-cols-4">
            {HIGHLIGHTS.map((item) => (
              <div key={item} className="px-4 py-5 text-center text-xs font-medium text-neutral-600 dark:text-neutral-400 sm:px-5">
                <CheckCircle2 className="mx-auto mb-1.5 h-4 w-4 text-brand-600 dark:text-brand-400" />
                {item}
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section id="features" className="py-14 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="max-w-xl">
              <span className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
                Platform features
              </span>
              <h2 className="mt-2.5 text-2xl font-semibold tracking-tight sm:text-3xl">
                Everything you need to understand your skin
              </h2>
              <p className="mt-3 max-w-lg text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                Skyntri combines multiple skincare tools into one connected
                experience, so your analysis, recommendations, and progress
                stay together.
              </p>
            </div>

            <div className="mt-9 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, description }) => (
                <div
                  key={title}
                  className="group rounded-xl border border-neutral-200 bg-white p-5 shadow-subtle transition-colors hover:border-brand-300 dark:border-neutral-800 dark:bg-panel-dark dark:hover:border-brand-700"
                >
                  <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-900/30">
                    <Icon className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>
                  <p className="mt-1.5 text-sm leading-6 text-neutral-600 dark:text-neutral-400">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="border-y border-neutral-200 bg-neutral-50 py-14 dark:border-neutral-800 dark:bg-neutral-900/40 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="mx-auto max-w-xl text-center">
              <span className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
                Simple process
              </span>
              <h2 className="mt-2.5 text-2xl font-semibold tracking-tight sm:text-3xl">How Skyntri works</h2>
              <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                Start with your profile, explore your skin insights, and keep
                track of your progress over time.
              </p>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
              {STEPS.map((step, index) => (
                <div key={step.number} className="relative rounded-xl border border-neutral-200 bg-white p-5 shadow-subtle dark:border-neutral-800 dark:bg-panel-dark">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-semibold text-brand-200 dark:text-brand-800">{step.number}</span>
                    {index < STEPS.length - 1 && (
                      <ArrowRight className="hidden h-4 w-4 text-neutral-300 dark:text-neutral-700 md:block" />
                    )}
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-neutral-900 dark:text-neutral-100">{step.title}</h3>
                  <p className="mt-1.5 text-sm leading-6 text-neutral-600 dark:text-neutral-400">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Security / Safety */}
        <section id="security" className="py-14 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="grid gap-8 rounded-xl border border-neutral-200 bg-white p-6 shadow-subtle dark:border-neutral-800 dark:bg-panel-dark sm:p-8 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-900/30">
                  <ShieldCheck className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                </div>
                <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                  Built with privacy and responsible AI in mind
                </h2>
                <p className="mt-3 max-w-md text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                  Skyntri is designed to provide educational and AI-assisted
                  skincare insights. Results are not a medical diagnosis and
                  should not replace professional medical advice.
                </p>
              </div>

              <div className="grid gap-2.5 sm:grid-cols-2">
                {[
                  "Secure account access",
                  "Personalized user history",
                  "AI-assisted recommendations",
                  "Clear health disclaimer",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2.5 rounded-lg border border-neutral-200 bg-surface-light p-3.5 dark:border-neutral-800 dark:bg-surface-dark">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-brand-600 dark:text-brand-400" />
                    <span className="text-sm text-neutral-700 dark:text-neutral-300">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-neutral-200 py-14 dark:border-neutral-800 sm:py-20">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 dark:bg-brand-900/30">
              <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            </div>
            <h2 className="mt-5 text-2xl font-semibold tracking-tight sm:text-3xl">
              Start understanding your skin today
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-neutral-600 dark:text-neutral-400">
              Create your Skyntri account and explore AI-assisted skin
              analysis, ingredient insights, personalized guidance, and
              progress tracking.
            </p>
            <Link
              to="/signup"
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              Create your account
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-200 dark:border-neutral-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 text-xs text-neutral-500 dark:text-neutral-400 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-600">
              <Sparkles className="h-3 w-3 text-white" />
            </div>
            <span className="font-medium text-neutral-700 dark:text-neutral-300">Skyntri</span>
          </Link>
          <p className="text-center sm:text-right">
            © {new Date().getFullYear()} Skyntri. Final Year Project — MUST,
            Department of Software Engineering.
          </p>
        </div>
      </footer>
    </div>
  );
}
