// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Ana layout: Sidebar drawer + hamburger menu + içerik alani (mobil uyumlu)

import { ReactNode, useState } from "react";
import { Menu } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { FirewallLogo } from "../ui/FirewallLogo";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 md:ml-64">
        {/* Mobil ust bar - sadece kucuk ekranlarda */}
        <div className="md:hidden flex items-center gap-3 p-4 border-b border-glass-border glass-card sticky top-0 z-30">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-xl text-gray-400 hover:text-neon-cyan hover:bg-glass-light transition-all duration-200"
          >
            <Menu size={22} />
          </button>
          <FirewallLogo size={26} />
          <span className="text-sm font-bold neon-text">TonbilAi Firewall</span>
        </div>

        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
