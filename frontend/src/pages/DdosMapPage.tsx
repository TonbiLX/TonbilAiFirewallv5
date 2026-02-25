// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// DDoS Attack Map: Dünya haritası üzerinde canlı saldırı görüntüleme

import { useEffect, useState, useCallback } from "react";
import { Globe, Shield, Zap, Activity, RefreshCw, AlertTriangle } from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { DdosWorldMap } from "../components/ddos/DdosWorldMap";
import { AttackFeed } from "../components/ddos/AttackFeed";
import { fetchDdosAttackMap } from "../services/ddosApi";

interface AttackData {
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

interface MapData {
  target: { lat: number; lon: number; label: string };
  attacks: AttackData[];
  summary: {
    total_packets: number;
    total_bytes: number;
    by_protection: Record<string, { packets: number; bytes: number }>;
    active_attackers: number;
  };
  last_updated: string;
}

const PROT_LABELS: Record<string, string> = {
  syn_flood: "SYN Flood",
  udp_flood: "UDP Flood",
  icmp_flood: "ICMP Flood",
  conn_limit: "Conn Limit",
  invalid_packet: "Invalid Pkt",
};

const PROT_COLORS: Record<string, string> = {
  syn_flood: "#ef4444",
  udp_flood: "#f97316",
  icmp_flood: "#eab308",
  conn_limit: "#a855f7",
  invalid_packet: "#6b7280",
};

function formatNumber(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n.toString();
}

function formatBytes(b: number): string {
  if (b >= 1073741824) return (b / 1073741824).toFixed(1) + " GB";
  if (b >= 1048576) return (b / 1048576).toFixed(1) + " MB";
  if (b >= 1024) return (b / 1024).toFixed(1) + " KB";
  return b + " B";
}

export function DdosMapPage() {
  const [data, setData] = useState<MapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    try {
      const res = await fetchDdosAttackMap();
      setData(res.data);
      setError(null);
      setLastRefresh(new Date());
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Veri alinamadi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const byProt = data?.summary?.by_protection || {};

  return (
    <div className="space-y-4">
      <TopBar title="DDoS Attack Map" connected={true} />

      {/* Ust istatistik kartlari */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <GlassCard className="p-3 text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Shield size={16} className="text-neon-cyan" />
            <span className="text-xs text-gray-400">Toplam Engel</span>
          </div>
          <p className="text-xl font-bold text-white">
            {data ? formatNumber(data.summary.total_packets) : "-"}
          </p>
          <p className="text-[10px] text-gray-500">
            {data ? formatBytes(data.summary.total_bytes) : ""}
          </p>
        </GlassCard>

        {Object.entries(byProt).map(([prot, stats]) => (
          <GlassCard key={prot} className="p-3 text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: PROT_COLORS[prot] || "#6b7280" }}
              />
              <span className="text-xs text-gray-400">
                {PROT_LABELS[prot] || prot}
              </span>
            </div>
            <p className="text-xl font-bold text-white">
              {formatNumber(stats.packets)}
            </p>
            <p className="text-[10px] text-gray-500">{formatBytes(stats.bytes)}</p>
          </GlassCard>
        ))}

        <GlassCard className="p-3 text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <AlertTriangle size={16} className="text-red-400" />
            <span className="text-xs text-gray-400">Saldırgan</span>
          </div>
          <p className="text-xl font-bold text-white">
            {data ? data.summary.active_attackers : "-"}
          </p>
          <p className="text-[10px] text-gray-500">aktif kaynak</p>
        </GlassCard>
      </div>

      {/* Hata mesaji */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Dünya Haritası */}
      <GlassCard className="p-0 overflow-hidden relative">
        {/* Baslik bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-glass-border">
          <div className="flex items-center gap-2">
            <Globe size={16} className="text-neon-cyan" />
            <span className="text-sm font-medium text-white">
              Canlı Saldırı Haritası
            </span>
            <span className="flex items-center gap-1 text-xs">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-green-400">Live</span>
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>
              {lastRefresh.toLocaleTimeString("tr-TR")}
            </span>
            <button
              onClick={loadData}
              className="p-1 rounded hover:bg-glass-light transition"
              title="Yenile"
            >
              <RefreshCw size={14} className={loading ? "animate-spin text-neon-cyan" : "text-gray-400"} />
            </button>
          </div>
        </div>

        {/* Harita */}
        <div className="relative" style={{ height: "min(55vh, 500px)" }}>
          {data && (
            <DdosWorldMap
              attacks={data.attacks}
              target={data.target}
            />
          )}
          {loading && !data && (
            <div className="absolute inset-0 flex items-center justify-center">
              <RefreshCw size={32} className="animate-spin text-neon-cyan" />
            </div>
          )}
        </div>

        {/* Lejant */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-glass-border">
          {Object.entries(PROT_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs text-gray-400">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: PROT_COLORS[key] }}
              />
              <span>{label}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 text-xs text-gray-400 ml-auto">
            <div className="w-2 h-2 rounded-full bg-neon-cyan animate-pulse" />
            <span>Hedef</span>
          </div>
        </div>
      </GlassCard>

      {/* Saldırı Akışı */}
      <AttackFeed attacks={data?.attacks || []} />
    </div>
  );
}
