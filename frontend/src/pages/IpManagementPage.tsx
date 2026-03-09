// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// IP Yönetimi sayfası: Güvenilir IP ve Engellenen IP yönetimi

import { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  ShieldOff,
  Plus,
  Trash2,
  Unlock,
  Shield,
  Ban,
  Clock,
  ChevronDown,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchIpManagementStats,
  fetchTrustedIps,
  addTrustedIp,
  deleteTrustedIp,
  fetchBlockedIps,
  addBlockedIp,
  unblockIp,
  updateBlockedIpDuration,
} from "../services/ipManagementApi";
import type {
  TrustedIp,
  ManagedBlockedIp,
  IpManagementStats,
} from "../types";

type TabType = "trusted" | "blocked";

// Sure secenekleri
const DURATION_OPTIONS: { label: string; value: number | null }[] = [
  { label: "1 Saat", value: 60 },
  { label: "6 Saat", value: 360 },
  { label: "24 Saat", value: 1440 },
  { label: "1 Hafta", value: 10080 },
  { label: "Kalici", value: null },
];

export function IpManagementPage() {
  const { connected } = useWebSocket();
  const [activeTab, setActiveTab] = useState<TabType>("trusted");
  const [stats, setStats] = useState<IpManagementStats | null>(null);
  const [trustedIps, setTrustedIps] = useState<TrustedIp[]>([]);
  const [blockedIps, setBlockedIps] = useState<ManagedBlockedIp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Trusted IP form
  const [showTrustedForm, setShowTrustedForm] = useState(false);
  const [trustedForm, setTrustedForm] = useState({
    ip_address: "",
    description: "",
  });

  // Blocked IP form
  const [showBlockedForm, setShowBlockedForm] = useState(false);
  const [blockedForm, setBlockedForm] = useState<{
    ip_address: string;
    reason: string;
    duration_minutes: number | null;
  }>({
    ip_address: "",
    reason: "",
    duration_minutes: null,
  });

  const [submitting, setSubmitting] = useState(false);

  // Trusted IP siralama
  const [trustedSortBy, setTrustedSortBy] = useState<"ip_address" | "description" | "created_at">("created_at");
  const [trustedSortOrder, setTrustedSortOrder] = useState<"asc" | "desc">("desc");
  // Blocked IP siralama
  const [blockedSortBy, setBlockedSortBy] = useState<"ip_address" | "reason" | "blocked_at" | "is_manual">("blocked_at");
  const [blockedSortOrder, setBlockedSortOrder] = useState<"asc" | "desc">("desc");

  // Sure değiştirme inline select state
  const [editingDurationIp, setEditingDurationIp] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [statsRes, trustedRes, blockedRes] = await Promise.all([
        fetchIpManagementStats(),
        fetchTrustedIps(),
        fetchBlockedIps(),
      ]);
      setStats(statsRes.data);
      setTrustedIps(trustedRes.data);
      setBlockedIps(blockedRes.data);
      setError(null);
    } catch (err) {
      setError("IP yönetimi verileri yüklenemedi");
      console.error("IP yönetimi veri yükleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);


  // --- Güvenilir IP işlemleri ---

  const handleAddTrustedIp = async () => {
    if (!trustedForm.ip_address.trim()) return;
    setSubmitting(true);
    try {
      await addTrustedIp({
        ip_address: trustedForm.ip_address.trim(),
        description: trustedForm.description.trim() || undefined,
      });
      setTrustedForm({ ip_address: "", description: "" });
      setShowTrustedForm(false);
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Güvenilir IP eklenemedi";
      setError(msg);
      console.error("Güvenilir IP ekleme hatasi:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTrustedIp = async (id: number) => {
    try {
      await deleteTrustedIp(id);
      await loadData();
    } catch (err) {
      console.error("Güvenilir IP silme hatasi:", err);
    }
  };

  // --- Engellenen IP işlemleri ---

  const handleAddBlockedIp = async () => {
    if (!blockedForm.ip_address.trim()) return;
    setSubmitting(true);
    try {
      await addBlockedIp({
        ip_address: blockedForm.ip_address.trim(),
        reason: blockedForm.reason.trim() || undefined,
        duration_minutes: blockedForm.duration_minutes,
      });
      setBlockedForm({ ip_address: "", reason: "", duration_minutes: null });
      setShowBlockedForm(false);
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "IP engellenemedi";
      setError(msg);
      console.error("IP engelleme hatasi:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnblockIp = async (ip: string) => {
    try {
      await unblockIp(ip);
      await loadData();
    } catch (err) {
      console.error("IP engel kaldirma hatasi:", err);
    }
  };

  const handleChangeDuration = async (ipAddress: string, durationMinutes: number | null) => {
    setEditingDurationIp(null);
    try {
      await updateBlockedIpDuration({ ip_address: ipAddress, duration_minutes: durationMinutes });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Süre değiştirilemedi";
      setError(msg);
      console.error("Sure değiştirme hatasi:", err);
    }
  };

  // --- Siralama fonksiyonlari ---

  function handleTrustedSort(col: typeof trustedSortBy) {
    if (trustedSortBy === col) setTrustedSortOrder(o => o === "asc" ? "desc" : "asc");
    else { setTrustedSortBy(col); setTrustedSortOrder("asc"); }
  }

  function handleBlockedSort(col: typeof blockedSortBy) {
    if (blockedSortBy === col) setBlockedSortOrder(o => o === "asc" ? "desc" : "asc");
    else { setBlockedSortBy(col); setBlockedSortOrder("asc"); }
  }

  // --- Yardimci fonksiyonlar ---

  const formatTTL = (seconds: number | null) => {
    if (seconds === null || seconds <= 0) return "Kalici";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}g ${h}s`;
    if (h > 0) return `${h}s ${m}dk`;
    return `${m}dk`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "--";
    try {
      return new Date(dateStr).toLocaleString("tr-TR");
    } catch {
      return dateStr;
    }
  };

  if (loading) return <LoadingSpinner />;

  const inputClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors";
  const selectClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors appearance-none cursor-pointer";
  const labelClass =
    "block text-xs text-gray-400 mb-1 uppercase tracking-wider";

  return (
    <div className="space-y-6">
      <TopBar title="IP Yönetimi" connected={connected} />

      {/* Hata mesaji */}
      {error && (
        <div className="bg-neon-red/10 border border-neon-red/30 rounded-xl p-4 text-neon-red text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-neon-red/70 hover:text-neon-red ml-4"
          >
            &times;
          </button>
        </div>
      )}

      {/* İstatistik Kartlari */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Güvenilir IP"
            value={stats.trusted_ip_count}
            icon={<ShieldCheck size={32} />}
            neonColor="green"
          />
          <StatCard
            title="Engelli IP"
            value={stats.blocked_ip_count}
            icon={<Ban size={32} />}
            neonColor="magenta"
          />
          <StatCard
            title="Manuel Engel"
            value={stats.manual_block_count}
            icon={<Shield size={32} />}
            neonColor="cyan"
          />
          <StatCard
            title="Otomatik Engel"
            value={stats.auto_block_count}
            icon={<ShieldOff size={32} />}
            neonColor="amber"
          />
        </div>
      )}

      {/* Sekme Cubugu */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab("trusted")}
          className={`px-6 py-2.5 text-sm font-medium rounded-xl transition-all ${
            activeTab === "trusted"
              ? "bg-neon-green/10 text-neon-green border border-neon-green/30 shadow-[0_0_15px_rgba(57,255,20,0.15)]"
              : "text-gray-400 hover:text-white hover:bg-glass-light border border-transparent"
          }`}
        >
          <span className="flex items-center gap-2">
            <ShieldCheck size={16} />
            Güvenilir IP'ler ({trustedIps.length})
          </span>
        </button>
        <button
          onClick={() => setActiveTab("blocked")}
          className={`px-6 py-2.5 text-sm font-medium rounded-xl transition-all ${
            activeTab === "blocked"
              ? "bg-neon-red/10 text-neon-red border border-neon-red/30 shadow-[0_0_15px_rgba(255,50,50,0.15)]"
              : "text-gray-400 hover:text-white hover:bg-glass-light border border-transparent"
          }`}
        >
          <span className="flex items-center gap-2">
            <Ban size={16} />
            Engellenen IP'ler ({blockedIps.length})
          </span>
        </button>
      </div>

      {/* ===== GUVENILIR IP SEKMESI ===== */}
      {activeTab === "trusted" && (
        <>
          {/* Ekle Butonu */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">
              Güvenilir IP Listesi
            </h3>
            <button
              onClick={() => setShowTrustedForm(!showTrustedForm)}
              className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all"
            >
              <Plus size={16} />
              {showTrustedForm ? "Formu Kapat" : "Güvenilir IP Ekle"}
            </button>
          </div>

          {/* Ekleme Formu */}
          {showTrustedForm && (
            <GlassCard>
              <h4 className="text-sm font-semibold text-gray-300 mb-4">
                Yeni Güvenilir IP
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>IP Adresi *</label>
                  <input
                    type="text"
                    value={trustedForm.ip_address}
                    onChange={(e) =>
                      setTrustedForm((prev) => ({
                        ...prev,
                        ip_address: e.target.value,
                      }))
                    }
                    placeholder="örnek: 192.168.1.100"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Açıklama</label>
                  <input
                    type="text"
                    value={trustedForm.description}
                    onChange={(e) =>
                      setTrustedForm((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                    placeholder="örnek: Annemin telefonu"
                    className={inputClass}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-glass-border">
                <button
                  onClick={() => {
                    setTrustedForm({ ip_address: "", description: "" });
                    setShowTrustedForm(false);
                  }}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Iptal
                </button>
                <button
                  onClick={handleAddTrustedIp}
                  disabled={!trustedForm.ip_address.trim() || submitting}
                  className="flex items-center gap-2 px-6 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <div className="w-4 h-4 border-2 border-neon-green/30 border-t-neon-green rounded-full animate-spin" />
                  ) : (
                    <Plus size={16} />
                  )}
                  Ekle
                </button>
              </div>
            </GlassCard>
          )}

          {/* Güvenilir IP Tablosu */}
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-glass-border">
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleTrustedSort("ip_address")}
                    >
                      <span className="flex items-center gap-1.5">
                        IP Adresi
                        {trustedSortBy === "ip_address" ? (
                          trustedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleTrustedSort("description")}
                    >
                      <span className="flex items-center gap-1.5">
                        Açıklama
                        {trustedSortBy === "description" ? (
                          trustedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleTrustedSort("created_at")}
                    >
                      <span className="flex items-center gap-1.5">
                        Ekleme Tarihi
                        {trustedSortBy === "created_at" ? (
                          trustedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th className="pb-3 text-right">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {trustedIps.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        className="py-8 text-center text-gray-500"
                      >
                        Henüz güvenilir IP eklenmemiş
                      </td>
                    </tr>
                  )}
                  {(() => {
                    const sortedTrustedIps = [...trustedIps].sort((a, b) => {
                      const aVal = a[trustedSortBy] ?? "";
                      const bVal = b[trustedSortBy] ?? "";
                      const cmp = String(aVal).localeCompare(String(bVal));
                      return trustedSortOrder === "asc" ? cmp : -cmp;
                    });
                    return sortedTrustedIps.map((ip) => (
                      <tr
                        key={ip.id}
                        className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                      >
                        <td className="py-2.5 pr-4">
                          <span className="font-mono text-neon-green">
                            {ip.ip_address}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 text-gray-300">
                          {ip.description || "--"}
                        </td>
                        <td className="py-2.5 pr-4 text-xs text-gray-400">
                          {formatDate(ip.created_at)}
                        </td>
                        <td className="py-2.5 text-right">
                          <button
                            onClick={() => handleDeleteTrustedIp(ip.id)}
                            className="p-1.5 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                            title="Güvenilir IP'yi Sil"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ));
                  })()}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </>
      )}

      {/* ===== ENGELLENEN IP SEKMESI ===== */}
      {activeTab === "blocked" && (
        <>
          {/* Ekle Butonu */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">
              Engellenen IP Listesi
            </h3>
            <button
              onClick={() => setShowBlockedForm(!showBlockedForm)}
              className="flex items-center gap-2 px-4 py-2 bg-neon-red/10 hover:bg-neon-red/20 border border-neon-red/30 text-neon-red rounded-xl text-sm transition-all"
            >
              <Plus size={16} />
              {showBlockedForm ? "Formu Kapat" : "IP Engelle"}
            </button>
          </div>

          {/* Ekleme Formu */}
          {showBlockedForm && (
            <GlassCard>
              <h4 className="text-sm font-semibold text-gray-300 mb-4">
                Yeni IP Engelle
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className={labelClass}>IP Adresi *</label>
                  <input
                    type="text"
                    value={blockedForm.ip_address}
                    onChange={(e) =>
                      setBlockedForm((prev) => ({
                        ...prev,
                        ip_address: e.target.value,
                      }))
                    }
                    placeholder="örnek: 45.33.32.156"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Engelleme Sebebi</label>
                  <input
                    type="text"
                    value={blockedForm.reason}
                    onChange={(e) =>
                      setBlockedForm((prev) => ({
                        ...prev,
                        reason: e.target.value,
                      }))
                    }
                    placeholder="örnek: Şüpheli trafik"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Engelleme Süresi</label>
                  <div className="relative">
                    <select
                      value={blockedForm.duration_minutes ?? "permanent"}
                      onChange={(e) =>
                        setBlockedForm((prev) => ({
                          ...prev,
                          duration_minutes:
                            e.target.value === "permanent"
                              ? null
                              : Number(e.target.value),
                        }))
                      }
                      className={selectClass}
                    >
                      {DURATION_OPTIONS.map((opt) => (
                        <option
                          key={opt.value ?? "permanent"}
                          value={opt.value ?? "permanent"}
                        >
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      size={14}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-glass-border">
                <button
                  onClick={() => {
                    setBlockedForm({ ip_address: "", reason: "", duration_minutes: null });
                    setShowBlockedForm(false);
                  }}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Iptal
                </button>
                <button
                  onClick={handleAddBlockedIp}
                  disabled={!blockedForm.ip_address.trim() || submitting}
                  className="flex items-center gap-2 px-6 py-2 bg-neon-red/10 hover:bg-neon-red/20 border border-neon-red/30 text-neon-red rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <div className="w-4 h-4 border-2 border-neon-red/30 border-t-neon-red rounded-full animate-spin" />
                  ) : (
                    <Ban size={16} />
                  )}
                  Engelle
                </button>
              </div>
            </GlassCard>
          )}

          {/* Engellenen IP Tablosu */}
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-glass-border">
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleBlockedSort("ip_address")}
                    >
                      <span className="flex items-center gap-1.5">
                        IP Adresi
                        {blockedSortBy === "ip_address" ? (
                          blockedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleBlockedSort("reason")}
                    >
                      <span className="flex items-center gap-1.5">
                        Sebep
                        {blockedSortBy === "reason" ? (
                          blockedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleBlockedSort("blocked_at")}
                    >
                      <span className="flex items-center gap-1.5">
                        Engel Tarihi
                        {blockedSortBy === "blocked_at" ? (
                          blockedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th
                      className="pb-3 pr-4 cursor-pointer select-none hover:text-white transition-colors"
                      onClick={() => handleBlockedSort("is_manual")}
                    >
                      <span className="flex items-center gap-1.5">
                        Kaynak
                        {blockedSortBy === "is_manual" ? (
                          blockedSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    </th>
                    <th className="pb-3 pr-4">Kalan Sure</th>
                    <th className="pb-3 text-right">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {blockedIps.length === 0 && (
                    <tr>
                      <td
                        colSpan={6}
                        className="py-8 text-center text-gray-500"
                      >
                        Henüz engellenen IP yok
                      </td>
                    </tr>
                  )}
                  {(() => {
                    const sortedBlockedIps = [...blockedIps].sort((a, b) => {
                      if (blockedSortBy === "is_manual") {
                        const cmp = (a.is_manual ? 1 : 0) - (b.is_manual ? 1 : 0);
                        return blockedSortOrder === "asc" ? cmp : -cmp;
                      }
                      const aVal = a[blockedSortBy] ?? "";
                      const bVal = b[blockedSortBy] ?? "";
                      const cmp = String(aVal).localeCompare(String(bVal));
                      return blockedSortOrder === "asc" ? cmp : -cmp;
                    });
                    return sortedBlockedIps.map((ip, idx) => (
                    <tr
                      key={ip.id ?? `redis-${idx}`}
                      className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                    >
                      <td className="py-2.5 pr-4">
                        <span className="font-mono text-neon-red">
                          {ip.ip_address}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-gray-300 max-w-[200px] truncate">
                        {ip.reason || "--"}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-gray-400">
                        {formatDate(ip.blocked_at)}
                      </td>
                      <td className="py-2.5 pr-4">
                        <NeonBadge
                          label={ip.is_manual ? "MANUEL" : "OTO"}
                          variant={ip.is_manual ? "green" : "amber"}
                        />
                      </td>
                      <td className="py-2.5 pr-4">
                        {editingDurationIp === ip.ip_address ? (
                          <select
                            autoFocus
                            defaultValue="__pick__"
                            onChange={(e) => {
                              const v = e.target.value;
                              if (v === "__pick__") return;
                              handleChangeDuration(
                                ip.ip_address,
                                v === "permanent" ? null : Number(v)
                              );
                            }}
                            onBlur={() => setEditingDurationIp(null)}
                            className="bg-surface-800 border border-neon-cyan/40 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-neon-cyan cursor-pointer"
                          >
                            <option value="__pick__" disabled>
                              Süre Seç...
                            </option>
                            {DURATION_OPTIONS.map((opt) => (
                              <option
                                key={opt.value ?? "permanent"}
                                value={opt.value ?? "permanent"}
                              >
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <button
                            onClick={() => setEditingDurationIp(ip.ip_address)}
                            className="flex items-center gap-1 text-xs hover:text-neon-cyan transition-colors group"
                            title="Süreyi Değiştir"
                          >
                            {ip.remaining_seconds !== null && ip.remaining_seconds > 0 ? (
                              <>
                                <Clock size={12} className="text-neon-amber group-hover:text-neon-cyan" />
                                <span className="text-neon-amber group-hover:text-neon-cyan">
                                  {formatTTL(ip.remaining_seconds)}
                                </span>
                              </>
                            ) : (
                              <span className="text-gray-500 group-hover:text-neon-cyan">
                                Kalici
                              </span>
                            )}
                          </button>
                        )}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => handleUnblockIp(ip.ip_address)}
                          className="p-1.5 text-gray-500 hover:text-neon-green hover:bg-neon-green/10 rounded-lg transition-all"
                          title="Engeli Kaldir"
                        >
                          <Unlock size={14} />
                        </button>
                      </td>
                    </tr>
                    ));
                  })()}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </>
      )}
    </div>
  );
}
