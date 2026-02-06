import React from "react";
import { LayoutDashboard, Upload, Search, LineChart, History, ShoppingBag, LogOut, ShieldCheck, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar({ activeTab, setActiveTab, isMobileMenuOpen, setIsMobileMenuOpen }) {
  const navigate = useNavigate();

  const SidebarContent = () => (
    <>
      <div className="p-8">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="bg-blue-600 p-2 rounded-xl shadow-blue-200 shadow-lg group-hover:rotate-12 transition-transform">
            <ShieldCheck className="text-white" size={24} />
          </div>
          <span className="text-2xl font-black tracking-tighter text-slate-900 dark:text-white">Skyntri</span>
        </Link>
      </div>

      <nav className="flex-1 px-6 space-y-2 overflow-y-auto">
        <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] mb-4 px-2">Main Menu</p>
        
        <NavItem icon={<LayoutDashboard size={20} />} label="Overview" active={activeTab === "Overview"} onClick={() => { setActiveTab("Overview"); setIsMobileMenuOpen(false); }} />
        <NavItem icon={<Upload size={20} />} label="Skin Analysis" active={activeTab === "Analysis"} onClick={() => { setActiveTab("Analysis"); setIsMobileMenuOpen(false); }} />
        <NavItem icon={<Search size={20} />} label="Ingredient Scan" active={activeTab === "OCR"} onClick={() => { setActiveTab("OCR"); setIsMobileMenuOpen(false); }} />
        <NavItem icon={<LineChart size={20} />} label="Progress Tracking" active={activeTab === "Progress"} onClick={() => { setActiveTab("Progress"); setIsMobileMenuOpen(false); }} />
        <NavItem icon={<History size={20} />} label="History" active={activeTab === "History"} onClick={() => { setActiveTab("History"); setIsMobileMenuOpen(false); }} />
        
        <div className="pt-4">
          <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] mb-4 px-2">Shop</p>
          <NavItem icon={<ShoppingBag size={20} />} label="Marketplace" active={activeTab === "Products"} onClick={() => { setActiveTab("Products"); setIsMobileMenuOpen(false); }} color="text-emerald-600" />
        </div>
      </nav>

      <div className="p-6 border-t border-slate-50 dark:border-slate-800 space-y-3">
        <ThemeToggle className="w-full justify-center" />
        <button onClick={() => navigate("/login")} className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all">
          <LogOut size={20} /> Logout
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="w-72 bg-white dark:bg-slate-800 border-r border-slate-100 dark:border-slate-700 hidden lg:flex flex-col sticky top-0 h-screen shadow-sm shrink-0 z-20 relative">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Toggle Button - shown in DashboardHeader */}
      
      {/* Mobile Sidebar Drawer */}
      {isMobileMenuOpen && (
        <>
          {/* Overlay */}
          <div 
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          
          {/* Drawer */}
          <aside className="fixed left-0 top-0 bottom-0 w-72 bg-white dark:bg-slate-800 border-r border-slate-100 dark:border-slate-700 flex flex-col shadow-2xl z-50 lg:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <X size={24} />
            </button>
            <SidebarContent />
          </aside>
        </>
      )}
    </>
  );
}

function NavItem({ icon, label, active, onClick, color = "text-slate-500" }) {
  return (
    <button onClick={onClick} className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-sm font-bold transition-all duration-200 ${active ? "bg-blue-600 text-white shadow-lg shadow-blue-100 dark:shadow-blue-900/20 scale-[1.02]" : `${color} dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white`}`}>
      {icon}
      <span className="flex-1 text-left">{label}</span>
    </button>
  );
}