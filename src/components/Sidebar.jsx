import React from "react";
import { LayoutDashboard, Upload, Search, LineChart, History, ShoppingBag, LogOut, ShieldCheck, Crown, X } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

export default function Sidebar({ isSidebarOpen, setIsSidebarOpen }) {
  const navigate = useNavigate();

  return (
    <>
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-72 bg-white border-r border-slate-100 
        flex flex-col h-screen shadow-sm shrink-0
        transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header with Logo */}
        <div className="p-8 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="bg-blue-600 p-2 rounded-xl shadow-blue-200 shadow-lg group-hover:rotate-12 transition-transform">
              <ShieldCheck className="text-white" size={24} />
            </div>
            <span className="text-2xl font-black tracking-tighter text-slate-900">Skyntri</span>
          </Link>
          
          {/* Close button for mobile */}
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="lg:hidden p-2 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-900 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-6 space-y-2 overflow-y-auto">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4 px-2">Main Menu</p>
          
          <NavItem to="/dashboard" icon={<LayoutDashboard size={20} />} label="Overview" end />
          <NavItem to="/dashboard/analysis" icon={<Upload size={20} />} label="Skin Analysis" />
          <NavItem to="/dashboard/scan" icon={<Search size={20} />} label="Ingredient Scan" />
          <NavItem to="/dashboard/progress" icon={<LineChart size={20} />} label="Progress Tracking" />
          <NavItem to="/dashboard/history" icon={<History size={20} />} label="History" />
          
          <div className="pt-6">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4 px-2">Premium</p>
            <NavItem 
              to="/dashboard/premium" 
              icon={<Crown size={20} />} 
              label="Get Plus" 
              isPremium 
            />
          </div>
          
          <div className="pt-6">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4 px-2">Shop</p>
            <NavLink 
              to="/marketplace" 
              className={({ isActive }) => `
                w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-sm font-bold transition-all duration-200
                ${isActive 
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-100 scale-[1.02]" 
                  : "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700"
                }
              `}
              onClick={() => setIsSidebarOpen(false)}
            >
              <ShoppingBag size={20} />
              <span className="flex-1 text-left">Marketplace</span>
            </NavLink>
          </div>
        </nav>

        {/* Logout Button */}
        <div className="p-6 border-t border-slate-50">
          <button 
            onClick={() => navigate("/login")} 
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold text-red-500 hover:bg-red-50 transition-all"
          >
            <LogOut size={20} /> Logout
          </button>
        </div>
      </aside>
    </>
  );
}

function NavItem({ to, icon, label, end = false, isPremium = false, color = "text-slate-500" }) {
  return (
    <NavLink 
      to={to}
      end={end}
      className={({ isActive }) => `
        w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-sm font-bold transition-all duration-200
        ${isActive 
          ? "bg-blue-600 text-white shadow-lg shadow-blue-100 scale-[1.02]" 
          : isPremium
            ? "text-amber-600 hover:bg-amber-50 hover:text-amber-700"
            : `${color} hover:bg-slate-50 hover:text-slate-900`
        }
      `}
    >
      {icon}
      <span className="flex-1 text-left">{label}</span>
    </NavLink>
  );
}
