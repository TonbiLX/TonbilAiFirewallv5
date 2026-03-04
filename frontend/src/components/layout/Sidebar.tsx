// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Kenar cubugu navigasyonu: Cyberpunk temalı, mobil uyumlu drawer

import { NavLink } from "react-router-dom";
import {
  Map,
  LayoutDashboard,
  Monitor,
  Users,
  Activity,
  Brain,
  ShieldCheck,
  ShieldBan,
  Network,
  Flame,
  Globe,
  MessageSquare,
  Lock,
  Filter,
  Radar,
  Wifi,
  LogOut,
  Settings,
  ScrollText,
  Clock,
  Send,
  Cpu,
  Sparkles,
  Wrench,
  X,
} from "lucide-react";
import { FirewallLogo } from "../ui/FirewallLogo";
import clsx from "clsx";
import { getUser, clearAuth } from "../../services/tokenStore";
import { authApi } from "../../services/authApi";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/system-monitor", icon: Cpu, label: "Sistem Monitörü" },
  { to: "/devices", icon: Monitor, label: "Cihazlar" },
  { to: "/profiles", icon: Users, label: "Profiller" },
  { to: "/content-categories", icon: Filter, label: "İçerik Filtreleri" },
  { to: "/dns", icon: ShieldBan, label: "DNS Engelleme" },
  { to: "/dhcp", icon: Network, label: "DHCP" },
  { to: "/wifi", icon: Wifi, label: "WiFi AP" },
  { to: "/firewall", icon: Flame, label: "Güvenlik Duvarı" },
  { to: "/ddos-map", icon: Map, label: "DDoS Harita" },
  { to: "/ip-management", icon: ShieldCheck, label: "IP Yönetimi" },
  { to: "/vpn", icon: Globe, label: "VPN (Uzak Erisim)" },
  { to: "/vpn-client", icon: Radar, label: "Dış VPN İstemci" },
  { to: "/tls", icon: Lock, label: "TLS Şifreleme" },
  { to: "/chat", icon: MessageSquare, label: "AI Asistan" },
  { to: "/traffic", icon: Activity, label: "Trafik" },
  { to: "/insights", icon: Brain, label: "AI Insights" },
  { to: "/system-logs", icon: ScrollText, label: "Sistem Logları" },
  { to: "/system-time", icon: Clock, label: "Saat & Tarih" },
  { to: "/telegram", icon: Send, label: "Telegram Bot" },
  { to: "/ai-settings", icon: Sparkles, label: "Yapay Zeka Ayarları" },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobil backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          "fixed left-0 top-0 h-screen w-64 glass-card rounded-none border-r border-glass-border z-50 flex flex-col",
          "transition-transform duration-300 ease-in-out",
          "md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="p-6 border-b border-glass-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FirewallLogo size={34} />
              <div>
                <h1 className="text-lg font-bold neon-text">TonbilAi</h1>
                <p className="text-xs text-gray-500">AI Firewall v5.0</p>
              </div>
            </div>
            {/* Mobil kapat butonu */}
            <button
              onClick={onClose}
              className="md:hidden p-1 rounded-lg text-gray-400 hover:text-white hover:bg-glass-light transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Navigasyon */}
        <nav className="flex-1 min-h-0 overflow-y-auto p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all duration-200",
                  isActive
                    ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 shadow-neon"
                    : "text-gray-400 hover:text-white hover:bg-glass-light"
                )
              }
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Alt bilgi + Ayarlar + Çıkış */}
        <div className="p-4 border-t border-glass-border space-y-1">
          {(() => {
            const userInfo = getUser();
            return userInfo ? (
              <div className="px-4 py-2 mb-2">
                <p className="text-xs text-white font-medium truncate">
                  {userInfo.display_name || userInfo.username}
                </p>
                <p className="text-[10px] text-gray-500">Yönetici</p>
              </div>
            ) : null;
          })()}
          <NavLink
            to="/system-management"
            onClick={onClose}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all duration-200",
                isActive
                  ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                  : "text-gray-400 hover:text-white hover:bg-glass-light"
              )
            }
          >
            <Wrench size={18} />
            <span>Sistem Yönetimi</span>
          </NavLink>
          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all duration-200",
                isActive
                  ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                  : "text-gray-400 hover:text-white hover:bg-glass-light"
              )
            }
          >
            <Settings size={18} />
            <span>Hesap Ayarları</span>
          </NavLink>
          <button
            onClick={async () => {
              try { await authApi.logout(); } catch {}
              clearAuth();
              window.location.href = "/login";
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-neon-red hover:bg-neon-red/10 transition-all duration-200"
          >
            <LogOut size={18} />
            <span>Çıkış Yap</span>
          </button>
          <div className="text-xs text-gray-600 text-center">
            <p>TonbilAiFirewall V5.0</p>
            <p className="text-neon-cyan/50 mt-1">Yapay Zeka Destekli Güvenlik Duvarı</p>
          </div>
        </div>
      </aside>
    </>
  );
}
