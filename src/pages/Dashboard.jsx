import React, { useState } from "react";
import { Upload, Search, History, ArrowRight, Sparkles } from "lucide-react";

// Components
import Sidebar from "../components/Sidebar";
import DashboardHeader from "../components/DashboardHeader";
import AnalysisModal from "../components/AnalysisModal";
import IngredientSafetyTab from "../components/IngredientSafetyTab";
import GlobalAIAssistant from "../components/GlobalAIAssistant";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    // We use h-screen and overflow-hidden on the wrapper to prevent "Double Scrollbars"
    <div className="h-screen w-full bg-[#F8FAFC] dark:bg-slate-900 flex font-sans overflow-hidden">
      
      {/* 1. SIDEBAR: Fixed to the left */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* 2. MAIN CONTENT AREA: A flex column that fills the rest of the screen */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        
        {/* 3. HEADER: Stays at the top of the content area */}
        <DashboardHeader 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          onMobileMenuToggle={() => setIsMobileMenuOpen(true)}
        />

        {/* 4. SCROLLABLE BODY: This is the ONLY part that should scroll */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 md:p-10 custom-scrollbar">
          <div className="max-w-7xl mx-auto w-full pb-20">
            
            {/* --- OVERVIEW TAB --- */}
            {activeTab === "Overview" && (
              <section className="space-y-10 animate-in fade-in duration-500">
                <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-[2.5rem] p-10 text-white relative overflow-hidden shadow-2xl">
                  <div className="relative z-10 max-w-lg">
                    <h2 className="text-4xl font-black mb-4 tracking-tight">Good Morning, Husnain</h2>
                    <p className="text-blue-100 mb-8 font-medium">Ready to check your skin progress today?</p>
                    <button
                      onClick={() => setActiveTab("Analysis")}
                      className="bg-white text-blue-600 px-8 py-4 rounded-2xl font-black text-sm flex items-center gap-2 hover:shadow-lg hover:scale-105 transition-all"
                    >
                      Start New Analysis <ArrowRight size={18} />
                    </button>
                  </div>
                  <Sparkles className="absolute right-[-20px] top-[-20px] text-white/10 w-80 h-80 rotate-12 pointer-events-none" />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <QuickAction title="Skin Scan" desc="Detect conditions" icon={<Upload />} color="text-blue-600" bg="bg-blue-50" onClick={() => setActiveTab("Analysis")} />
                  <QuickAction title="Safety Check" desc="Verify ingredients" icon={<Search />} color="text-emerald-600" bg="bg-emerald-50" onClick={() => setActiveTab("OCR")} />
                  <QuickAction title="Reports" desc="12 saved results" icon={<History />} color="text-amber-600" bg="bg-amber-50" onClick={() => setActiveTab("History")} />
                </div>
              </section>
            )}

            {/* --- ANALYSIS TAB --- */}
            {activeTab === "Analysis" && (
              <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                <AnalysisModal isOpen={true} onClose={() => setActiveTab("Overview")} isTabMode={true} />
              </section>
            )}

            {/* --- INGREDIENT SAFETY TAB --- */}
            {activeTab === "OCR" && (
              <div className="animate-in fade-in duration-500">
                <IngredientSafetyTab />
              </div>
            )}

            {/* --- PLACEHOLDERS --- */}
            {["Progress", "History", "Products", "Settings"].includes(activeTab) && (
              <div className="p-20 text-center bg-white dark:bg-slate-800 rounded-[2.5rem] border border-slate-100 dark:border-slate-700 animate-in zoom-in-95 duration-300">
                <h3 className="text-xl font-black text-slate-900 dark:text-white mb-2">{activeTab} View</h3>
                <p className="text-slate-400 dark:text-slate-500 font-medium">This section is currently under clinical review.</p>
              </div>
            )}
          </div>
        </main>

        {/* 5. AI ASSISTANT: 
            Placed OUTSIDE the <main> scroll area but INSIDE the relative container.
            This ensures it floats on top of everything and never gets cut off. 
        */}
        <div className="absolute bottom-0 right-0 z-[999]">
          <GlobalAIAssistant />
        </div>
      </div>
    </div>
  );
}

function QuickAction({ title, desc, icon, color, bg, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-white dark:bg-slate-800 p-8 rounded-[2.5rem] border border-slate-100 dark:border-slate-700 hover:shadow-2xl hover:shadow-slate-200 dark:hover:shadow-slate-900 hover:-translate-y-2 transition-all cursor-pointer group"
    >
      <div className={`w-16 h-16 ${bg} ${color} rounded-[1.25rem] flex items-center justify-center mb-6 group-hover:rotate-6 transition-transform shadow-sm`}>
        {icon && React.isValidElement(icon) ? React.cloneElement(icon, { size: 32 }) : null}
      </div>
      <h3 className="font-black text-slate-900 dark:text-white text-xl mb-2 tracking-tight">{title}</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{desc}</p>
    </div>
  );
}