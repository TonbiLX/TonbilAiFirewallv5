// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP Sunucu sayfası: havuz yönetimi, kiralama tablosu, statik atama
// Yeni: Tam havuz CRUD, düzenleme modali, gelistirilmis lease tablosu

import { useState, useEffect } from "react";
import {
  Network,
  List,
  Settings,
  Plus,
  Pencil,
  Trash2,
  X,
  Server,
  Globe,
  Clock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { DhcpPoolCard } from "../components/dhcp/DhcpPoolCard";
import { DhcpStatsCards } from "../components/dhcp/DhcpStatsCards";
import { StaticLeaseForm } from "../components/dhcp/StaticLeaseForm";
import { useWebSocket } from "../hooks/useWebSocket";
import { useDhcp } from "../hooks/useDhcp";
import {
  togglePool,
  deletePool,
  createPool,
  updatePool,
  deleteLease,
} from "../services/dhcpApi";
import type { DhcpPool, DhcpLease } from "../types";

type Tab = "overview" | "leases" | "settings";

const tabs: { key: Tab; label: string; icon: typeof Network }[] = [
  { key: "overview", label: "Genel Bakış", icon: Network },
  { key: "leases", label: "Kiralamalar", icon: List },
  { key: "settings", label: "Ayarlar", icon: Settings },
];

// --- Havuz form yapisi ---
interface PoolFormData {
  name: string;
  subnet: string;
  netmask: string;
  range_start: string;
  range_end: string;
  gateway: string;
  dns_servers: string;
  lease_time_seconds: string;
  enabled: boolean;
}

const emptyPoolForm: PoolFormData = {
  name: "",
  subnet: "192.168.1.0",
  netmask: "255.255.255.0",
  range_start: "192.168.1.100",
  range_end: "192.168.1.200",
  gateway: "192.168.1.1",
  dns_servers: "8.8.8.8, 8.8.4.4",
  lease_time_seconds: "86400",
  enabled: true,
};

export function DhcpPage() {
  const { connected } = useWebSocket();
  const { pools, leases, stats, loading, refresh } = useDhcp();
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Havuz modal durumu
  const [poolModalOpen, setPoolModalOpen] = useState(false);
  const [editingPool, setEditingPool] = useState<DhcpPool | null>(null);
  const [poolForm, setPoolForm] = useState<PoolFormData>(emptyPoolForm);
  const [poolFormErrors, setPoolFormErrors] = useState<
    Record<string, boolean>
  >({});
  const [submitting, setSubmitting] = useState(false);

  // Silme onay
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  // Lease silme onay
  const [deleteLeaseConfirmMac, setDeleteLeaseConfirmMac] = useState<
    string | null
  >(null);

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // --- Geri bildirim zamanlayici ---
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  if (loading) return <LoadingSpinner />;

  // --- Mevcut havuz işlemleri ---
  const handleTogglePool = async (id: number) => {
    try {
      await togglePool(id);
      refresh();
    } catch (err) {
      console.error("Havuz toggle hatasi:", err);
      setFeedback({
        type: "error",
        message: "Havuz durumu değiştirilemedi.",
      });
    }
  };

  const handleDeletePool = async (id: number) => {
    try {
      await deletePool(id);
      setDeleteConfirmId(null);
      setFeedback({ type: "success", message: "Havuz silindi." });
      refresh();
    } catch (err) {
      console.error("Havuz silinemedi:", err);
      setFeedback({
        type: "error",
        message: "Havuz silinirken hata oluştu.",
      });
    }
  };

  // --- Lease silme ---
  const handleDeleteLease = async (mac: string) => {
    try {
      await deleteLease(mac);
      setDeleteLeaseConfirmMac(null);
      setFeedback({ type: "success", message: "Lease kaydi silindi." });
      refresh();
    } catch (err) {
      console.error("Lease silinemedi:", err);
      setFeedback({
        type: "error",
        message: "Lease silinirken hata oluştu.",
      });
    }
  };

  // --- Havuz modal işlemleri ---
  const openCreatePoolModal = () => {
    setEditingPool(null);
    setPoolForm(emptyPoolForm);
    setPoolFormErrors({});
    setPoolModalOpen(true);
  };

  const openEditPoolModal = (pool: DhcpPool) => {
    setEditingPool(pool);
    setPoolForm({
      name: pool.name,
      subnet: pool.subnet,
      netmask: pool.netmask,
      range_start: pool.range_start,
      range_end: pool.range_end,
      gateway: pool.gateway,
      dns_servers: pool.dns_servers.join(", "),
      lease_time_seconds: pool.lease_time_seconds.toString(),
      enabled: pool.enabled,
    });
    setPoolFormErrors({});
    setPoolModalOpen(true);
  };

  const closePoolModal = () => {
    setPoolModalOpen(false);
    setEditingPool(null);
    setPoolForm(emptyPoolForm);
    setPoolFormErrors({});
  };

  const validatePoolForm = (): boolean => {
    const errors: Record<string, boolean> = {};
    if (!poolForm.name.trim()) errors.name = true;
    if (!poolForm.subnet.trim()) errors.subnet = true;
    if (!poolForm.netmask.trim()) errors.netmask = true;
    if (!poolForm.range_start.trim()) errors.range_start = true;
    if (!poolForm.range_end.trim()) errors.range_end = true;
    if (!poolForm.gateway.trim()) errors.gateway = true;
    if (!poolForm.dns_servers.trim()) errors.dns_servers = true;
    if (
      !poolForm.lease_time_seconds ||
      parseInt(poolForm.lease_time_seconds) <= 0
    )
      errors.lease_time_seconds = true;
    setPoolFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handlePoolSubmit = async () => {
    if (!validatePoolForm()) return;
    setSubmitting(true);

    const payload: Partial<DhcpPool> = {
      name: poolForm.name.trim(),
      subnet: poolForm.subnet.trim(),
      netmask: poolForm.netmask.trim(),
      range_start: poolForm.range_start.trim(),
      range_end: poolForm.range_end.trim(),
      gateway: poolForm.gateway.trim(),
      dns_servers: poolForm.dns_servers
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      lease_time_seconds: parseInt(poolForm.lease_time_seconds),
      enabled: poolForm.enabled,
    };

    try {
      if (editingPool) {
        await updatePool(editingPool.id, payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" havuzu güncellendi.`,
        });
      } else {
        await createPool(payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" havuzu oluşturuldu.`,
        });
      }
      closePoolModal();
      refresh();
    } catch (err) {
      console.error("Havuz kaydedilemedi:", err);
      setFeedback({
        type: "error",
        message: "Havuz kaydedilirken hata oluştu.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  // --- Lease süresi formatlama ---
  const formatLeaseExpiry = (leaseEnd: string | null): string => {
    if (!leaseEnd) return "--";
    const end = new Date(leaseEnd);
    const now = new Date();
    const diff = end.getTime() - now.getTime();
    if (diff <= 0) return "Süresi Dolmus";
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    if (hours > 0) return `${hours}s ${mins}dk kaldi`;
    return `${mins}dk kaldi`;
  };

  // --- Havuz adi getirme ---
  const getPoolName = (poolId: number | null): string => {
    if (!poolId) return "--";
    const pool = pools.find((p) => p.id === poolId);
    return pool ? pool.name : "--";
  };

  return (
    <div className="space-y-6">
      <TopBar title="DHCP Sunucu" connected={connected} />

      {/* Tab navigasyonu */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
              activeTab === tab.key
                ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                : "text-gray-400 bg-glass-light border border-glass-border hover:text-white"
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Geri bildirim mesaji */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle size={16} />
          ) : (
            <AlertTriangle size={16} />
          )}
          {feedback.message}
        </div>
      )}

      {/* GENEL BAKIS */}
      {activeTab === "overview" && stats && (
        <div className="space-y-6">
          <DhcpStatsCards stats={stats} />

          {/* Havuzlar + Yeni Havuz butonu */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">
              IP Havuzlari
            </h3>
            <button
              onClick={openCreatePoolModal}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all"
            >
              <Plus size={16} />
              Yeni Havuz
            </button>
          </div>

          <div className="space-y-3">
            {pools.map((pool) => {
              const poolLeases = leases.filter((l) => l.pool_id === pool.id);
              return (
                <div key={pool.id} className="relative group">
                  <DhcpPoolCard
                    pool={pool}
                    leaseCount={poolLeases.length}
                    onToggle={handleTogglePool}
                    onDelete={handleDeletePool}
                  />
                  {/* Düzenleme butonu - kart üzerinde hover */}
                  <button
                    onClick={() => openEditPoolModal(pool)}
                    className="absolute top-4 right-28 p-1.5 rounded-lg text-gray-500 opacity-0 group-hover:opacity-100 hover:text-neon-cyan hover:bg-neon-cyan/10 transition-all"
                    title="Havuzu düzenle"
                  >
                    <Pencil size={14} />
                  </button>
                </div>
              );
            })}
            {pools.length === 0 && (
              <GlassCard>
                <p className="text-gray-500 text-center py-8">
                  Henüz IP havuzu oluşturulmamis. "Yeni Havuz" ile başlayabilirsiniz.
                </p>
              </GlassCard>
            )}
          </div>
        </div>
      )}

      {/* KIRALAMALAR - Gelistirilmis tablo */}
      {activeTab === "leases" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">
              {leases.length} aktif kiralama (
              {leases.filter((l) => l.is_static).length} statik,{" "}
              {leases.filter((l) => !l.is_static).length} dinamik)
            </p>
          </div>

          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-glass-border">
                    <th className="pb-3 pr-4">Hostname</th>
                    <th className="pb-3 pr-4">IP Adresi</th>
                    <th className="pb-3 pr-4">MAC Adresi</th>
                    <th className="pb-3 pr-4">Havuz</th>
                    <th className="pb-3 pr-4">Tip</th>
                    <th className="pb-3 pr-4">Kalan Sure</th>
                    <th className="pb-3 text-right">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {leases.map((lease) => (
                    <tr
                      key={lease.id}
                      className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                    >
                      <td className="py-2.5 pr-4 text-xs">
                        {lease.hostname || (
                          <span className="text-gray-600">--</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-neon-cyan">
                        {lease.ip_address}
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-400">
                        {lease.mac_address}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-gray-400">
                        {getPoolName(lease.pool_id)}
                      </td>
                      <td className="py-2.5 pr-4">
                        <NeonBadge
                          label={lease.is_static ? "STATIK" : "DINAMIK"}
                          variant={lease.is_static ? "magenta" : "cyan"}
                        />
                      </td>
                      <td className="py-2.5 pr-4 text-xs">
                        {lease.is_static ? (
                          <span className="text-neon-green">Kalici</span>
                        ) : (
                          <span
                            className={
                              formatLeaseExpiry(lease.lease_end) ===
                              "Süresi Dolmus"
                                ? "text-neon-red"
                                : "text-gray-400"
                            }
                          >
                            {formatLeaseExpiry(lease.lease_end)}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-right">
                        {deleteLeaseConfirmMac === lease.mac_address ? (
                          <div className="flex items-center gap-1 justify-end">
                            <button
                              onClick={() =>
                                handleDeleteLease(lease.mac_address)
                              }
                              className="px-2 py-1 bg-neon-red/10 text-neon-red border border-neon-red/20 rounded text-xs hover:bg-neon-red/20 transition-colors"
                            >
                              Onayla
                            </button>
                            <button
                              onClick={() => setDeleteLeaseConfirmMac(null)}
                              className="px-2 py-1 text-gray-400 border border-glass-border rounded text-xs hover:text-white transition-colors"
                            >
                              Iptal
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() =>
                              setDeleteLeaseConfirmMac(lease.mac_address)
                            }
                            className="p-1.5 text-gray-500 hover:text-neon-red transition-colors"
                            title="Lease sil"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {leases.length === 0 && (
                    <tr>
                      <td
                        colSpan={7}
                        className="py-8 text-center text-gray-500"
                      >
                        Henüz aktif kiralama yok.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </div>
      )}

      {/* AYARLAR */}
      {activeTab === "settings" && (
        <div className="space-y-4">
          <StaticLeaseForm onCreated={refresh} />

          {/* Havuz Yönetimi */}
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-semibold text-gray-300">
                DHCP Havuzlari
              </h4>
              <button
                onClick={openCreatePoolModal}
                className="flex items-center gap-1 px-3 py-1.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-lg text-xs hover:bg-neon-cyan/20 transition-colors"
              >
                <Plus size={14} />
                Yeni Havuz
              </button>
            </div>
            <div className="space-y-3">
              {pools.map((pool) => (
                <div
                  key={pool.id}
                  className="p-4 bg-surface-800 rounded-xl border border-white/5"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Network
                        size={16}
                        className={
                          pool.enabled ? "text-neon-cyan" : "text-gray-600"
                        }
                      />
                      <p className="text-sm font-medium">{pool.name}</p>
                      <NeonBadge
                        label={pool.enabled ? "AKTIF" : "PASIF"}
                        variant={pool.enabled ? "green" : "red"}
                      />
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEditPoolModal(pool)}
                        className="p-1.5 text-gray-400 hover:text-neon-cyan hover:bg-neon-cyan/10 rounded-lg transition-all"
                        title="Düzenle"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleTogglePool(pool.id)}
                        className={`px-3 py-1 text-xs rounded-lg transition-all ${
                          pool.enabled
                            ? "bg-neon-green/10 text-neon-green border border-neon-green/20"
                            : "bg-gray-800 text-gray-400 border border-glass-border"
                        }`}
                      >
                        {pool.enabled ? "Durdur" : "Başlat"}
                      </button>
                      {deleteConfirmId === pool.id ? (
                        <div className="flex items-center gap-1 ml-2">
                          <button
                            onClick={() => handleDeletePool(pool.id)}
                            className="px-2 py-1 bg-neon-red/10 text-neon-red border border-neon-red/20 rounded text-xs hover:bg-neon-red/20 transition-colors"
                          >
                            Onayla
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="px-2 py-1 text-gray-400 border border-glass-border rounded text-xs hover:text-white transition-colors"
                          >
                            Iptal
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(pool.id)}
                          className="p-1.5 text-gray-500 hover:text-neon-red transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Havuz detayları grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-gray-400">
                    <div className="flex items-center gap-1.5">
                      <Server size={12} className="text-gray-500" />
                      <span>
                        {pool.range_start} - {pool.range_end}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Globe size={12} className="text-gray-500" />
                      <span>GW: {pool.gateway}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Network size={12} className="text-gray-500" />
                      <span>DNS: {pool.dns_servers.join(", ")}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock size={12} className="text-gray-500" />
                      <span>
                        Lease:{" "}
                        {Math.round(pool.lease_time_seconds / 3600)} saat
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              {pools.length === 0 && (
                <p className="text-gray-500 text-center py-4 text-sm">
                  Henüz havuz yok.
                </p>
              )}
            </div>
          </GlassCard>
        </div>
      )}

      {/* --- HAVUZ OLUSTURMA / DUZENLEME MODAL --- */}
      {poolModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Arka plan overlay */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closePoolModal}
          />

          {/* Modal içerik */}
          <div className="relative w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Modal baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Network size={20} className="text-neon-cyan" />
                {editingPool ? "Havuzu Düzenle" : "Yeni DHCP Havuzu"}
              </h3>
              <button
                onClick={closePoolModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form alanlari */}
            <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
              {/* Havuz Adi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Havuz Adi <span className="text-neon-red">*</span>
                </label>
                <input
                  type="text"
                  value={poolForm.name}
                  onChange={(e) =>
                    setPoolForm((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  placeholder="örn. Ana AG, Misafir AG"
                  className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                    poolFormErrors.name
                      ? "border-neon-red/50 focus:border-neon-red"
                      : "border-white/10 focus:border-neon-cyan/50"
                  }`}
                />
                {poolFormErrors.name && (
                  <p className="text-xs text-neon-red mt-1">
                    Havuz adi zorunludur.
                  </p>
                )}
              </div>

              {/* Subnet + Netmask */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Subnet <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={poolForm.subnet}
                    onChange={(e) =>
                      setPoolForm((prev) => ({
                        ...prev,
                        subnet: e.target.value,
                      }))
                    }
                    placeholder="192.168.1.0"
                    className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      poolFormErrors.subnet
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Netmask <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={poolForm.netmask}
                    onChange={(e) =>
                      setPoolForm((prev) => ({
                        ...prev,
                        netmask: e.target.value,
                      }))
                    }
                    placeholder="255.255.255.0"
                    className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      poolFormErrors.netmask
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
              </div>

              {/* IP Aralığı */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Aralık Başlangic <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={poolForm.range_start}
                    onChange={(e) =>
                      setPoolForm((prev) => ({
                        ...prev,
                        range_start: e.target.value,
                      }))
                    }
                    placeholder="192.168.1.100"
                    className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      poolFormErrors.range_start
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Aralık Bitiş <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={poolForm.range_end}
                    onChange={(e) =>
                      setPoolForm((prev) => ({
                        ...prev,
                        range_end: e.target.value,
                      }))
                    }
                    placeholder="192.168.1.200"
                    className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      poolFormErrors.range_end
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
              </div>

              {/* Gateway */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Gateway <span className="text-neon-red">*</span>
                </label>
                <div className="relative">
                  <Globe
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="text"
                    value={poolForm.gateway}
                    onChange={(e) =>
                      setPoolForm((prev) => ({
                        ...prev,
                        gateway: e.target.value,
                      }))
                    }
                    placeholder="192.168.1.1"
                    className={`w-full pl-10 pr-4 bg-surface-800 border rounded-xl py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      poolFormErrors.gateway
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
              </div>

              {/* DNS Sunuculari */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  DNS Sunuculari <span className="text-neon-red">*</span>
                </label>
                <input
                  type="text"
                  value={poolForm.dns_servers}
                  onChange={(e) =>
                    setPoolForm((prev) => ({
                      ...prev,
                      dns_servers: e.target.value,
                    }))
                  }
                  placeholder="8.8.8.8, 8.8.4.4"
                  className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                    poolFormErrors.dns_servers
                      ? "border-neon-red/50 focus:border-neon-red"
                      : "border-white/10 focus:border-neon-cyan/50"
                  }`}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Birden fazla sunucu için virgül ile ayirin.
                </p>
              </div>

              {/* Lease Süresi + Durum */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Lease Süresi (saniye)
                  </label>
                  <div className="relative">
                    <Clock
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                    />
                    <input
                      type="number"
                      min="300"
                      value={poolForm.lease_time_seconds}
                      onChange={(e) =>
                        setPoolForm((prev) => ({
                          ...prev,
                          lease_time_seconds: e.target.value,
                        }))
                      }
                      className={`w-full pl-10 pr-4 bg-surface-800 border rounded-xl py-2.5 text-sm text-white focus:outline-none transition-colors ${
                        poolFormErrors.lease_time_seconds
                          ? "border-neon-red/50 focus:border-neon-red"
                          : "border-white/10 focus:border-neon-cyan/50"
                      }`}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {poolForm.lease_time_seconds &&
                    parseInt(poolForm.lease_time_seconds) > 0
                      ? `= ${Math.round(
                          parseInt(poolForm.lease_time_seconds) / 3600
                        )} saat`
                      : ""}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Durum
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setPoolForm((prev) => ({
                        ...prev,
                        enabled: !prev.enabled,
                      }))
                    }
                    className={`w-full py-2.5 text-sm rounded-xl border transition-all ${
                      poolForm.enabled
                        ? "bg-neon-green/10 text-neon-green border-neon-green/20 hover:bg-neon-green/20"
                        : "bg-surface-800 text-gray-400 border-white/10 hover:border-white/20"
                    }`}
                  >
                    {poolForm.enabled ? "Aktif" : "Pasif"}
                  </button>
                </div>
              </div>
            </div>

            {/* Modal alt butonlar */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closePoolModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 hover:text-white transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handlePoolSubmit}
                disabled={submitting}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Kaydediliyor...
                  </>
                ) : editingPool ? (
                  "Güncelle"
                ) : (
                  "Oluştur"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
