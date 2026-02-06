import React from "react";
import { useNavigate } from "react-router-dom";
import AnalysisModal from "../components/AnalysisModal";

export default function AnalysisPage() {
  const navigate = useNavigate();

  return (
    <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <AnalysisModal 
        isOpen={true} 
        onClose={() => navigate('/dashboard')} 
        isTabMode={true} 
      />
    </section>
  );
}
