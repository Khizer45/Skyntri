import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`p-2.5 rounded-xl border transition-all hover:scale-105 active:scale-95 ${
        theme === 'dark'
          ? 'bg-slate-800 border-slate-700 text-yellow-400 hover:bg-slate-700'
          : 'bg-white border-slate-100 text-slate-600 hover:bg-slate-50'
      } ${className}`}
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
