import React from "react";
import { ShieldCheck, ArrowRight, Lock, Mail } from "lucide-react";
import { Link, useNavigate } from "react-router-dom"; // 1. Added useNavigate

export default function LoginPage() {
  const navigate = useNavigate(); // 2. Initialize navigate

  const handleLogin = (e) => {
    e.preventDefault();
    // Here you would normally check email/password with a database
    // For now, we just redirect to the dashboard
    navigate("/dashboard"); 
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center gap-2 mb-6">
          <div className="bg-blue-600 p-1.5 rounded-lg shadow-sm">
            <ShieldCheck className="text-white" size={24} />
          </div>
          <span className="text-xl font-black tracking-tight text-slate-900 dark:text-white">Skyntri</span>
        </Link>
        <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">Welcome back</h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-slate-800 py-8 px-4 shadow-xl border border-slate-100 dark:border-slate-700 sm:rounded-2xl sm:px-10">
          
          {/* 3. Added onSubmit={handleLogin} */}
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center">
                  <Mail className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                </div>
                <input required type="email" className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-600 outline-none" placeholder="name@example.com" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center">
                  <Lock className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                </div>
                <input required type="password" className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-600 outline-none" placeholder="••••••••" />
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <Link to="/forgot-password" size={18} className="font-bold text-blue-600 hover:text-blue-500">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl shadow-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 transition-all transform hover:scale-[1.01]"
            >
              Sign in <ArrowRight size={18} />
            </button>
          </form>

          <div className="mt-6 text-center pt-6 border-t border-slate-50 dark:border-slate-700">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Don't have an account?{" "}
              <Link to="/signup" className="font-bold text-blue-600 dark:text-blue-400 hover:text-blue-500">Create account</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}