// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Kapsamli Sistem Logları sayfası: filtreleme, sayfalama, özet kartlari

import { useState, useEffect, useCallback } from "react";
import {
  ScrollText,
  Search,
  ShieldBan,
  Brain,
  AlertTriangle,
  Filter,
  X,
  ChevronLeft,
  ChevronRight,
  RotateCw,
  Database,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import { fetchSystemLogs, fetchSystemLogSummary } from "../services/systemLogApi";
import type { SystemLogEntry, SystemLogListResponse, SystemLogSummary } from "../types";

interface Filters {
  date_from: string;
  date_to: string;
  source_ip: string;
  dest_ip: string;
  domain_search: string;
  action: string;
  severity: string;
  category: string;
  search: string;
}

const emptyFilters: Filters = {
  date_from: "",
  date_to: "",
  source_ip: "",
  dest_ip: "",
  domain_search: "",
  action: "",
  severity: "",
  category: "",
  search: "",
};

export function SystemLogsPage() {
  const { connected } = useWebSocket();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<SystemLogSummary | null>(null);
  const [logData, setLogData] = useState<SystemLogListResponse | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [filterOpen, setFilterOpen] = useState(false);
  const [goToPage, setGoToPage] = useState("");

  const loadData = useCallback(async (currentPage: number, currentPerPage: number, currentFilters: Filters) => {
    try {
      const params: Record<string, string | number> = {
        page: currentPage,
        per_page: currentPerPage,
      };
      if (currentFilters.date_from) params.date_from = currentFilters.date_from;
      if (currentFilters.date_to) params.date_to = currentFilters.date_to;
      if (currentFilters.source_ip) params.source_ip = currentFilters.source_ip;
      if (currentFilters.dest_ip) params.dest_ip = currentFilters.dest_ip;
      if (currentFilters.domain_search) params.domain_search = currentFilters.domain_search;
      if (currentFilters.action) params.action = currentFilters.action;
      if (currentFilters.severity) params.severity = currentFilters.severity;
      if (currentFilters.category) params.category = currentFilters.category;
      if (currentFilters.search) params.search = currentFilters.search;

      const [logs, sum] = await Promise.all([
        fetchSystemLogs(params),
        fetchSystemLogSummary(),
      ]);
      setLogData(logs);
      setSummary(sum);
    } catch (err) {
      console.error("Sistem loglari alinamadi:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData(page, perPage, appliedFilters);
  }, [page, perPage, appliedFilters, loadData]);

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters });
    setPage(1);
  };

  const handleClearFilters = () => {
    setFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
    setPage(1);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData(page, perPage, appliedFilters);
  };

  const handleGoToPage = () => {
    const p = parseInt(goToPage);
    if (p >= 1 && logData && p <= logData.total_pages) {
      setPage(p);
      setGoToPage("");
    }
  };

  const formatTime = (ts: string | null) => {
    if (!ts) return "--";
    const d = new Date(ts);
    return d.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const actionBadge = (action: string) => {
    switch (action) {
      case "block":
        return <NeonBadge label="ENGEL" variant="red" />;
      case "allow":
        return <NeonBadge label="IZIN" variant="green" />;
      default:
        return <NeonBadge label="SORGU" variant="cyan" />;
    }
  };

  const severityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return <NeonBadge label="KRITIK" variant="red" />;
      case "warning":
        return <NeonBadge label="UYARI" variant="amber" />;
      default:
        return <NeonBadge label="BILGI" variant="cyan" />;
    }
  };

  const categoryBadge = (category: string) => {
    switch (category) {
      case "ddos":
        return <NeonBadge label="DDOS" variant="red" />;
      case "security":
        return <NeonBadge label="GUVENLIK" variant="red" />;
      case "ai":
        return <NeonBadge label="AI" variant="magenta" />;
      case "traffic":
        return <NeonBadge label="TRAFIK" variant="amber" />;
      default:
        return <NeonBadge label="DNS" variant="cyan" />;
    }
  };

  if (loading) return <LoadingSpinner />;

  // Sayfa numaralarini hesapla
  const totalPages = logData?.total_pages || 1;
  const pageNumbers: number[] = [];
  const maxPageButtons = 5;
  let startPage = Math.max(1, page - Math.floor(maxPageButtons / 2));
  let endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
  if (endPage - startPage < maxPageButtons - 1) {
    startPage = Math.max(1, endPage - maxPageButtons + 1);
  }
  for (let i = startPage; i <= endPage; i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="space-y-6">
      <TopBar title="Sistem Logları" connected={connected} />

      {/* Özet kartlari */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Toplam Log (30g)"
            value={summary.total_logs_30d.toLocaleString()}
            icon={<Database size={32} />}
            neonColor="cyan"
          />
          <StatCard
            title="DNS Sorgu (30g)"
            value={summary.dns_queries_30d.toLocaleString()}
            icon={<Search size={32} />}
            neonColor="green"
          />
          <StatCard
            title="Engellenen (30g)"
            value={summary.blocked_30d.toLocaleString()}
            icon={<ShieldBan size={32} />}
            neonColor="amber"
          />
          <StatCard
            title="Kritik (30g)"
            value={summary.critical_30d.toLocaleString()}
            icon={<AlertTriangle size={32} />}
            neonColor="magenta"
          />
        </div>
      )}

      {/* Filtre paneli toggle + yenile butonu */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
            filterOpen
              ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
              : "text-gray-400 bg-glass-light border border-glass-border hover:text-white"
          }`}
        >
          <Filter size={16} />
          Filtreler
          {Object.values(appliedFilters).some(v => v) && (
            <span className="ml-1 w-2 h-2 rounded-full bg-neon-cyan" />
          )}
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            Toplam: {logData?.total?.toLocaleString() || 0} kayit
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
          >
            <RotateCw size={16} className={refreshing ? "animate-spin" : ""} />
            Yenile
          </button>
        </div>
      </div>

      {/* Filtre paneli */}
      {filterOpen && (
        <GlassCard>
          <div className="space-y-4">
            {/* Satır 1: Tarih aralığı */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Başlangıç Tarihi</label>
                <input
                  type="datetime-local"
                  value={filters.date_from}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Bitiş Tarihi</label>
                <input
                  type="datetime-local"
                  value={filters.date_to}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
            </div>

            {/* Satır 2: IP + Domain + Serbest arama */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Kaynak IP</label>
                <input
                  type="text"
                  value={filters.source_ip}
                  onChange={(e) => setFilters(prev => ({ ...prev, source_ip: e.target.value }))}
                  placeholder="192.168.1.x"
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Hedef IP / Domain</label>
                <input
                  type="text"
                  value={filters.dest_ip}
                  onChange={(e) => setFilters(prev => ({ ...prev, dest_ip: e.target.value }))}
                  placeholder="1.1.1.1 veya google.com"
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Serbest Arama</label>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  placeholder="Herhangi bir metin..."
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
            </div>

            {/* Satır 3: Dropdown filtreler */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Aksiyon</label>
                <select
                  value={filters.action}
                  onChange={(e) => setFilters(prev => ({ ...prev, action: e.target.value }))}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  <option value="">Tümü</option>
                  <option value="block">Engellenen</option>
                  <option value="allow">İzin Verilen</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Önem Derecesi</label>
                <select
                  value={filters.severity}
                  onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  <option value="">Tümü</option>
                  <option value="info">Bilgi</option>
                  <option value="warning">Uyarı</option>
                  <option value="critical">Kritik</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Kategori</label>
                <select
                  value={filters.category}
                  onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  <option value="">Tümü</option>
                  <option value="dns">DNS</option>
                  <option value="ai">AI</option>
                  <option value="security">Güvenlik</option>
                  <option value="ddos">DDoS</option>
                  <option value="traffic">Trafik</option>
                </select>
              </div>
            </div>

            {/* Butonlar */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleApplyFilters}
                className="flex items-center gap-2 px-5 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all"
              >
                <Search size={16} />
                Filtrele
              </button>
              <button
                onClick={handleClearFilters}
                className="flex items-center gap-2 px-4 py-2.5 text-gray-400 border border-glass-border rounded-xl text-sm hover:text-white hover:bg-glass-light transition-all"
              >
                <X size={16} />
                Temizle
              </button>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Sonuç tablosu */}
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-glass-border">
                <th className="pb-3 pr-3 whitespace-nowrap">Zaman</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Kaynak IP</th>
                <th className="pb-3 pr-3 whitespace-nowrap">MAC</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Hostname</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Domain</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Tip</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Aksiyon</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Kategori</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Önem</th>
                <th className="pb-3 pr-3 whitespace-nowrap">Yanit IP</th>
                <th className="pb-3 pr-3 whitespace-nowrap">ms</th>
                <th className="pb-3 whitespace-nowrap">Paket Boyutu</th>
              </tr>
            </thead>
            <tbody>
              {logData?.items.map((log) => (
                <tr
                  key={log.id}
                  className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                >
                  <td className="py-2 pr-3 text-xs text-gray-300 whitespace-nowrap">
                    {formatTime(log.timestamp)}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs">
                    {log.client_ip || "--"}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-gray-500">
                    {log.mac_address || "--"}
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-400">
                    {log.hostname || "--"}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs max-w-[200px] truncate" title={log.domain}>
                    {log.domain}
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-500">
                    {log.query_type}
                  </td>
                  <td className="py-2 pr-3">
                    {actionBadge(log.action)}
                  </td>
                  <td className="py-2 pr-3">
                    {categoryBadge(log.category)}
                  </td>
                  <td className="py-2 pr-3">
                    {severityBadge(log.severity)}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-gray-500">
                    {log.answer_ip || "--"}
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-500">
                    {log.upstream_response_ms != null ? `${log.upstream_response_ms}` : "--"}
                  </td>
                  <td className="py-2 text-xs text-gray-500">
                    {log.bytes_total != null
                      ? log.bytes_total >= 1048576
                        ? `${(log.bytes_total / 1048576).toFixed(1)} MB`
                        : log.bytes_total >= 1024
                          ? `${(log.bytes_total / 1024).toFixed(1)} KB`
                          : `${log.bytes_total} B`
                      : "--"}
                  </td>
                </tr>
              ))}
              {(!logData?.items || logData.items.length === 0) && (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-gray-500">
                    <ScrollText size={40} className="mx-auto mb-3 opacity-30" />
                    <p>Filtrelerinize uyan kayıt bulunamadı.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Sayfalama cubugu */}
      {logData && logData.total > 0 && (
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Sol: sayfa başına kayit */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Sayfa başına:</span>
            <select
              value={perPage}
              onChange={(e) => {
                setPerPage(parseInt(e.target.value));
                setPage(1);
              }}
              className="bg-surface-800 border border-glass-border rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          {/* Orta: sayfa numaralari */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-glass-light transition-all disabled:opacity-30"
            >
              <ChevronLeft size={16} />
            </button>

            {startPage > 1 && (
              <>
                <button
                  onClick={() => setPage(1)}
                  className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-glass-light transition-all"
                >
                  1
                </button>
                {startPage > 2 && <span className="text-gray-600 px-1">...</span>}
              </>
            )}

            {pageNumbers.map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  p === page
                    ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                    : "text-gray-400 hover:text-white hover:bg-glass-light"
                }`}
              >
                {p}
              </button>
            ))}

            {endPage < totalPages && (
              <>
                {endPage < totalPages - 1 && <span className="text-gray-600 px-1">...</span>}
                <button
                  onClick={() => setPage(totalPages)}
                  className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-glass-light transition-all"
                >
                  {totalPages}
                </button>
              </>
            )}

            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-glass-light transition-all disabled:opacity-30"
            >
              <ChevronRight size={16} />
            </button>
          </div>

          {/* Sag: sayfaya git */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Sayfaya git:</span>
            <input
              type="number"
              min={1}
              max={totalPages}
              value={goToPage}
              onChange={(e) => setGoToPage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGoToPage()}
              className="w-16 bg-surface-800 border border-glass-border rounded-lg px-2 py-1.5 text-sm text-white text-center focus:outline-none focus:border-neon-cyan/50"
              placeholder={`${page}`}
            />
            <button
              onClick={handleGoToPage}
              className="px-3 py-1.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-lg text-sm hover:bg-neon-cyan/20 transition-all"
            >
              Git
            </button>
            <span className="text-xs text-gray-500 ml-2">
              Sayfa {page} / {totalPages}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
