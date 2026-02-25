// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Sistem Yönetimi Sayfasi: servis kontrol, reboot, shutdown, boot bilgi,
// safe mode, watchdog, journal görüntüleyici.

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Server,
  RotateCcw,
  Power,
  PowerOff,
  Play,
  Square,
  ShieldAlert,
  Activity,
  Clock,
  Terminal,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Shield,
  Wrench,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchSystemOverview,
  fetchServicesStatus,
  fetchBootInfo,
  fetchJournal,
  restartService,
  startService,
  stopService,
  rebootSystem,
  shutdownSystem,
  resetSafeMode,
} from "../services/systemManagementApi";
import type { ServiceStatus, SystemOverview, BootInfo } from "../types";

// ============================================================================
// Yardimci Fonksiyonlar
// ============================================================================

function formatUptime(seconds: number): string {
  if (!seconds || seconds <= 0) return "-";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}g`);
  if (h > 0) parts.push(`${h}s`);
  parts.push(`${m}dk`);
  return parts.join(" ");
}

function stateColor(state: string): string {
  switch (state) {
    case "active":
      return "text-neon-green";
    case "inactive":
    case "dead":
      return "text-gray-500";
    case "failed":
      return "text-neon-red";
    case "activating":
    case "deactivating":
      return "text-neon-amber";
    default:
      return "text-gray-400";
  }
}

function stateDot(state: string): string {
  switch (state) {
    case "active":
      return "bg-neon-green";
    case "inactive":
    case "dead":
      return "bg-gray-500";
    case "failed":
      return "bg-neon-red";
    default:
      return "bg-neon-amber";
  }
}

function stateLabel(state: string, subState: string): string {
  if (state === "active" && subState === "running") return "AKTIF";
  if (state === "active" && subState === "exited") return "AKTIF (cikti)";
  if (state === "inactive") return "PASIF";
  if (state === "failed") return "BASARISIZ";
  if (state === "activating") return "BASLATIYOR";
  if (state === "deactivating") return "DURDURUYOR";
  return state.toUpperCase();
}

// ============================================================================
// Onay Dialogu Bileşeni
// ============================================================================

function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  variant = "red",
}: {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: "red" | "amber";
}) {
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const colorClass =
    variant === "red"
      ? "border-neon-red/30 bg-neon-red/10 text-neon-red"
      : "border-neon-amber/30 bg-neon-amber/10 text-neon-amber";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass-card border border-glass-border rounded-2xl p-6 max-w-md w-full mx-4">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle size={24} className={variant === "red" ? "text-neon-red" : "text-neon-amber"} />
          <h3 className="text-lg font-bold text-white">{title}</h3>
        </div>
        <p className="text-sm text-gray-300 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-xl text-sm text-gray-400 border border-glass-border hover:bg-glass-light transition-all"
          >
            Iptal
          </button>
          <button
            onClick={onConfirm}
            disabled={countdown > 0}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all disabled:opacity-50 ${colorClass}`}
          >
            {countdown > 0 ? `${confirmLabel} (${countdown})` : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Ana Bilesken
// ============================================================================

export function SystemManagementPage() {
  const { connected } = useWebSocket();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [bootInfo, setBootInfo] = useState<BootInfo | null>(null);
  const [journal, setJournal] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    variant: "red" | "amber";
    action: () => Promise<void>;
  } | null>(null);
  const journalRef = useRef<HTMLDivElement>(null);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadData = useCallback(async () => {
    try {
      const [ovRes, svcRes, bootRes, jrnRes] = await Promise.all([
        fetchSystemOverview(),
        fetchServicesStatus(),
        fetchBootInfo(),
        fetchJournal(50),
      ]);
      setOverview(ovRes.data);
      setServices(svcRes.data);
      setBootInfo(bootRes.data);
      setJournal(jrnRes.data.lines || []);
    } catch (err) {
      console.error("Sistem yönetimi verisi yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Journal auto-scroll
  useEffect(() => {
    if (journalRef.current) {
      journalRef.current.scrollTop = journalRef.current.scrollHeight;
    }
  }, [journal]);

  // ========== Servis İşlemleri ==========
  const handleRestart = async (name: string, label: string) => {
    setConfirmDialog({
      title: "Servisi Yeniden Başlat",
      message: `${label} servisi yeniden başlatilacak. Devam etmek istiyor musunuz?`,
      confirmLabel: "Yeniden Başlat",
      variant: "amber",
      action: async () => {
        setActionLoading(name);
        try {
          await restartService(name);
          showFeedback("success", `${label} yeniden başlatildi`);
          setTimeout(loadData, 2000);
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } } };
          showFeedback("error", e?.response?.data?.detail || "Restart başarısız");
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const handleStart = async (name: string, label: string) => {
    setActionLoading(name);
    try {
      await startService(name);
      showFeedback("success", `${label} başlatildi`);
      setTimeout(loadData, 2000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      showFeedback("error", e?.response?.data?.detail || "Başlatma başarısız");
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (name: string, label: string) => {
    setConfirmDialog({
      title: "Servisi Durdur",
      message: `${label} servisi durdurulacak. Bu işlem sistemi etkileyebilir. Devam etmek istiyor musunuz?`,
      confirmLabel: "Durdur",
      variant: "red",
      action: async () => {
        setActionLoading(name);
        try {
          await stopService(name);
          showFeedback("success", `${label} durduruldu`);
          setTimeout(loadData, 2000);
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } } };
          showFeedback("error", e?.response?.data?.detail || "Durdurma başarısız");
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  // ========== Sistem İşlemleri ==========
  const handleReboot = () => {
    setConfirmDialog({
      title: "Sistemi Yeniden Başlat",
      message: "Sistem 3 saniye içinde yeniden başlatilacak. Tum servisler kapanacak ve yeniden açılacak. SSH bağlantınizi kaybedeceksiniz.",
      confirmLabel: "Yeniden Başlat",
      variant: "red",
      action: async () => {
        try {
          await rebootSystem();
          showFeedback("success", "Sistem 3 saniye içinde yeniden başlatilacak...");
        } catch {
          showFeedback("error", "Reboot başlatilamadi");
        }
      },
    });
  };

  const handleShutdown = () => {
    setConfirmDialog({
      title: "Sistemi Kapat",
      message: "Sistem 3 saniye içinde kapanacak. Fiziksel olarak yeniden başlatmaniz gerekecek. Emin misiniz?",
      confirmLabel: "Kapat",
      variant: "red",
      action: async () => {
        try {
          await shutdownSystem();
          showFeedback("success", "Sistem 3 saniye içinde kapanacak...");
        } catch {
          showFeedback("error", "Shutdown başlatilamadi");
        }
      },
    });
  };

  const handleResetSafeMode = () => {
    setConfirmDialog({
      title: "Safe Mode Sifirla",
      message: "Boot sayacı sıfırlanacak, safe mode kaldirilacak ve durdurulan servisler (backend, nginx) yeniden başlatilacak.",
      confirmLabel: "Sifirla",
      variant: "amber",
      action: async () => {
        try {
          await resetSafeMode();
          showFeedback("success", "Safe mode sıfırlandi, servisler başlatildi");
          setTimeout(loadData, 3000);
        } catch {
          showFeedback("error", "Safe mode sıfırlanamadi");
        }
      },
    });
  };

  const handleRefreshJournal = async () => {
    try {
      const res = await fetchJournal(50);
      setJournal(res.data.lines || []);
    } catch {
      showFeedback("error", "Journal yüklenemedi");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <TopBar title="Sistem Yönetimi" connected={connected} />

      {/* Feedback */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border mb-6 ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          {feedback.message}
        </div>
      )}

      {/* Onay Dialogu */}
      {confirmDialog && (
        <ConfirmDialog
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmLabel={confirmDialog.confirmLabel}
          variant={confirmDialog.variant}
          onConfirm={async () => {
            setConfirmDialog(null);
            await confirmDialog.action();
          }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}

      {/* ============ BOLUM 1: Sistem Durumu + İşlemler ============ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Sol: Sistem Durumu */}
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-neon-cyan/10 border border-neon-cyan/20 flex items-center justify-center">
                <Activity size={20} className="text-neon-cyan" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Sistem Durumu</h3>
                <p className="text-xs text-gray-500">
                  {overview?.hostname || "-"}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Uptime */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <Clock size={14} />
                  <span>Calisma Süresi</span>
                </div>
                <span className="text-sm text-white font-mono">
                  {overview ? formatUptime(overview.uptime_seconds) : "-"}
                </span>
              </div>

              {/* Son boot */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Son Boot</span>
                <span className="text-xs text-gray-300 font-mono">
                  {overview?.boot_time || "-"}
                </span>
              </div>

              {/* Boot sayacı */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Boot Sayacı</span>
                <NeonBadge
                  label={`${bootInfo?.boot_count ?? 0} / ${bootInfo?.max_boots_threshold ?? 5}`}
                  variant={
                    (bootInfo?.boot_count ?? 0) >= 3
                      ? "red"
                      : (bootInfo?.boot_count ?? 0) >= 1
                      ? "amber"
                      : "green"
                  }
                />
              </div>

              {/* Safe mode */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <ShieldAlert size={14} />
                  <span>Safe Mode</span>
                </div>
                <NeonBadge
                  label={overview?.safe_mode ? "AKTIF" : "PASIF"}
                  variant={overview?.safe_mode ? "red" : "green"}
                />
              </div>

              {/* Watchdog */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <Shield size={14} />
                  <span>Watchdog</span>
                </div>
                <NeonBadge
                  label={overview?.watchdog_active ? "AKTIF" : "PASIF"}
                  variant={overview?.watchdog_active ? "green" : "amber"}
                />
              </div>
            </div>

            {/* Safe mode uyarısı */}
            {overview?.safe_mode && (
              <div className="mt-4 p-3 rounded-xl bg-neon-red/10 border border-neon-red/20">
                <p className="text-xs text-neon-red">
                  <AlertTriangle size={12} className="inline mr-1" />
                  Sistem safe mode'da! Tekrarli boot tespit edildi. Backend ve Nginx durduruldu.
                  SSH erişimi aktif. Safe mode'u sıfırlamak için aşağıdaki butonu kullanın.
                </p>
              </div>
            )}
          </div>
        </GlassCard>

        {/* Sag: Sistem İşlemleri */}
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-neon-amber/10 border border-neon-amber/20 flex items-center justify-center">
                <Wrench size={20} className="text-neon-amber" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Sistem İşlemleri
                </h3>
                <p className="text-xs text-gray-500">
                  Kritik işlemler onay gerektirir
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {/* Yeniden başlat */}
              <button
                onClick={handleReboot}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-neon-red/10 border border-neon-red/20 text-neon-red text-sm font-medium hover:bg-neon-red/20 transition-all"
              >
                <RotateCcw size={16} />
                Sistemi Yeniden Başlat
              </button>

              {/* Kapat */}
              <button
                onClick={handleShutdown}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-900/20 border border-red-900/30 text-red-400 text-sm font-medium hover:bg-red-900/30 transition-all"
              >
                <PowerOff size={16} />
                Sistemi Kapat
              </button>

              {/* Safe mode sıfırla */}
              {overview?.safe_mode && (
                <button
                  onClick={handleResetSafeMode}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-neon-amber/10 border border-neon-amber/20 text-neon-amber text-sm font-medium hover:bg-neon-amber/20 transition-all"
                >
                  <ShieldAlert size={16} />
                  Safe Mode Sifirla
                </button>
              )}

              {/* Bilgi kutusu */}
              <div className="mt-4 p-3 rounded-xl bg-surface-800/50 border border-glass-border">
                <p className="text-[10px] text-gray-500 leading-relaxed">
                  <strong className="text-gray-400">Watchdog:</strong> Sistem takilirsa 15sn içinde otomatik reboot.{" "}
                  <strong className="text-gray-400">Safe Mode:</strong> 5 art arda başarısız boot'ta aktif olur — sadece SSH ve ag çalışır.{" "}
                  <strong className="text-gray-400">Boot Sayacı:</strong> Başarılı 2dk çalışma sonrası sıfırlanir.
                </p>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* ============ BOLUM 2: Servis Yönetimi ============ */}
      <GlassCard>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-neon-cyan/10 border border-neon-cyan/20 flex items-center justify-center">
                <Server size={20} className="text-neon-cyan" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Servis Yönetimi
                </h3>
                <p className="text-xs text-gray-500">
                  {services.filter((s) => s.active_state === "active").length} /{" "}
                  {services.length} aktif
                </p>
              </div>
            </div>
            <button
              onClick={loadData}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-gray-400 border border-glass-border hover:text-white hover:bg-glass-light transition-all"
            >
              <RefreshCw size={12} />
              Yenile
            </button>
          </div>

          {/* Tablo */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-glass-border">
                  <th className="pb-3 pl-2">Servis</th>
                  <th className="pb-3">Durum</th>
                  <th className="pb-3 hidden md:table-cell">PID</th>
                  <th className="pb-3 hidden md:table-cell">Bellek</th>
                  <th className="pb-3 hidden lg:table-cell">Uptime</th>
                  <th className="pb-3 hidden lg:table-cell">Restart</th>
                  <th className="pb-3 text-right pr-2">İşlemler</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc) => (
                  <tr
                    key={svc.name}
                    className="border-b border-glass-border/50 hover:bg-glass-light/30 transition-colors"
                  >
                    {/* Servis adi */}
                    <td className="py-3 pl-2">
                      <div className="flex items-center gap-2">
                        {svc.critical && (
                          <AlertTriangle
                            size={12}
                            className="text-neon-amber flex-shrink-0"
                          />
                        )}
                        <div>
                          <p className="text-white font-medium">{svc.label}</p>
                          <p className="text-[10px] text-gray-500 font-mono">
                            {svc.name}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Durum */}
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${stateDot(
                            svc.active_state
                          )}`}
                        />
                        <span
                          className={`text-xs font-medium ${stateColor(
                            svc.active_state
                          )}`}
                        >
                          {stateLabel(svc.active_state, svc.sub_state)}
                        </span>
                      </div>
                    </td>

                    {/* PID */}
                    <td className="py-3 hidden md:table-cell">
                      <span className="text-xs text-gray-400 font-mono">
                        {svc.pid || "-"}
                      </span>
                    </td>

                    {/* Bellek */}
                    <td className="py-3 hidden md:table-cell">
                      <span className="text-xs text-gray-400 font-mono">
                        {svc.memory_mb != null
                          ? `${svc.memory_mb} MB`
                          : "-"}
                      </span>
                    </td>

                    {/* Uptime */}
                    <td className="py-3 hidden lg:table-cell">
                      <span className="text-xs text-gray-400">
                        {svc.uptime_seconds != null
                          ? formatUptime(svc.uptime_seconds)
                          : "-"}
                      </span>
                    </td>

                    {/* Restart count */}
                    <td className="py-3 hidden lg:table-cell">
                      <span className="text-xs text-gray-400 font-mono">
                        {svc.restart_count ?? "-"}
                      </span>
                    </td>

                    {/* İşlemler */}
                    <td className="py-3 text-right pr-2">
                      <div className="flex items-center gap-1 justify-end">
                        {svc.active_state === "active" ? (
                          <>
                            <button
                              onClick={() =>
                                handleRestart(svc.name, svc.label)
                              }
                              disabled={actionLoading === svc.name}
                              className="px-2 py-1 rounded-lg text-[10px] font-medium text-neon-amber border border-neon-amber/20 bg-neon-amber/10 hover:bg-neon-amber/20 transition-all disabled:opacity-50"
                              title="Yeniden Başlat"
                            >
                              {actionLoading === svc.name ? (
                                <RotateCcw
                                  size={10}
                                  className="animate-spin"
                                />
                              ) : (
                                <RotateCcw size={10} />
                              )}
                            </button>
                            {svc.name !== "ssh" && (
                              <button
                                onClick={() =>
                                  handleStop(svc.name, svc.label)
                                }
                                disabled={actionLoading === svc.name}
                                className="px-2 py-1 rounded-lg text-[10px] font-medium text-neon-red border border-neon-red/20 bg-neon-red/10 hover:bg-neon-red/20 transition-all disabled:opacity-50"
                                title="Durdur"
                              >
                                <Square size={10} />
                              </button>
                            )}
                          </>
                        ) : (
                          <button
                            onClick={() =>
                              handleStart(svc.name, svc.label)
                            }
                            disabled={actionLoading === svc.name}
                            className="px-2 py-1 rounded-lg text-[10px] font-medium text-neon-green border border-neon-green/20 bg-neon-green/10 hover:bg-neon-green/20 transition-all disabled:opacity-50"
                            title="Başlat"
                          >
                            <Play size={10} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </GlassCard>

      {/* ============ BOLUM 3: Sistem Journal ============ */}
      <div className="mt-6">
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-neon-green/10 border border-neon-green/20 flex items-center justify-center">
                  <Terminal size={20} className="text-neon-green" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Sistem Journal
                  </h3>
                  <p className="text-xs text-gray-500">
                    Son 50 satir (journalctl)
                  </p>
                </div>
              </div>
              <button
                onClick={handleRefreshJournal}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-gray-400 border border-glass-border hover:text-white hover:bg-glass-light transition-all"
              >
                <RefreshCw size={12} />
                Yenile
              </button>
            </div>

            <div
              ref={journalRef}
              className="bg-black/60 rounded-xl border border-glass-border p-4 h-64 overflow-y-auto font-mono text-[11px] leading-relaxed"
            >
              {journal.length === 0 ? (
                <p className="text-gray-500">Journal kaydi yok</p>
              ) : (
                journal.map((line, i) => (
                  <div
                    key={i}
                    className={`${
                      line.includes("error") || line.includes("Error") || line.includes("HATA")
                        ? "text-neon-red"
                        : line.includes("warning") || line.includes("Warning")
                        ? "text-neon-amber"
                        : line.includes("tonbilai")
                        ? "text-neon-cyan"
                        : "text-gray-300"
                    }`}
                  >
                    {line}
                  </div>
                ))
              )}
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
