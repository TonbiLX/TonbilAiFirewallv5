// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Trafik sayfasi: per-flow baglanti takibi (3 tab: Canli, Buyuk Transferler, Gecmis)

import { useEffect, useState, useCallback, useRef } from "react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { StatCard } from "../components/common/StatCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchLiveFlows,
  fetchLargeTransfers,
  fetchFlowHistory,
  fetchFlowStats,
} from "../services/trafficApi";
import type { LiveFlow, FlowStats, FlowHistoryResponse } from "../types";
import {
  Activity,
  ArrowDownCircle,
  ArrowUpCircle,
  Download,
  Upload,
  Monitor,
  Zap,
  Clock,
  Filter,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react";

// ─── Yardimci Fonksiyonlar ──────────────────────────────────

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatBps(bps: number): string {
  if (!bps || bps === 0) return "0 bps";
  const k = 1000;
  const sizes = ["bps", "Kbps", "Mbps", "Gbps"];
  const i = Math.floor(Math.log(bps) / Math.log(k));
  return parseFloat((bps / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

const stateColor: Record<string, string> = {
  ESTABLISHED: "text-neon-green",
  TIME_WAIT: "text-gray-500",
  CLOSE_WAIT: "text-gray-500",
  SYN_SENT: "text-yellow-400",
  SYN_RECV: "text-yellow-400",
  FIN_WAIT: "text-gray-400",
  CLOSE: "text-gray-600",
  LAST_ACK: "text-gray-500",
};

const categoryVariant: Record<
  string,
  "cyan" | "magenta" | "green" | "amber" | "red"
> = {
  streaming: "magenta",
  social: "cyan",
  education: "green",
  gambling: "red",
  malicious: "red",
  search: "cyan",
  development: "green",
  gaming: "amber",
  news: "cyan",
  communication: "amber",
  shopping: "magenta",
  technology: "cyan",
};

type ActiveTab = "live" | "large" | "history";

const HISTORY_PERIODS = [
  { label: "1s", hours: 1 },
  { label: "6s", hours: 6 },
  { label: "24s", hours: 24 },
  { label: "7g", hours: 168 },
];

// ─── Ana Bilesen ──────────────────────────────────────────────

export function TrafficPage() {
  const { connected } = useWebSocket();
  const [activeTab, setActiveTab] = useState<ActiveTab>("live");
  const [loading, setLoading] = useState(true);

  // Stat kartlari
  const [stats, setStats] = useState<FlowStats | null>(null);

  // Canli akislar
  const [liveFlows, setLiveFlows] = useState<LiveFlow[]>([]);
  const [liveProtocol, setLiveProtocol] = useState("");
  const [liveSearchText, setLiveSearchText] = useState("");
  const [liveDomainFilter, setLiveDomainFilter] = useState("");

  // Buyuk transferler
  const [largeTransfers, setLargeTransfers] = useState<LiveFlow[]>([]);

  // Gecmis
  const [historyData, setHistoryData] = useState<FlowHistoryResponse | null>(
    null
  );
  const [historyPage, setHistoryPage] = useState(0);
  const [historyPeriod, setHistoryPeriod] = useState(24);
  const [historyProtocol, setHistoryProtocol] = useState("");
  const [historySearchText, setHistorySearchText] = useState("");
  const [historyDomainFilter, setHistoryDomainFilter] = useState("");

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ─── Debounce: arama metni -> filtre ──────────────────────

  useEffect(() => {
    const timer = setTimeout(() => setLiveDomainFilter(liveSearchText), 400);
    return () => clearTimeout(timer);
  }, [liveSearchText]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setHistoryDomainFilter(historySearchText);
      setHistoryPage(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [historySearchText]);

  // ─── Veri Yukleme ──────────────────────────────────────────

  const loadStats = useCallback(async () => {
    try {
      const { data } = await fetchFlowStats();
      setStats(data);
    } catch {
      /* quiet */
    }
  }, []);

  const loadLive = useCallback(async () => {
    try {
      const params: Record<string, unknown> = { sort: "bytes_desc" };
      if (liveProtocol) params.protocol = liveProtocol;
      if (liveDomainFilter) params.dst_domain = liveDomainFilter;
      const { data } = await fetchLiveFlows(
        params as Parameters<typeof fetchLiveFlows>[0]
      );
      setLiveFlows(data);
    } catch {
      /* quiet */
    } finally {
      setLoading(false);
    }
  }, [liveProtocol, liveDomainFilter]);

  const loadLarge = useCallback(async () => {
    try {
      const { data } = await fetchLargeTransfers();
      setLargeTransfers(data);
    } catch {
      /* quiet */
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const params: Record<string, unknown> = {
        hours: historyPeriod,
        limit: 50,
        offset: historyPage * 50,
      };
      if (historyProtocol) params.protocol = historyProtocol;
      if (historyDomainFilter) params.dst_domain = historyDomainFilter;
      const { data } = await fetchFlowHistory(
        params as Parameters<typeof fetchFlowHistory>[0]
      );
      setHistoryData(data);
    } catch {
      /* quiet */
    } finally {
      setLoading(false);
    }
  }, [historyPeriod, historyPage, historyProtocol, historyDomainFilter]);

  // ─── Otomatik Yenileme ─────────────────────────────────────

  useEffect(() => {
    loadStats();
    const statInterval = setInterval(loadStats, 5000);
    return () => clearInterval(statInterval);
  }, [loadStats]);

  useEffect(() => {
    // Tab degisince ilk yukleme
    setLoading(true);
    if (activeTab === "live") {
      loadLive();
    } else if (activeTab === "large") {
      loadLarge();
    } else {
      loadHistory();
    }

    // Otomatik yenileme
    if (intervalRef.current) clearInterval(intervalRef.current);

    const refreshMs =
      activeTab === "large" ? 3000 : activeTab === "live" ? 5000 : 15000;
    const loader =
      activeTab === "live"
        ? loadLive
        : activeTab === "large"
          ? loadLarge
          : loadHistory;

    intervalRef.current = setInterval(loader, refreshMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [activeTab, loadLive, loadLarge, loadHistory]);

  // ─── Tab Stili ─────────────────────────────────────────────

  const tabClass = (tab: ActiveTab) =>
    `flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
      activeTab === tab
        ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
        : "text-gray-400 bg-glass-light border border-glass-border hover:text-white"
    }`;

  // ─── Yenile butonu handler ──────────────────────────────────

  const handleRefresh = () => {
    if (activeTab === "live") loadLive();
    else if (activeTab === "large") loadLarge();
    else loadHistory();
    loadStats();
  };

  // ─── Flow Satiri Render ─────────────────────────────────────

  const renderFlowRow = (flow: LiveFlow, showEnded = false) => {
    const bytesTotal = flow.bytes_sent + flow.bytes_received;
    const isLarge = bytesTotal >= 10_000_000; // 10MB

    return (
      <tr
        key={flow.flow_id + (flow.ended_at || "")}
        className="border-b border-glass-border/30 hover:bg-glass-light/50 transition-colors"
      >
        {/* Cihaz */}
        <td className="py-2.5 pr-3 text-xs">
          <div>
            <span className="text-white">
              {flow.device_hostname || flow.src_ip}
            </span>
            {flow.device_hostname && (
              <span className="block text-gray-500 font-mono text-[10px]">
                {flow.src_ip}
              </span>
            )}
          </div>
        </td>

        {/* Yon */}
        <td className="py-2.5 pr-2 text-center" title={flow.direction === "inbound" ? "Gelen" : "Giden"}>
          {flow.direction === "inbound" ? (
            <ArrowDownLeft size={15} className="text-neon-magenta inline-block" />
          ) : (
            <ArrowUpRight size={15} className="text-neon-cyan inline-block" />
          )}
        </td>

        {/* Hedef */}
        <td className="py-2.5 pr-3 font-mono text-xs">
          <div>
            <span className="text-gray-200">
              {flow.dst_domain || flow.dst_ip}
            </span>
            <span className="text-gray-500">:{flow.dst_port}</span>
            {flow.dst_domain && flow.dst_domain !== flow.dst_ip && (
              <span className="block text-gray-600 text-[10px]">
                {flow.dst_ip}
              </span>
            )}
          </div>
        </td>

        {/* Protokol */}
        <td className="py-2.5 pr-3 text-xs text-gray-400">
          {flow.protocol}
        </td>

        {/* Uygulama */}
        <td className="py-2.5 pr-3 text-xs">
          {flow.app_name ? (
            <NeonBadge
              label={flow.app_name}
              variant={categoryVariant[flow.category || ""] || "cyan"}
            />
          ) : flow.service_name ? (
            <span className="text-gray-400">{flow.service_name}</span>
          ) : (
            <span className="text-gray-600">--</span>
          )}
        </td>

        {/* Durum */}
        <td className="py-2.5 pr-3 text-xs">
          {flow.state ? (
            <span
              className={`font-mono ${stateColor[flow.state] || "text-gray-400"}`}
            >
              {flow.state}
            </span>
          ) : (
            <span className="text-gray-600">--</span>
          )}
        </td>

        {/* Gonderilen */}
        <td className="py-2.5 pr-3 text-xs text-right">
          <span className="text-cyan-400">
            {formatBytes(flow.bytes_sent)}
          </span>
        </td>

        {/* Alinan */}
        <td className="py-2.5 pr-3 text-xs text-right">
          <span className="text-neon-magenta">
            {formatBytes(flow.bytes_received)}
          </span>
        </td>

        {/* Toplam */}
        <td className="py-2.5 pr-3 text-xs text-right">
          {isLarge ? (
            <span className="text-neon-magenta font-semibold animate-pulse">
              {formatBytes(bytesTotal)}
            </span>
          ) : (
            <span className="text-gray-300">{formatBytes(bytesTotal)}</span>
          )}
        </td>

        {/* Hiz */}
        <td className="py-2.5 pr-3 text-xs text-right">
          {!showEnded && (flow.bps_in > 0 || flow.bps_out > 0) ? (
            <div>
              <span className="text-neon-magenta text-[10px]">
                {formatBps(flow.bps_in)}
              </span>
              <span className="text-gray-600 mx-0.5">/</span>
              <span className="text-cyan-400 text-[10px]">
                {formatBps(flow.bps_out)}
              </span>
            </div>
          ) : (
            <span className="text-gray-600">--</span>
          )}
        </td>

        {/* Kategori */}
        <td className="py-2.5 text-xs">
          {flow.category && (
            <NeonBadge
              label={flow.category}
              variant={categoryVariant[flow.category] || "cyan"}
            />
          )}
        </td>

        {/* Bitis (sadece gecmis) */}
        {showEnded && (
          <td className="py-2.5 pl-3 text-xs text-gray-500 font-mono">
            {flow.ended_at
              ? new Date(flow.ended_at).toLocaleTimeString("tr-TR")
              : "aktif"}
          </td>
        )}
      </tr>
    );
  };

  // ─── Tablo Header ────────────────────────────────────────────

  const renderTableHeader = (showEnded = false) => (
    <thead>
      <tr className="text-left text-gray-400 border-b border-glass-border text-xs uppercase tracking-wider">
        <th className="pb-2 pr-3">Cihaz</th>
        <th className="pb-2 pr-2 text-center w-8">Yon</th>
        <th className="pb-2 pr-3">Hedef</th>
        <th className="pb-2 pr-3">Proto</th>
        <th className="pb-2 pr-3">Uygulama</th>
        <th className="pb-2 pr-3">Durum</th>
        <th className="pb-2 pr-3 text-right">
          <Upload size={12} className="inline mr-1" />
          Giden
        </th>
        <th className="pb-2 pr-3 text-right">
          <Download size={12} className="inline mr-1" />
          Gelen
        </th>
        <th className="pb-2 pr-3 text-right">Toplam</th>
        <th className="pb-2 pr-3 text-right">Hiz</th>
        <th className="pb-2">Kategori</th>
        {showEnded && <th className="pb-2 pl-3">Bitis</th>}
      </tr>
    </thead>
  );

  // ─── Render ─────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <TopBar title="Trafik Akislari" connected={connected} />

      {/* Ozet Kartlar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard
            title="Aktif Akis"
            value={stats.total_active_flows}
            icon={<Activity size={28} />}
            neonColor="cyan"
          />
          <StatCard
            title="Toplam Gelen"
            value={formatBytes(stats.total_bytes_in)}
            icon={<ArrowDownCircle size={28} />}
            neonColor="magenta"
          />
          <StatCard
            title="Toplam Giden"
            value={formatBytes(stats.total_bytes_out)}
            icon={<ArrowUpCircle size={28} />}
            neonColor="cyan"
          />
          <StatCard
            title="Buyuk Transfer"
            value={stats.large_transfer_count}
            icon={<Zap size={28} />}
            neonColor="amber"
          />
          <StatCard
            title="Aktif Cihaz"
            value={stats.total_devices_with_flows}
            icon={<Monitor size={28} />}
            neonColor="green"
          />
        </div>
      )}

      {/* Tab Butonlari */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab("live")}
          className={tabClass("live")}
        >
          <Activity size={16} />
          Canli Akislar
        </button>
        <button
          onClick={() => setActiveTab("large")}
          className={tabClass("large")}
        >
          <Zap size={16} />
          Buyuk Transferler
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={tabClass("history")}
        >
          <Clock size={16} />
          Gecmis
        </button>
      </div>

      {/* Tab Icerigi */}
      {loading ? (
        <LoadingSpinner />
      ) : (
        <>
          {/* ─── Tab 1: Canli Akislar ─── */}
          {activeTab === "live" && (
            <GlassCard>
              {/* Filtre + Yenile */}
              <div className="flex flex-wrap gap-3 items-center mb-4">
                <div className="flex items-center gap-1.5 text-gray-400 text-xs">
                  <Filter size={14} />
                  <span>Filtre:</span>
                </div>
                <select
                  value={liveProtocol}
                  onChange={(e) => setLiveProtocol(e.target.value)}
                  className="bg-glass-light border border-glass-border text-white text-xs rounded-lg px-3 py-1.5 focus:border-neon-cyan/50 outline-none"
                >
                  <option value="">Tum Protokoller</option>
                  <option value="TCP">TCP</option>
                  <option value="UDP">UDP</option>
                </select>
                <input
                  type="text"
                  placeholder="Domain ara..."
                  value={liveSearchText}
                  onChange={(e) => setLiveSearchText(e.target.value)}
                  className="bg-glass-light border border-glass-border text-white text-xs rounded-lg px-3 py-1.5 w-48 focus:border-neon-cyan/50 outline-none placeholder-gray-500"
                />
                <div className="flex-1" />
                <button
                  onClick={handleRefresh}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-neon-cyan bg-glass-light border border-glass-border hover:border-neon-cyan/30 transition-all"
                  title="Yenile"
                >
                  <RefreshCw size={13} />
                  Yenile
                </button>
              </div>

              {liveFlows.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Activity size={48} className="mx-auto mb-3 opacity-30" />
                  <p>Aktif akis bulunamadi</p>
                  <p className="text-xs mt-1">
                    Conntrack verileri bekleniyor...
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    {renderTableHeader()}
                    <tbody>
                      {liveFlows.map((flow) => renderFlowRow(flow))}
                    </tbody>
                  </table>
                  <div className="mt-3 text-xs text-gray-500 text-right">
                    {liveFlows.length} aktif akis | 5 saniyede yenileniyor
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {/* ─── Tab 2: Buyuk Transferler ─── */}
          {activeTab === "large" && (
            <GlassCard>
              {/* Yenile butonu */}
              <div className="flex items-center justify-between mb-4">
                <div />
                <button
                  onClick={handleRefresh}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-neon-cyan bg-glass-light border border-glass-border hover:border-neon-cyan/30 transition-all"
                  title="Yenile"
                >
                  <RefreshCw size={13} />
                  Yenile
                </button>
              </div>

              {largeTransfers.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Zap size={48} className="mx-auto mb-3 opacity-30" />
                  <p>Buyuk transfer yok</p>
                  <p className="text-xs mt-1">
                    1 MB ustu transferler burada gorunur
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    {renderTableHeader()}
                    <tbody>
                      {largeTransfers.map((flow) => renderFlowRow(flow))}
                    </tbody>
                  </table>
                  <div className="mt-3 text-xs text-gray-500 text-right">
                    {largeTransfers.length} buyuk transfer ({">"}1 MB) | 3
                    saniyede yenileniyor
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {/* ─── Tab 3: Gecmis ─── */}
          {activeTab === "history" && (
            <GlassCard>
              {/* Periyot secici + filtreler + yenile */}
              <div className="flex flex-wrap gap-3 items-center mb-4">
                <div className="flex gap-1 bg-black/20 rounded-lg p-1">
                  {HISTORY_PERIODS.map((p) => (
                    <button
                      key={p.hours}
                      onClick={() => {
                        setHistoryPeriod(p.hours);
                        setHistoryPage(0);
                      }}
                      className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                        historyPeriod === p.hours
                          ? "bg-cyan-500/20 text-cyan-400"
                          : "text-gray-400 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <select
                  value={historyProtocol}
                  onChange={(e) => {
                    setHistoryProtocol(e.target.value);
                    setHistoryPage(0);
                  }}
                  className="bg-glass-light border border-glass-border text-white text-xs rounded-lg px-3 py-1.5 focus:border-neon-cyan/50 outline-none"
                >
                  <option value="">Tum Protokoller</option>
                  <option value="TCP">TCP</option>
                  <option value="UDP">UDP</option>
                </select>
                <input
                  type="text"
                  placeholder="Domain ara..."
                  value={historySearchText}
                  onChange={(e) => setHistorySearchText(e.target.value)}
                  className="bg-glass-light border border-glass-border text-white text-xs rounded-lg px-3 py-1.5 w-48 focus:border-neon-cyan/50 outline-none placeholder-gray-500"
                />
                <div className="flex-1" />
                <button
                  onClick={handleRefresh}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-neon-cyan bg-glass-light border border-glass-border hover:border-neon-cyan/30 transition-all"
                  title="Yenile"
                >
                  <RefreshCw size={13} />
                  Yenile
                </button>
              </div>

              {!historyData || historyData.items.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Clock size={48} className="mx-auto mb-3 opacity-30" />
                  <p>Gecmis kayit bulunamadi</p>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      {renderTableHeader(true)}
                      <tbody>
                        {historyData.items.map((flow) =>
                          renderFlowRow(flow, true)
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-4">
                    <span className="text-xs text-gray-500">
                      Toplam: {historyData.total} kayit
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        disabled={historyPage === 0}
                        onClick={() =>
                          setHistoryPage((p) => Math.max(0, p - 1))
                        }
                        className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-glass-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <span className="text-xs text-gray-400">
                        Sayfa {historyPage + 1} /{" "}
                        {Math.max(1, Math.ceil(historyData.total / 50))}
                      </span>
                      <button
                        disabled={
                          (historyPage + 1) * 50 >= historyData.total
                        }
                        onClick={() => setHistoryPage((p) => p + 1)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-glass-light disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </GlassCard>
          )}
        </>
      )}
    </div>
  );
}
