import React from "react";
// ADD 'Sparkles' HERE IN THE LIST
import { Sparkles, Settings, Bell, Menu } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

export default function DashboardHeader({ activeTab, setActiveTab, onMobileMenuToggle }) {
  return (
    <header className="h-20 bg-white dark:bg-slate-800 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between px-6 md:px-10 sticky top-0 z-[100] w-full">
      <div className="flex items-center gap-4">
        {/* Mobile Menu Button */}
        <button
          onClick={onMobileMenuToggle}
          className="lg:hidden p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
        >
          <Menu size={24} />
        </button>
        
        <div>
          <h1 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Skyntri Portal</h1>
          <p className="text-lg font-black text-slate-900 dark:text-white">{activeTab}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 relative z-[110]">
        {/* Hide AI Assistant button on small screens */}
        <button
          type="button"
          onMouseEnter={() => console.log("MOUSE ENTERED")}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("CLICKED!");
            window.dispatchEvent(new Event('openSkyntriAI'));
          }}
          className="hidden sm:flex group items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl font-bold transition-all cursor-pointer hover:bg-slate-900 active:scale-95 shadow-lg relative pointer-events-auto"
        >
          <Sparkles size={18} />
          <span>AI Assistant</span>
        </button>

        {/* Theme Toggle - visible on all screens */}
        <ThemeToggle />

        {/* Settings - hide on smallest screens */}
        <button
          onClick={() => setActiveTab("Settings")}
          className={`hidden sm:block p-2.5 rounded-xl border transition-all cursor-pointer pointer-events-auto ${
            activeTab === 'Settings'
              ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-100 dark:border-blue-800 text-blue-600 dark:text-blue-400'
              : 'bg-white dark:bg-slate-700 border-slate-100 dark:border-slate-600 text-slate-400 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400'
          }`}
        >
          <Settings size={20} />
        </button>

        {/* Notification Bell - hide on smallest screens */}
        <button className="hidden sm:block p-2.5 rounded-xl bg-white dark:bg-slate-700 border border-slate-100 dark:border-slate-600 text-slate-400 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 relative cursor-pointer pointer-events-auto">
          <Bell size={20} />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white dark:border-slate-700"></span>
        </button>

        {/* User Avatar */}
        <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 p-[2px] ml-2 shrink-0">
          <div className="h-full w-full bg-white dark:bg-slate-800 rounded-[14px] flex items-center justify-center text-blue-600 dark:text-blue-400 font-black text-xs uppercase">HM</div>
        </div>
      </div>
    </header>
  );
}