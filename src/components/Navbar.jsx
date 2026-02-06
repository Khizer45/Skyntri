// src/components/Navbar.jsx
import React from "react";
import { ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom"; // Ensure this is imported

export default function Navbar() {
  return (
    <nav className="flex items-center justify-between px-6 md:px-12 py-4 bg-white/60 backdrop-blur-md sticky top-0 z-50 border-b border-slate-100">
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg shadow">
          <ShieldCheck className="text-white" size={22} />
        </div>
        <span className="text-lg md:text-xl font-extrabold tracking-tight text-slate-900">Skyntri</span>
      </div>

      <div className="hidden lg:flex gap-8 text-xs font-bold uppercase tracking-widest text-slate-500">
        <a href="#home" className="hover:text-blue-600 transition">Home</a>
        <a href="#solutions" className="hover:text-blue-600 transition">Solutions</a>
        <Link to="/marketplace" className="hover:text-blue-600 transition">Marketplace</Link>
        <a href="#footer" className="hover:text-blue-600 transition">Team</a>
      </div>

      {/* CHANGE THIS LINE FROM /login TO /signup */}
      <Link 
        to="/signup" 
        className="bg-blue-600 text-white px-5 py-2 rounded-full font-bold text-sm hover:bg-blue-700 transition-shadow"
      >
        Get Started
      </Link>
    </nav>
  );
}