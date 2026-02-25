// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Canlı saldırı akışı: paket detayları, IP, ülke, saldırı tipi

import { memo } from "react";
import { Activity } from "lucide-react";
import { GlassCard } from "../common/GlassCard";

interface Attack {
  ip: string;
  lat: number;
  lon: number;
  country: string;
  countryCode: string;
  city: string;
  isp: string;
  type: string;
  packets: number;
  bytes: number;
}

const PROT_LABELS: Record<string, string> = {
  syn_flood: "SYN Flood",
  udp_flood: "UDP Flood",
  icmp_flood: "ICMP Flood",
  conn_limit: "Conn Limit",
  invalid_packet: "Invalid Pkt",
};

const PROT_COLORS: Record<string, string> = {
  syn_flood: "text-red-400 bg-red-500/10 border-red-500/30",
  udp_flood: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  icmp_flood: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  conn_limit: "text-purple-400 bg-purple-500/10 border-purple-500/30",
  invalid_packet: "text-gray-400 bg-gray-500/10 border-gray-500/30",
};

function formatBytes(b: number): string {
  if (b >= 1073741824) return (b / 1073741824).toFixed(1) + " GB";
  if (b >= 1048576) return (b / 1048576).toFixed(1) + " MB";
  if (b >= 1024) return (b / 1024).toFixed(1) + " KB";
  return b + " B";
}

function formatNumber(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n.toString();
}

// Ülke kodu -> bayrak emoji
function countryFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const offset = 127397;
  return String.fromCodePoint(
    code.charCodeAt(0) + offset,
    code.charCodeAt(1) + offset
  );
}

function AttackFeedInner({ attacks }: { attacks: Attack[] }) {
  return (
    <GlassCard className="p-0">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-glass-border">
        <Activity size={16} className="text-red-400" />
        <span className="text-sm font-medium text-white">Saldırı Akışı</span>
        <span className="text-xs text-gray-500 ml-2">
          {attacks.length} aktif kaynak
        </span>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {attacks.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-gray-500 text-sm">
            Aktif saldırı tespit edilmedi
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-glass-border">
                <th className="text-left px-4 py-2 font-medium">Kaynak IP</th>
                <th className="text-left px-3 py-2 font-medium">Konum</th>
                <th className="text-left px-3 py-2 font-medium">ISP</th>
                <th className="text-left px-3 py-2 font-medium">Tip</th>
                <th className="text-right px-3 py-2 font-medium">Paket</th>
                <th className="text-right px-4 py-2 font-medium">Boyut</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack, i) => {
                const colorClass =
                  PROT_COLORS[attack.type] || PROT_COLORS.invalid_packet;
                return (
                  <tr
                    key={`${attack.ip}-${attack.type}-${i}`}
                    className="border-b border-glass-border/50 hover:bg-glass-light/30 transition-colors"
                  >
                    <td className="px-4 py-2">
                      <code className="text-red-300 text-xs font-mono">
                        {attack.ip}
                      </code>
                    </td>
                    <td className="px-3 py-2 text-gray-300">
                      <span className="mr-1.5 text-base">
                        {countryFlag(attack.countryCode)}
                      </span>
                      <span className="text-xs">
                        {attack.city ? `${attack.city}, ` : ""}
                        {attack.countryCode}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 max-w-[140px] truncate">
                      {attack.isp || "-"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block text-[10px] px-2 py-0.5 rounded-full border ${colorClass}`}
                      >
                        {PROT_LABELS[attack.type] || attack.type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-xs text-gray-300 font-mono">
                      {formatNumber(attack.packets)}
                    </td>
                    <td className="px-4 py-2 text-right text-xs text-gray-400">
                      {formatBytes(attack.bytes)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </GlassCard>
  );
}

export const AttackFeed = memo(AttackFeedInner);
