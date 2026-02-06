import React from "react";

export default function TeamMember({ name }) {
  return (
    <li className="flex items-center gap-3 group">
      <div className="h-[1px] w-3 bg-slate-700 dark:bg-slate-800 group-hover:w-5 group-hover:bg-blue-500 transition-all duration-300" />
      <span className="text-sm font-semibold text-slate-300 dark:text-slate-400 tracking-tight group-hover:text-blue-400 transition-colors">
        {name}
      </span>
    </li>
  );
}