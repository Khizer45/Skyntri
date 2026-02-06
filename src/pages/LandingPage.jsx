import React from "react";
import { BrainCircuit, MessageSquare, Search, ArrowRight } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import SolutionCard from "../components/SolutionCard";

export default function LandingPage() {
  return (
    <div id="home" className="min-h-screen bg-gradient-to-b from-white via-slate-50 to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 text-[#0F172A] dark:text-slate-100 font-sans selection:bg-blue-600 selection:text-white">
      <Navbar />

      <main>
        {/* HERO SECTION */}
        <header className="relative px-6 md:px-12 lg:px-24 pt-20 pb-20 text-center">
          <div className="max-w-5xl mx-auto">
            <div className="inline-block px-4 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-bold text-[10px] uppercase tracking-widest mb-6 border border-blue-100 dark:border-blue-800">
              Next Gen Dermatology AI
            </div>
            <h1 className="text-5xl md:text-7xl font-black leading-tight tracking-tight text-slate-900 dark:text-white mb-10">
              Precision Skin <span className="text-blue-600 dark:text-blue-400 italic">Intelligence</span>
            </h1>
            <p className="mt-6 text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto font-medium mb-10">
              Advanced AI screening for skin health and ingredient safety. Fast, explainable results with clear next steps.
            </p>
            <div className="flex justify-center">
              <button className="inline-flex items-center gap-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-xl font-bold hover:scale-[1.02] transition-transform shadow-lg">
                Explore Solutions <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </header>

        {/* PROJECT BRIEF */}
        <section id="intro" className="px-6 md:px-12 lg:px-24 py-16 bg-white/50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-700">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-white mb-8 tracking-tight">Project Brief</h2>
            <div className="max-w-3xl">
              <p className="text-xl md:text-2xl text-slate-600 dark:text-slate-300 leading-relaxed font-medium mb-6">
                Skyntri is an AI powered assistant designed to bridge the gap between technology and dermatology.
              </p>
              <p className="text-lg text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                By utilizing deep learning for image classification and intelligent ingredient scanning, 
                we empower users to monitor their skin health with clinical grade precision.
              </p>
            </div>
          </div>
        </section>

        {/* SOLUTIONS */}
        <section id="solutions" className="px-6 md:px-12 lg:px-24 py-20">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-white mb-8 tracking-tight">What Skyntri Does</h2>
            <div className="grid gap-6 lg:grid-cols-3">
              <SolutionCard
                accent="from-blue-50 to-blue-25"
                icon={<BrainCircuit size={22} className="text-blue-600" />}
                title="Image Analysis"
                desc="State of the art CNN classification for common skin conditions with confidence scores."
              />
              <SolutionCard
                accent="from-emerald-50 to-emerald-25"
                icon={<Search size={22} className="text-emerald-600" />}
                title="Ingredient Safety"
                desc="OCR driven ingredient scanning and curated safety checks tailored to skin type."
              />
              <SolutionCard
                accent="from-violet-50 to-violet-25"
                icon={<MessageSquare size={22} className="text-violet-600" />}
                title="Conversational Assistant"
                desc="NLP powered guidance for routines and evidence based next steps."
              />
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}