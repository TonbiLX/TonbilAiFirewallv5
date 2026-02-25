// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Üst çubuk: durum göstergeleri, başlık, kullanıcı menüsü, actions slot

import { useState, useRef, useEffect, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Wifi, WifiOff, User, Settings, LogOut, ChevronDown } from "lucide-react";
import { NeonBadge } from "../common/NeonBadge";
import { getUser, clearAuth } from "../../services/tokenStore";
import { authApi } from "../../services/authApi";

interface TopBarProps {
  title: string;
  connected: boolean;
  actions?: ReactNode;
}

export function TopBar({ title, connected, actions }: TopBarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const userInfo = getUser();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try { await authApi.logout(); } catch {}
    clearAuth();
    window.location.href = "/login";
  };

  return (
    <header className="flex items-center justify-between mb-6">
      <h2 className="text-2xl font-bold">{title}</h2>
      <div className="flex items-center gap-4">
        <NeonBadge label="DEV" variant="amber" />

        {actions}

        <div className="flex items-center gap-2">
          {connected ? (
            <>
              <Wifi size={16} className="text-neon-green" />
              <span className="text-xs text-neon-green">Canlı</span>
            </>
          ) : (
            <>
              <WifiOff size={16} className="text-neon-red" />
              <span className="text-xs text-neon-red">Bağlantı Yok</span>
            </>
          )}
        </div>

        {/* Kullanıcı Menüsü */}
        {userInfo && (
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl glass-card border border-glass-border hover:border-neon-cyan/30 transition-all duration-200"
            >
              <div className="w-8 h-8 rounded-lg bg-neon-cyan/20 flex items-center justify-center">
                <User size={16} className="text-neon-cyan" />
              </div>
              <span className="text-sm text-gray-300 hidden sm:inline">
                {userInfo.display_name || userInfo.username}
              </span>
              <ChevronDown
                size={14}
                className={`text-gray-500 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`}
              />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-2 w-56 glass-card border border-glass-border rounded-xl shadow-2xl z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-glass-border">
                  <p className="text-sm text-white font-medium truncate">
                    {userInfo.display_name || userInfo.username}
                  </p>
                  <p className="text-xs text-gray-500">Yönetici</p>
                </div>
                <div className="p-1">
                  <button
                    onClick={() => { setMenuOpen(false); navigate("/settings"); }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-glass-light transition-all duration-200"
                  >
                    <Settings size={16} />
                    <span>Hesap Ayarları</span>
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-neon-red hover:bg-neon-red/10 transition-all duration-200"
                  >
                    <LogOut size={16} />
                    <span>Çıkış Yap</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
