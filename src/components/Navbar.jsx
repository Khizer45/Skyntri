// src/components/Navbar.jsx
import React, { useState } from "react";
import { ShieldCheck, Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="flex items-center justify-between px-6 md:px-12 py-4 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md sticky top-0 z-50 border-b border-slate-100 dark:border-slate-800">
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg shadow">
          <ShieldCheck className="text-white" size={22} />
        </div>
        <span className="text-lg md:text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">Skyntri</span>
      </div>

      {/* Desktop Navigation */}
      <div className="hidden lg:flex gap-8 text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
        <a href="#home" className="hover:text-blue-600 dark:hover:text-blue-400 transition">Home</a>
        <a href="#solutions" className="hover:text-blue-600 dark:hover:text-blue-400 transition">Solutions</a>
        <a href="#footer" className="hover:text-blue-600 dark:hover:text-blue-400 transition">Team</a>
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />
        
        {/* Mobile Menu Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden p-2 text-slate-900 dark:text-white"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        {/* Get Started Button - Hidden on mobile when menu is open */}
        <Link 
          to="/signup" 
          className="hidden sm:inline-flex bg-blue-600 text-white px-5 py-2 rounded-full font-bold text-sm hover:bg-blue-700 transition-shadow"
        >
          Get Started
        </Link>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="absolute top-full left-0 right-0 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 lg:hidden shadow-lg">
          <div className="flex flex-col p-6 space-y-4">
            <a 
              href="#home" 
              onClick={() => setMobileMenuOpen(false)}
              className="text-sm font-bold uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition"
            >
              Home
            </a>
            <a 
              href="#solutions" 
              onClick={() => setMobileMenuOpen(false)}
              className="text-sm font-bold uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition"
            >
              Solutions
            </a>
            <a 
              href="#footer" 
              onClick={() => setMobileMenuOpen(false)}
              className="text-sm font-bold uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition"
            >
              Team
            </a>
            <Link 
              to="/signup"
              onClick={() => setMobileMenuOpen(false)}
              className="bg-blue-600 text-white px-5 py-3 rounded-full font-bold text-sm text-center hover:bg-blue-700 transition-shadow"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}