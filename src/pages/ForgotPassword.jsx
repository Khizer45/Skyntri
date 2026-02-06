import React, { useState } from "react"; // Added useState
import { ShieldCheck, ArrowRight, Mail, ArrowLeft, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function ForgotPassword() {
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real app, you would call your API here
    setIsSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="bg-blue-600 p-1.5 rounded-lg shadow-sm">
              <ShieldCheck className="text-white" size={24} />
            </div>
            <span className="text-xl font-black tracking-tight text-slate-900 dark:text-white">Skyntri</span>
          </Link>
        </div>

        {!isSubmitted ? (
          <>
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">Reset password</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Enter your email and we'll send you a link to reset your password.
            </p>
          </>
        ) : (
          <>
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="text-emerald-500" size={48} />
            </div>
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">Check your email</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 px-4">
              We've sent a password reset link to your email address.
            </p>
          </>
        )}
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-slate-800 py-8 px-4 shadow-xl border border-slate-100 dark:border-slate-700 sm:rounded-2xl sm:px-10">
          {!isSubmitted ? (
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                  </div>
                  <input
                    required
                    type="email"
                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-600 transition-all sm:text-sm"
                    placeholder="name@example.com"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl shadow-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 transition-all transform hover:scale-[1.01]"
              >
                Send Reset Link <ArrowRight size={18} />
              </button>
            </form>
          ) : (
            <div className="space-y-6">
              <p className="text-sm text-slate-500 dark:text-slate-400 text-center leading-relaxed">
                Didn't receive the email? Check your spam folder or try again in a few minutes.
              </p>
              <button
                onClick={() => setIsSubmitted(false)}
                className="w-full py-3 px-4 rounded-xl border-2 border-slate-100 dark:border-slate-700 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all"
              >
                Try a different email
              </button>
            </div>
          )}

          <div className="mt-6 text-center border-t border-slate-50 dark:border-slate-700 pt-6">
            <Link to="/login" className="inline-flex items-center gap-2 text-sm font-bold text-blue-600 dark:text-blue-400 hover:text-blue-500 transition-colors">
              <ArrowLeft size={16} /> Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}