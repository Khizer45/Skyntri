import React from "react";
import { ShieldCheck } from "lucide-react";
import TeamMember from "./TeamMember";

export default function Footer() {
  return (
    <footer id="footer" className="bg-slate-900 dark:bg-slate-950 text-slate-300 dark:text-slate-400 pt-16 pb-8 border-t border-slate-800 dark:border-slate-900">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-16">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <ShieldCheck className="text-white" size={20} />
              </div>
              <span className="text-xl font-black tracking-tight text-white">Skyntri</span>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-blue-500/90 mb-2">Project Support</p>
              <p className="text-white text-lg font-bold tracking-tight">Usman Ali</p>
            </div>
          </div>

          <div>
            <h4 className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-400 dark:text-slate-500 mb-6">Development Team</h4>
            <ul className="space-y-4">
              <TeamMember name="Saif Ur Rehman" />
              <TeamMember name="Khizer Hayat" />
              <TeamMember name="Syed Ammar Mehdi" />
            </ul>
          </div>

          <div className="space-y-6">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-400 dark:text-slate-500 mb-6">Institution</h4>
            <div className="space-y-2">
              <p className="text-white font-bold text-sm tracking-tight uppercase">Software Engineering Dept</p>
              <p className="text-sm text-slate-400 dark:text-slate-500 leading-relaxed font-medium">Mirpur University of Sciences and Technology</p>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800 dark:border-slate-900 text-center md:text-left flex flex-col md:flex-row justify-between items-center gap-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-600">© 2026 Skyntri Intelligence.</span>
        </div>
      </div>
    </footer>
  );
}