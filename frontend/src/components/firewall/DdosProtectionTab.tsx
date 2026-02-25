// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// DDoS Koruma sekmesi: 8 koruma karti, toggle, parametre ayarları.

import { useState, useEffect, useCallback } from "react";
import { Shield, ShieldCheck, RefreshCw, Save, AlertTriangle, Trash2 } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import { LoadingSpinner } from "../common/LoadingSpinner";
import {
  fetchDdosConfig,
  updateDdosConfig,
  applyDdosRules,
  toggleDdosProtection,
  fetchDdosStatus,
  fetchDdosCounters,
  flushDdosAttackers,
} from "../../services/ddosApi";
import type { DdosConfig, DdosProtectionStatus } from "../../types";

interface ProtectionCardDef {
  name: string;
  title: string;
  icon: string;
  enabledField: keyof DdosConfig;
  params: Array<{
    field: keyof DdosConfig;
    label: string;
    type: "number" | "text";
    suffix?: string;
    min?: number;
    max?: number;
  }>;
  warning?: string;
}

const PROTECTIONS: ProtectionCardDef[] = [
  {
    name: "syn_flood",
    title: "SYN Flood Korumasi",
    icon: "🛡️",
    enabledField: "syn_flood_enabled",
    params: [
      { field: "syn_flood_rate", label: "Limit", type: "number", suffix: "paket/sn", min: 1, max: 10000 },
      { field: "syn_flood_burst", label: "Burst", type: "number", suffix: "paket", min: 1, max: 50000 },
    ],
  },
  {
    name: "udp_flood",
    title: "UDP Flood Korumasi",
    icon: "🔒",
    enabledField: "udp_flood_enabled",
    params: [
      { field: "udp_flood_rate", label: "Limit", type: "number", suffix: "paket/sn", min: 1, max: 10000 },
      { field: "udp_flood_burst", label: "Burst", type: "number", suffix: "paket", min: 1, max: 50000 },
    ],
  },
  {
    name: "icmp_flood",
    title: "ICMP Flood Korumasi",
    icon: "📡",
    enabledField: "icmp_flood_enabled",
    params: [
      { field: "icmp_flood_rate", label: "Limit", type: "number", suffix: "paket/sn", min: 1, max: 1000 },
      { field: "icmp_flood_burst", label: "Burst", type: "number", suffix: "paket", min: 1, max: 5000 },
    ],
  },
  {
    name: "conn_limit",
    title: "Bağlantı Limiti (Per-IP)",
    icon: "🔗",
    enabledField: "conn_limit_enabled",
    params: [
      { field: "conn_limit_per_ip", label: "Maks. Bağlantı", type: "number", suffix: "adet/IP", min: 10, max: 10000 },
    ],
  },
  {
    name: "invalid_packet",
    title: "Geçersiz Paket Filtreleme",
    icon: "🚫",
    enabledField: "invalid_packet_enabled",
    params: [],
  },
  {
    name: "http_flood",
    title: "HTTP Flood Korumasi",
    icon: "🌐",
    enabledField: "http_flood_enabled",
    params: [
      { field: "http_flood_rate", label: "Rate", type: "text", suffix: "" },
      { field: "http_flood_burst", label: "Burst", type: "number", suffix: "istek", min: 1, max: 1000 },
    ],
    warning: "Nginx otomatik reload edilir",
  },
  {
    name: "kernel_hardening",
    title: "Kernel Sertlestirme",
    icon: "⚙️",
    enabledField: "kernel_hardening_enabled",
    params: [
      { field: "tcp_max_syn_backlog", label: "SYN Backlog", type: "number", suffix: "", min: 256, max: 65536 },
      { field: "tcp_synack_retries", label: "SYN-ACK Retry", type: "number", suffix: "", min: 1, max: 10 },
      { field: "netfilter_conntrack_max", label: "Conntrack Max", type: "number", suffix: "", min: 65536, max: 1048576 },
    ],
  },
  {
    name: "uvicorn_workers",
    title: "Uvicorn Worker Sayısı",
    icon: "🔧",
    enabledField: "uvicorn_workers_enabled",
    params: [
      { field: "uvicorn_workers", label: "Worker", type: "number", suffix: "adet", min: 1, max: 4 },
    ],
    warning: "Backend otomatik restart edilir",
  },
];

export function DdosProtectionTab() {
  const [config, setConfig] = useState<DdosConfig | null>(null);
  const [statuses, setStatuses] = useState<DdosProtectionStatus[]>([]);
  const [counters, setCounters] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [flushing, setFlushing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editedConfig, setEditedConfig] = useState<Partial<DdosConfig>>({});

  const loadData = useCallback(async () => {
    try {
      const [configRes, statusRes, counterRes] = await Promise.all([
        fetchDdosConfig(),
        fetchDdosStatus(),
        fetchDdosCounters(),
      ]);
      setConfig(configRes.data);
      setStatuses(statusRes.data);
      setCounters(counterRes.data);
      setEditedConfig({});
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Veri yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleToggle = async (protectionName: string) => {
    setToggling(protectionName);
    setError(null);
    setSuccess(null);
    try {
      const res = await toggleDdosProtection(protectionName);
      setSuccess(
        `${protectionName} ${res.data.enabled ? "aktif edildi" : "devre disi birakildi"}`
      );
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Toggle başarısız");
    } finally {
      setToggling(null);
    }
  };

  const handleParamChange = (field: keyof DdosConfig, value: string | number) => {
    setEditedConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    if (Object.keys(editedConfig).length === 0) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await updateDdosConfig(editedConfig);
      setSuccess("Ayarlar kaydedildi ve kurallar uygulandı");
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Kaydetme başarısız");
    } finally {
      setSaving(false);
    }
  };

  const handleApplyAll = async () => {
    setApplying(true);
    setError(null);
    setSuccess(null);
    try {
      await applyDdosRules();
      setSuccess("Tum kurallar yeniden uygulandı");
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Uygulama başarısız");
    } finally {
      setApplying(false);
    }
  };


  const handleFlushAttackers = async () => {
    setFlushing(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await flushDdosAttackers();
      const total = res.data?.total_cleared || 0;
      setSuccess(`DDoS engellenen IP'ler temizlendi (${total} IP)`);
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Temizleme başarısız");
    } finally {
      setFlushing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-8 text-gray-400">
        DDoS yapılandirmasi yüklenemedi
      </div>
    );
  }

  const getStatus = (name: string): DdosProtectionStatus | undefined =>
    statuses.find((s) => s.name === name);

  const getConfigValue = (field: keyof DdosConfig): any => {
    if (field in editedConfig) return (editedConfig as any)[field];
    return (config as any)[field];
  };

  const hasChanges = Object.keys(editedConfig).length > 0;

  return (
    <div className="space-y-4">
      {/* Baslik + İşlem butonlari */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Shield size={20} className="text-neon-cyan" />
          <h2 className="text-lg font-semibold text-white">DDoS Koruma Yönetimi</h2>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neon-green/20 text-neon-green border border-neon-green/30 hover:bg-neon-green/30 transition text-sm disabled:opacity-50"
            >
              <Save size={14} />
              {saving ? "Kaydediliyor..." : "Kaydet ve Uygula"}
            </button>
          )}
          <button
            onClick={handleFlushAttackers}
            disabled={flushing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition text-sm disabled:opacity-50"
          >
            <Trash2 size={14} />
            {flushing ? "Temizleniyor..." : "Engelleri Temizle"}
          </button>
          <button
            onClick={handleApplyAll}
            disabled={applying}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/30 transition text-sm disabled:opacity-50"
          >
            <RefreshCw size={14} className={applying ? "animate-spin" : ""} />
            {applying ? "Uygulanıyor..." : "Tümü Yeniden Uygula"}
          </button>
        </div>
      </div>

      {/* Bildirimler */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 rounded-lg bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm">
          {success}
        </div>
      )}

      {/* Engellenen Paket Özeti */}
      {counters && counters.total_dropped_packets > 0 && (
        <GlassCard neonColor="red" className="!p-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <Shield size={18} className="text-red-400" />
              <span className="text-sm font-medium text-white">
                Toplam Engellenen:{" "}
                <span className="text-red-400 font-bold">
                  {counters.total_dropped_packets.toLocaleString()}
                </span>{" "}
                paket
              </span>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-gray-400">
              {counters.by_protection &&
                Object.entries(counters.by_protection).map(
                  ([name, data]: [string, any]) =>
                    data.packets > 0 && (
                      <span key={name} className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-red-400/60" />
                        {name}: {data.packets.toLocaleString()}
                      </span>
                    )
                )}
            </div>
          </div>
        </GlassCard>
      )}

      {/* Koruma Kartlari */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {PROTECTIONS.map((prot) => {
          const status = getStatus(prot.name);
          const isEnabled = getConfigValue(prot.enabledField) as boolean;
          const isToggling = toggling === prot.name;

          return (
            <GlassCard
              key={prot.name}
              className="!p-4"
              neonColor={isEnabled ? "cyan" : undefined}
            >
              {/* Kart Baslik */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{prot.icon}</span>
                  <h3 className="text-sm font-semibold text-white">{prot.title}</h3>
                </div>
                <div className="flex items-center gap-2">
                  {/* Durum Badge */}
                  {status && (
                    <NeonBadge
                      label={
                        status.active
                          ? "AKTIF"
                          : status.enabled
                          ? "UYGULANMADI"
                          : "PASIF"
                      }
                      variant={
                        status.active
                          ? "green"
                          : status.enabled
                          ? "amber"
                          : "red"
                      }
                      pulse={status.active}
                    />
                  )}
                  {/* Toggle */}
                  <button
                    onClick={() => handleToggle(prot.name)}
                    disabled={isToggling}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      isEnabled
                        ? "bg-neon-cyan/40 border border-neon-cyan/50"
                        : "bg-dark-400 border border-dark-300"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full transition-transform ${
                        isEnabled
                          ? "translate-x-6 bg-neon-cyan"
                          : "translate-x-1 bg-gray-500"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Açıklama */}
              <p className="text-xs text-gray-400 mb-3">
                {status?.description || ""}
              </p>

              {/* Uyari */}
              {prot.warning && (
                <div className="flex items-center gap-1 text-xs text-yellow-400 mb-2">
                  <AlertTriangle size={12} />
                  <span>{prot.warning}</span>
                </div>
              )}

              {/* Parametreler */}
              {prot.params.length > 0 && isEnabled && (
                <div className="flex flex-wrap gap-2 mt-1">
                  {prot.params.map((param) => (
                    <div key={param.field} className="flex items-center gap-1.5">
                      <label className="text-xs text-gray-400 whitespace-nowrap">
                        {param.label}:
                      </label>
                      <input
                        type={param.type}
                        value={getConfigValue(param.field)}
                        onChange={(e) =>
                          handleParamChange(
                            param.field,
                            param.type === "number"
                              ? parseInt(e.target.value) || 0
                              : e.target.value
                          )
                        }
                        min={param.min}
                        max={param.max}
                        className="w-20 px-2 py-1 rounded bg-black/60 border border-gray-600 text-gray-100 text-xs focus:border-neon-cyan/50 focus:outline-none placeholder-gray-500"
                      />
                      {param.suffix && (
                        <span className="text-xs text-gray-500">{param.suffix}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          );
        })}
      </div>

      {/* Bilgi Karti */}
      <GlassCard className="!p-3">
        <div className="flex items-start gap-2">
          <ShieldCheck size={16} className="text-neon-cyan mt-0.5" />
          <div className="text-xs text-gray-400">
            <p className="font-medium text-gray-300 mb-1">DDoS Koruma Hakkında</p>
            <p>
              Kurallar nftables (ag katmani), sysctl (kernel) ve nginx (uygulama katmani)
              üzerinden uygulanir. Toggle ile aktif/pasif yapabilir, parametreleri
              ihtiyacınıza göre ayarlayabilirsiniz. Değişiklikler anında uygulanir.
            </p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
