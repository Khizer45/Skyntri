import React, { useState } from "react";
import { Outlet } from "react-router-dom";

// Components
import Sidebar from "../components/Sidebar";
import DashboardHeader from "../components/DashboardHeader";
import GlobalAIAssistant from "../components/GlobalAIAssistant";

export default function Dashboard() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    // We use h-screen and overflow-hidden on the wrapper to prevent "Double Scrollbars"
    <div className="h-screen w-full bg-[#F8FAFC] flex font-sans overflow-hidden">
      
      {/* 1. SIDEBAR: Fixed to the left */}
      <Sidebar isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen} />

      {/* 2. MAIN CONTENT AREA: A flex column that fills the rest of the screen */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        
        {/* 3. HEADER: Stays at the top of the content area */}
        <DashboardHeader isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen} />

        {/* 4. SCROLLABLE BODY: This is the ONLY part that should scroll */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 md:p-10 custom-scrollbar">
          <div className="max-w-7xl mx-auto w-full pb-20">
            {/* Nested routes will be rendered here */}
            <Outlet />
          </div>
        </main>

        {/* CRITICAL: AI Assistant outside the scrollable area, no z-index conflicts */}
        <GlobalAIAssistant />
      </div>
    </div>
  );
}
