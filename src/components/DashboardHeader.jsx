import React from "react";
import { Sparkles, Settings, Bell, Menu } from "lucide-react";
import { useLocation } from "react-router-dom";

export default function DashboardHeader({ isSidebarOpen, setIsSidebarOpen }) {
  const location = useLocation();
  
  // Determine the active tab name based on the current route
  const getActiveTabName = () => {
    const path = location.pathname;
    if (path === '/dashboard' || path === '/dashboard/') return 'Overview';
    if (path.includes('/analysis')) return 'Skin Analysis';
    if (path.includes('/scan')) return 'Ingredient Scan';
    if (path.includes('/progress')) return 'Progress Tracking';
    if (path.includes('/history')) return 'History';
    if (path.includes('/products')) return 'Marketplace';
    if (path.includes('/premium')) return 'Get Plus';
    return 'Dashboard';
  };

  return (
    <header className="h-20 bg-white border-b border-slate-100 flex items-center justify-between px-6 lg:px-10 sticky top-0 z-[100] w-full shadow-sm">
      <div className="flex items-center gap-4">
        {/* Hamburger Menu - Mobile Only */}
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="lg:hidden p-2.5 rounded-xl hover:bg-slate-100 text-slate-600 transition-colors"
        >
          <Menu size={24} />
        </button>
        
        <div>
          <h1 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Skyntri Portal</h1>
          <p className="text-lg font-black text-slate-900">{getActiveTabName()}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 relative z-[110]">
        <button
          type="button"
          onMouseEnter={() => console.log("MOUSE ENTERED")}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("CLICKED!");
            window.dispatchEvent(new Event('openSkyntriAI'));
          }}
          className="group flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl font-bold transition-all cursor-pointer hover:bg-slate-900 active:scale-95 shadow-lg relative pointer-events-auto"
        >
          <Sparkles size={18} />
          <span className="hidden sm:inline">AI Assistant</span>
        </button>

        {/* Settings */}
        <button
          className="p-2.5 rounded-xl border bg-white border-slate-100 text-slate-400 hover:text-blue-600 transition-all cursor-pointer pointer-events-auto"
        >
          <Settings size={20} />
        </button>

        <button className="p-2.5 rounded-xl bg-white border border-slate-100 text-slate-400 hover:text-blue-600 relative cursor-pointer pointer-events-auto">
          <Bell size={20} />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        </button>

        <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 p-[2px] ml-2 shrink-0">
          <div className="h-full w-full bg-white rounded-[14px] flex items-center justify-center text-blue-600 font-black text-xs uppercase">HM</div>
        </div>
      </div>
    </header>
  );
}