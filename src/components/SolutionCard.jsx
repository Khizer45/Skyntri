import React from "react";

export default function SolutionCard({ icon, title, desc, accent }) {
  return (
    <article className="p-8 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 hover:shadow-2xl hover:shadow-slate-200 dark:hover:shadow-slate-900 transition-all duration-300 hover:-translate-y-2 group">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-6 bg-gradient-to-br ${accent} group-hover:rotate-6 transition-transform shadow-md`}>
        {icon}
      </div>
      <h4 className="text-xl font-bold text-slate-900 dark:text-white mb-3">{title}</h4>
      <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed font-medium">{desc}</p>
    </article>
  );
}