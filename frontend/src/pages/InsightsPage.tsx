// --- Ajan: INSAATCI (THE CONSTRUCTOR) + ANALIST (THE ANALYST) ---
// AI Insights sayfası: tehdit paneli + trend grafik + domain reputation + filtreli insight akışı

import { useEffect, useState, useCallback } from "react";
import {
  AlertTriangle,
  Shield,
  Info,
  Brain,
  Ban,
  Unlock,
  Activity,
  Globe,
  ShieldBan,
  ShieldCheck,
  EyeOff,
  Check,
  ChevronDown,
  ChevronUp,
  Search,
  TrendingUp,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import api from "../services/api";
import type { AiInsight, ThreatStats, BlockedIp } from "../types";

// ---- Tip Tanımlamaları ----

interface HourlyTrend {
  hour_key: string; // "2026-03-12T14:00"
  total_queries: number;
  blocked_queries: number;
  suspicious_queries: number;
}

interface HourlyTrendsResponse {
  hours: number;
  trends: HourlyTrend[];
}

interface DomainReputationResponse {
  domain: string;
  score: number; // 0-100
  risk_level: "clean" | "suspicious" | "malicious" | string;
  factors: string[];
}

// ---- Yardımcı Fonksiyonlar ----

function relativeTime(timestamp: string | null): string {
  if (!timestamp) return "";
  const now = Date.now();
  const ts = new Date(timestamp).getTime();
  const diffMs = now - ts;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "az önce";
  if (diffMin < 60) return `${diffMin} dk önce`;
  if (diffHour < 24) return `${diffHour} saat önce`;
  if (diffDay === 1) return "dün";
  return `${diffDay} gün önce`;
}

function formatHourLabel(hourKey: string): string {
  // "2026-03-12T14:00" → "14:00"
  try {
    const parts = hourKey.split("T");
    if (parts.length === 2) return parts[1].substring(0, 5);
    return hourKey.substring(11, 16);
  } catch {
    return hourKey;
  }
}

function getReputationColor(score: number): string {
  if (score <= 20) return "#39FF14"; // neon-green
  if (score <= 60) return "#FFB800"; // neon-amber
  return "#FF003C"; // neon-red
}

function getReputationLabel(score: number): string {
  if (score <= 20) return "Temiz";
  if (score <= 60) return "Şüpheli";
  return "Tehlikeli";
}

function getReputationVariant(score: number): "green" | "amber" | "red" {
  if (score <= 20) return "green";
  if (score <= 60) return "amber";
  return "red";
}

// ---- Sabit Yapılandırmalar ----

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

type SeverityFilter = "all" | "critical" | "warning" | "info";

// ---- Ana Bileşen ----

export function InsightsPage() {
  const { connected } = useWebSocket();

  // Temel veriler
  const [insights, setInsights] = useState<AiInsight[]>([]);
  const [threatStats, setThreatStats] = useState<ThreatStats | null>(null);
  const [blockedIps, setBlockedIps] = useState<BlockedIp[]>([]);
  const [loading, setLoading] = useState(true);

  // Saatlik trend
  const [hourlyTrends, setHourlyTrends] = useState<HourlyTrend[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(true);

  // Domain reputation
  const [domainQuery, setDomainQuery] = useState("");
  const [domainResult, setDomainResult] = useState<DomainReputationResponse | null>(null);
  const [domainLoading, setDomainLoading] = useState(false);
  const [domainError, setDomainError] = useState<string | null>(null);

  // UI durumu
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [blockedIpsExpanded, setBlockedIpsExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [actionDone, setActionDone] = useState<Record<string, string>>({});

  // ---- Veri Yükleme ----

  const extractIp = (text: string): string | null => {
    const match = text.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/);
    return match ? match[1] : null;
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

  const loadTrends = useCallback(async () => {
    try {
      setTrendsLoading(true);
      const res = await api.get<HourlyTrendsResponse>("/insights/hourly-trends?hours=24");
      setHourlyTrends(res.data.trends || []);
    } catch (err) {
      console.error("Saatlik trend alinamadi:", err);
      setHourlyTrends([]);
    } finally {
      setTrendsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadTrends();
    const interval = setInterval(loadData, 10000);
    const trendInterval = setInterval(loadTrends, 60000);
    return () => {
      clearInterval(interval);
      clearInterval(trendInterval);
    };
  }, [loadData, loadTrends]);

  // ---- Domain Reputation Sorgulama ----

  const handleDomainSearch = async () => {
    const q = domainQuery.trim();
    if (!q) return;
    setDomainLoading(true);
    setDomainError(null);
    setDomainResult(null);
    try {
      const res = await api.get<DomainReputationResponse>(`/insights/domain-reputation/${encodeURIComponent(q)}`);
      setDomainResult(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setDomainError(axiosErr?.response?.data?.detail || "Domain sorgulanamadı");
    } finally {
      setDomainLoading(false);
    }
  };

  // ---- Insight Aksiyonları ----

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

  const handleUnblock = async (ip: string) => {
    try {
      await api.post("/insights/unblock-ip", { ip });
      await loadData();
    } catch (err) {
      console.error("IP engeli kaldirilamadi:", err);
    }
  };

  // ---- Filtrelenmiş Insight'lar ----

  const filteredInsights = insights.filter((ins) => {
    if (severityFilter === "all") return true;
    return ins.severity === severityFilter;
  });

  const countBySeverity = (sev: AiInsight["severity"]) =>
    insights.filter((i) => i.severity === sev).length;

  // ---- Grafik Verisi Hazırlama ----

  const chartData = hourlyTrends.map((t) => ({
    hour: formatHourLabel(t.hour_key),
    Toplam: t.total_queries,
    Engellenen: t.blocked_queries,
    Şüpheli: t.suspicious_queries,
  }));

  // ---- Render ----

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar title="AI Insights" connected={connected} />

      {/* --- 1) Özet İstatistik Kartları (kompakt, tek satır) --- */}
      {threatStats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <GlassCard className="py-3 px-4">
            <div className="flex items-center gap-2">
              <Ban size={16} className="text-neon-red flex-shrink-0" />
              <div>
                <p className="text-xl font-bold text-neon-red leading-none">{threatStats.blocked_ip_count}</p>
                <p className="text-xs text-gray-400 mt-0.5">Engelli IP</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard className="py-3 px-4">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-neon-amber flex-shrink-0" />
              <div>
                <p className="text-xl font-bold text-neon-amber leading-none">{threatStats.total_auto_blocks}</p>
                <p className="text-xs text-gray-400 mt-0.5">Otomatik Engel</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard className="py-3 px-4">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-neon-cyan flex-shrink-0" />
              <div>
                <p className="text-xl font-bold text-neon-cyan leading-none">{threatStats.total_suspicious}</p>
                <p className="text-xs text-gray-400 mt-0.5">Şüpheli Sorgu</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard className="py-3 px-4">
            <div className="flex items-center gap-2">
              <Globe size={16} className="text-gray-400 flex-shrink-0" />
              <div>
                <p className="text-xl font-bold leading-none">{threatStats.total_external_blocked}</p>
                <p className="text-xs text-gray-400 mt-0.5">Dış Sorgu Reddedildi</p>
              </div>
            </div>
            {threatStats.last_threat_time && (
              <p className="text-[10px] text-gray-600 mt-1.5 truncate">
                Son: {relativeTime(threatStats.last_threat_time)}
              </p>
            )}
          </GlassCard>
        </div>
      )}

      {/* --- 2) Saatlik Trend Grafik --- */}
      <GlassCard>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={18} className="text-neon-cyan" />
          <h3 className="text-sm font-semibold text-neon-cyan">Son 24 Saat DNS Tehdit Trendi</h3>
        </div>
        {trendsLoading ? (
          <div className="h-48 flex items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : chartData.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-10">Trend verisi bulunamadı.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00F0FF" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00F0FF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradBlocked" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF003C" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FF003C" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradSuspicious" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FFB800" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FFB800" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="hour"
                stroke="#555"
                fontSize={11}
                tickFormatter={(v) => v}
                interval={Math.floor(chartData.length / 8)}
              />
              <YAxis stroke="#555" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(18, 18, 26, 0.95)",
                  border: "1px solid rgba(0, 240, 255, 0.3)",
                  borderRadius: "10px",
                  color: "#fff",
                  fontSize: "12px",
                }}
              />
              <Area
                type="monotone"
                dataKey="Toplam"
                stroke="#00F0FF"
                strokeWidth={1.5}
                fill="url(#gradTotal)"
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="Engellenen"
                stroke="#FF003C"
                strokeWidth={1.5}
                fill="url(#gradBlocked)"
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="Şüpheli"
                stroke="#FFB800"
                strokeWidth={1.5}
                fill="url(#gradSuspicious)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
        {/* Grafik Açıklaması */}
        <div className="flex items-center gap-4 mt-2 pl-1">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#00F0FF] inline-block rounded" />
            <span className="text-xs text-gray-400">Toplam</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#FF003C] inline-block rounded" />
            <span className="text-xs text-gray-400">Engellenen</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#FFB800] inline-block rounded" />
            <span className="text-xs text-gray-400">Şüpheli</span>
          </div>
        </div>
      </GlassCard>

      {/* --- 3) Domain Reputation Sorgulama --- */}
      <GlassCard>
        <div className="flex items-center gap-2 mb-4">
          <Search size={18} className="text-neon-magenta" />
          <h3 className="text-sm font-semibold text-neon-magenta">Domain İtibar Sorgulama</h3>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={domainQuery}
            onChange={(e) => setDomainQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleDomainSearch()}
            placeholder="örn: malware.example.com"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2
                       text-sm text-white placeholder-gray-500
                       focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/20
                       transition-colors"
          />
          <button
            onClick={handleDomainSearch}
            disabled={domainLoading || !domainQuery.trim()}
            className="px-4 py-2 rounded-lg text-sm font-medium
                       bg-neon-magenta/10 border border-neon-magenta/30
                       hover:bg-neon-magenta/20 hover:border-neon-magenta/50
                       text-neon-magenta transition-all
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center gap-1.5"
          >
            <Search size={14} />
            {domainLoading ? "Sorgulanıyor..." : "Sorgula"}
          </button>
        </div>

        {domainError && (
          <p className="mt-3 text-sm text-neon-red">{domainError}</p>
        )}

        {domainResult && (
          <div className="mt-4 p-4 bg-white/5 rounded-xl border border-white/10 space-y-3">
            {/* Domain + Risk Seviyesi */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="font-mono text-sm text-white">{domainResult.domain}</span>
              <NeonBadge
                label={getReputationLabel(domainResult.score)}
                variant={getReputationVariant(domainResult.score)}
                pulse={domainResult.score > 60}
              />
            </div>

            {/* Skor Çubuğu */}
            <div>
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>İtibar Skoru</span>
                <span style={{ color: getReputationColor(domainResult.score) }}>
                  {domainResult.score} / 100
                </span>
              </div>
              <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${domainResult.score}%`,
                    backgroundColor: getReputationColor(domainResult.score),
                    boxShadow: `0 0 8px ${getReputationColor(domainResult.score)}80`,
                  }}
                />
              </div>
            </div>

            {/* Faktörler */}
            {domainResult.factors && domainResult.factors.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-1.5">Tespit Edilen Faktörler:</p>
                <div className="flex flex-wrap gap-1.5">
                  {domainResult.factors.map((factor, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 rounded-full
                                 bg-white/5 border border-white/10 text-gray-300"
                    >
                      {factor}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </GlassCard>

      {/* --- 4) Engellenen IP Bölümü (Açılır/Kapanır) --- */}
      {blockedIps.length > 0 && (
        <GlassCard>
          <button
            onClick={() => setBlockedIpsExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Ban size={16} className="text-neon-red" />
              Engellenen IP Adresleri
              <span className="ml-1 px-2 py-0.5 rounded-full text-xs
                             bg-neon-red/10 border border-neon-red/30 text-neon-red">
                {blockedIps.length}
              </span>
            </h3>
            {blockedIpsExpanded ? (
              <ChevronUp size={16} className="text-gray-400" />
            ) : (
              <ChevronDown size={16} className="text-gray-400" />
            )}
          </button>

          {blockedIpsExpanded && (
            <div className="mt-3 space-y-2">
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
          )}
        </GlassCard>
      )}

      {/* --- 5) Insight Akışı Başlığı + Filtre Tabları --- */}
      <div className="space-y-3">
        {/* Başlık */}
        <div className="flex items-center gap-3">
          <Brain size={22} className="text-neon-cyan" />
          <h2 className="text-base font-semibold">AI İçgörü Akışı</h2>
          <span className="text-gray-400 text-sm">{insights.length} içgörü</span>
        </div>

        {/* Severity Filtre Tabları */}
        <div className="flex items-center gap-2 flex-wrap">
          {(
            [
              { key: "all", label: "Tümü", count: insights.length },
              { key: "critical", label: "Kritik", count: countBySeverity("critical") },
              { key: "warning", label: "Uyarı", count: countBySeverity("warning") },
              { key: "info", label: "Bilgi", count: countBySeverity("info") },
            ] as { key: SeverityFilter; label: string; count: number }[]
          ).map((tab) => {
            const isActive = severityFilter === tab.key;
            const colorMap: Record<SeverityFilter, string> = {
              all: "neon-cyan",
              critical: "neon-red",
              warning: "neon-amber",
              info: "neon-cyan",
            };
            const col = colorMap[tab.key];

            return (
              <button
                key={tab.key}
                onClick={() => setSeverityFilter(tab.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                           border transition-all
                           ${isActive
                             ? `bg-${col}/10 border-${col}/50 text-${col} shadow-[0_0_10px_rgba(0,240,255,0.15)]`
                             : "bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-200"
                           }`}
              >
                {tab.label}
                <span
                  className={`px-1.5 py-0.5 rounded-full text-xs
                             ${isActive ? `bg-${col}/20` : "bg-white/10"}`}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* --- 6) Insight Listesi --- */}
      <div className="space-y-3">
        {filteredInsights.length === 0 && (
          <GlassCard>
            <p className="text-gray-500 text-sm text-center py-6">
              {severityFilter === "all"
                ? "Henüz bir tehdit veya içgörü tespit edilmedi."
                : `Bu kategoride içgörü bulunamadı.`}
            </p>
          </GlassCard>
        )}
        {filteredInsights.map((insight) => {
          const config = severityConfig[insight.severity];
          const Icon = config.icon;

          return (
            <GlassCard key={insight.id} hoverable>
              <div className="flex items-start gap-4">
                <Icon size={18} className={`${config.color} mt-0.5 flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  {/* Üst Satır: severity + category + zaman */}
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <NeonBadge
                      label={config.label}
                      variant={config.variant}
                      pulse={insight.severity === "critical"}
                    />
                    {insight.category && (
                      <span className="text-xs px-2 py-0.5 rounded-full
                                     bg-white/5 border border-white/10 text-gray-400">
                        {insight.category}
                      </span>
                    )}
                    <span className="text-xs text-gray-500 ml-auto" title={
                      insight.timestamp
                        ? new Date(insight.timestamp).toLocaleString("tr-TR")
                        : ""
                    }>
                      {relativeTime(insight.timestamp)}
                    </span>
                  </div>

                  {/* Mesaj */}
                  <p className="text-sm leading-relaxed">{insight.message}</p>

                  {/* Önerilen Aksiyon */}
                  {insight.suggested_action && (
                    <p className="text-xs text-gray-400 mt-2 border-l-2 border-neon-cyan/30 pl-3">
                      Önerilen Aksiyon: {insight.suggested_action}
                    </p>
                  )}

                  {/* Aksiyon Butonları */}
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
