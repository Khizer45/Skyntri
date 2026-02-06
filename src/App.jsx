// src/App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

// These paths must match your folder structure exactly
import LandingPage from "./pages/LandingPage";
import SignupPage from "./pages/SignupPage";
import LoginPage from "./pages/LoginPage";
import ForgotPassword from "./pages/ForgotPassword";
import Dashboard from "./pages/Dashboard";
import DashboardOverview from "./pages/DashboardOverview";
import AnalysisPage from "./pages/AnalysisPage";
import IngredientScanPage from "./pages/IngredientScanPage";

// Placeholder component for under-development pages
function PlaceholderPage({ title }) {
  return (
    <div className="p-20 text-center bg-white rounded-[2.5rem] border border-slate-100 animate-in zoom-in-95 duration-300">
      <h3 className="text-xl font-black text-slate-900 mb-2">{title} View</h3>
      <p className="text-slate-400 font-medium">This section is currently under clinical review.</p>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        
        {/* Dashboard with nested routes */}
        <Route path="/dashboard" element={<Dashboard />}>
          <Route index element={<DashboardOverview />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="scan" element={<IngredientScanPage />} />
          <Route path="history" element={<PlaceholderPage title="History" />} />
          <Route path="progress" element={<PlaceholderPage title="Progress Tracking" />} />
          <Route path="products" element={<PlaceholderPage title="Marketplace" />} />
          <Route path="premium" element={<PlaceholderPage title="Get Plus" />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;