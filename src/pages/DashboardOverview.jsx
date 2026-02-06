import React from "react";
import { useNavigate } from "react-router-dom";
import { Upload, Search, History, ArrowRight, Sparkles } from "lucide-react";

export default function DashboardOverview() {
  const navigate = useNavigate();

  return (
    <section className="space-y-10 animate-in fade-in duration-500">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-[2.5rem] p-10 text-white relative overflow-hidden shadow-2xl">
        <div className="relative z-10 max-w-lg">
          <h2 className="text-4xl font-black mb-4 tracking-tight">Good Morning, Husnain</h2>
          <p className="text-blue-100 mb-8 font-medium">Ready to check your skin progress today?</p>
          <button
            onClick={() => navigate('/dashboard/analysis')}
            className="bg-white text-blue-600 px-8 py-4 rounded-2xl font-black text-sm flex items-center gap-2 hover:shadow-lg hover:scale-105 transition-all"
          >
            Start New Analysis <ArrowRight size={18} />
          </button>
        </div>
        <Sparkles className="absolute right-[-20px] top-[-20px] text-white/10 w-80 h-80 rotate-12 pointer-events-none" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <QuickAction 
          title="Skin Scan" 
          desc="Detect conditions" 
          icon={<Upload />} 
          color="text-blue-600" 
          bg="bg-blue-50" 
          onClick={() => navigate('/dashboard/analysis')} 
        />
        <QuickAction 
          title="Safety Check" 
          desc="Verify ingredients" 
          icon={<Search />} 
          color="text-emerald-600" 
          bg="bg-emerald-50" 
          onClick={() => navigate('/dashboard/scan')} 
        />
        <QuickAction 
          title="Reports" 
          desc="12 saved results" 
          icon={<History />} 
          color="text-amber-600" 
          bg="bg-amber-50" 
          onClick={() => navigate('/dashboard/history')} 
        />
      </div>
    </section>
  );
}

function QuickAction({ title, desc, icon, color, bg, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-white p-8 rounded-[2.5rem] border border-slate-100 hover:shadow-2xl hover:shadow-slate-200 hover:-translate-y-2 transition-all cursor-pointer group"
    >
      <div className={`w-16 h-16 ${bg} ${color} rounded-[1.25rem] flex items-center justify-center mb-6 group-hover:rotate-6 transition-transform shadow-sm`}>
        {icon && React.isValidElement(icon) ? React.cloneElement(icon, { size: 32 }) : null}
      </div>
      <h3 className="font-black text-slate-900 text-xl mb-2 tracking-tight">{title}</h3>
      <p className="text-sm text-slate-500 font-medium leading-relaxed">{desc}</p>
    </div>
  );
}
