// --- Ajan: INSAATCI (THE CONSTRUCTOR) + ANALIST (THE ANALYST) ---
// AI Insights sayfası: tehdit paneli + engellenen IP listesi + yapay zeka uyari akışı

import { useEffect, useState, useCallback } from "react";
import { AlertTriangle, Shield, Info, Brain, Ban, Unlock, Activity, Globe, ShieldBan, ShieldCheck, EyeOff, Check } from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import api from "../services/api";
import type { AiInsight, ThreatStats, BlockedIp } from "../types";

const severityConfig = {
  critical: {
    icon: Shield,
    variant: "red" as const,
    label: "KRITIK",
    color: "text-neon-red",
  },
  warning: {
    icon: AlertTriangle,
    variant: "amber" as const,
    label: "UYARI",
    color: "text-neon-amber",
  },
  info: {
    icon: Info,
    variant: "cyan" as const,
    label: "BILGI",
    color: "text-neon-cyan",
  },
};

export function InsightsPage() {
  const { connected } = useWebSocket();
  const [insights, setInsights] = useState<AiInsight[]>([]);
  const [threatStats, setThreatStats] = useState<ThreatStats | null>(null);
  const [blockedIps, setBlockedIps] = useState<BlockedIp[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [actionDone, setActionDone] = useState<Record<string, string>>({});

  // Mesajdan IP adresi cikart
  const extractIp = (text: string): string | null => {
    const match = text.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/);
    return match ? match[1] : null;
  };

  const handleBlockIp = async (insightId: number, ip: string) => {
    const key = `block-${insightId}`;
    setActionLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await api.post("/insights/block-ip", { ip, reason: "Insight üzerinden manuel engelleme" });
      setActionDone((prev) => ({ ...prev, [insightId]: "blocked" }));
      await loadData();
    } catch (err) {
      console.error("IP engellenemedi:", err);
    } finally {
      setActionLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleUnblockIp = async (insightId: number, ip: string) => {
    const key = `unblock-${insightId}`;
    setActionLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await api.post("/insights/unblock-ip", { ip });
      setActionDone((prev) => ({ ...prev, [insightId]: "unblocked" }));
      await loadData();
    } catch (err) {
      console.error("IP engeli kaldirilamadi:", err);
    } finally {
      setActionLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleDismiss = async (insightId: number) => {
    const key = `dismiss-${insightId}`;
    setActionLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await api.post(`/insights/${insightId}/dismiss`);
      setActionDone((prev) => ({ ...prev, [insightId]: "dismissed" }));
      // Kısa bir gecikme ile listeden kaldir (animasyon için)
      setTimeout(() => {
        setInsights((prev) => prev.filter((i) => i.id !== insightId));
        setActionDone((prev) => {
          const next = { ...prev };
          delete next[insightId];
          return next;
        });
      }, 800);
    } catch (err) {
      console.error("Insight gormezden gelinemedi:", err);
    } finally {
      setActionLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const loadData = useCallback(async () => {
    try {
      const [insightsRes, statsRes, ipsRes] = await Promise.all([
        api.get("/insights/?limit=100"),
        api.get("/insights/threat-stats"),
        api.get("/insights/blocked-ips"),
      ]);
      setInsights(insightsRes.data);
      setThreatStats(statsRes.data);
      setBlockedIps(ipsRes.data);
    } catch (err) {
      console.error("Veri alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleUnblock = async (ip: string) => {
    try {
      await api.post("/insights/unblock-ip", { ip });
      await loadData();
    } catch (err) {
      console.error("IP engeli kaldirilamadi:", err);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar title="AI Insights" connected={connected} />

      {/* Tehdit İstatistik Kartlari */}
      {threatStats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassCard>
            <div className="flex items-center gap-3">
              <Ban size={20} className="text-neon-red" />
              <div>
                <p className="text-2xl font-bold text-neon-red">
                  {threatStats.blocked_ip_count}
                </p>
                <p className="text-xs text-gray-400">Engelli IP</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="flex items-center gap-3">
              <Shield size={20} className="text-neon-amber" />
              <div>
                <p className="text-2xl font-bold text-neon-amber">
                  {threatStats.total_auto_blocks}
                </p>
                <p className="text-xs text-gray-400">Otomatik Engel</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="flex items-center gap-3">
              <Activity size={20} className="text-neon-cyan" />
              <div>
                <p className="text-2xl font-bold text-neon-cyan">
                  {threatStats.total_suspicious}
                </p>
                <p className="text-xs text-gray-400">Şüpheli Sorgu</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="flex items-center gap-3">
              <Globe size={20} className="text-gray-400" />
              <div>
                <p className="text-2xl font-bold">
                  {threatStats.total_external_blocked}
                </p>
                <p className="text-xs text-gray-400">Dış Sorgu Reddedildi</p>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Engellenen IP Listesi */}
      {blockedIps.length > 0 && (
        <GlassCard>
          <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Ban size={16} className="text-neon-red" />
            Engellenen IP Adresleri ({blockedIps.length})
          </h3>
          <div className="space-y-2">
            {blockedIps.map((item) => (
              <div
                key={item.ip}
                className="flex items-center justify-between bg-dark-800/50 rounded-lg px-3 py-2"
              >
                <div>
                  <span className="font-mono text-sm text-neon-red">{item.ip}</span>
                  <span className="text-xs text-gray-500 ml-3">{item.reason}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">
                    {Math.floor(item.remaining_seconds / 60)} dk
                  </span>
                  <button
                    onClick={() => handleUnblock(item.ip)}
                    className="text-xs px-2 py-1 rounded bg-dark-700 hover:bg-dark-600
                             text-gray-300 hover:text-neon-cyan transition-colors
                             flex items-center gap-1"
                  >
                    <Unlock size={12} />
                    Kaldir
                  </button>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Insight Akışı */}
      <div className="flex items-center gap-3 mb-4">
        <Brain size={24} className="text-neon-cyan" />
        <p className="text-gray-400 text-sm">
          {insights.length} içgörü tespit edildi
        </p>
      </div>

      <div className="space-y-3">
        {insights.length === 0 && (
          <GlassCard>
            <p className="text-gray-500 text-sm text-center py-4">
              Henüz bir tehdit veya içgörü tespit edilmedi.
            </p>
          </GlassCard>
        )}
        {insights.map((insight) => {
          const config = severityConfig[insight.severity];
          const Icon = config.icon;

          return (
            <GlassCard key={insight.id} hoverable>
              <div className="flex items-start gap-4">
                <Icon size={20} className={`${config.color} mt-0.5 flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <NeonBadge
                      label={config.label}
                      variant={config.variant}
                      pulse={insight.severity === "critical"}
                    />
                    {insight.category && (
                      <span className="text-xs text-gray-500">
                        {insight.category}
                      </span>
                    )}
                    <span className="text-xs text-gray-600 ml-auto">
                      {insight.timestamp
                        ? new Date(insight.timestamp).toLocaleString("tr-TR")
                        : ""}
                    </span>
                  </div>
                  <p className="text-sm">{insight.message}</p>
                  {insight.suggested_action && (
                    <p className="text-xs text-gray-400 mt-2 border-l-2 border-neon-cyan/30 pl-3">
                      Önerilen Aksiyon: {insight.suggested_action}
                    </p>
                  )}

                  {/* Aksiyon Butonlari */}
                  {actionDone[insight.id] ? (
                    <div className="flex items-center gap-2 mt-3 text-xs">
                      <Check size={14} className="text-neon-green" />
                      <span className="text-neon-green">
                        {actionDone[insight.id] === "blocked" && "IP engellendi"}
                        {actionDone[insight.id] === "unblocked" && "IP engeli kaldırıldı"}
                        {actionDone[insight.id] === "dismissed" && "Gormezden gelindi"}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {(() => {
                        const ip = extractIp(insight.message);
                        return ip ? (
                          <>
                            <button
                              onClick={() => handleBlockIp(insight.id, ip)}
                              disabled={!!actionLoading[`block-${insight.id}`]}
                              className="text-xs px-3 py-1.5 rounded-lg
                                       bg-neon-red/10 border border-neon-red/30
                                       hover:bg-neon-red/20 hover:border-neon-red/50
                                       text-neon-red transition-all
                                       flex items-center gap-1.5
                                       disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ShieldBan size={13} />
                              {actionLoading[`block-${insight.id}`] ? "Engelleniyor..." : `${ip} Engelle`}
                            </button>
                            <button
                              onClick={() => handleUnblockIp(insight.id, ip)}
                              disabled={!!actionLoading[`unblock-${insight.id}`]}
                              className="text-xs px-3 py-1.5 rounded-lg
                                       bg-neon-green/10 border border-neon-green/30
                                       hover:bg-neon-green/20 hover:border-neon-green/50
                                       text-neon-green transition-all
                                       flex items-center gap-1.5
                                       disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ShieldCheck size={13} />
                              {actionLoading[`unblock-${insight.id}`] ? "Kaldiriliyor..." : "Engeli Kaldir"}
                            </button>
                          </>
                        ) : null;
                      })()}
                      <button
                        onClick={() => handleDismiss(insight.id)}
                        disabled={!!actionLoading[`dismiss-${insight.id}`]}
                        className="text-xs px-3 py-1.5 rounded-lg
                                 bg-dark-700/50 border border-gray-600/30
                                 hover:bg-dark-600/50 hover:border-gray-500/50
                                 text-gray-400 hover:text-gray-300 transition-all
                                 flex items-center gap-1.5
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <EyeOff size={13} />
                        {actionLoading[`dismiss-${insight.id}`] ? "..." : "Gormezden Gel"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>
    </div>
  );
}
