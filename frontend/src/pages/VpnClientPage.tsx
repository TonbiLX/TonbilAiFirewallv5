// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// Dış VPN İstemci sayfası: WireGuard ile dis VPN sunucusuna baglanma
// .conf dosya yükleme, yapıştırma, manuel giriş desteği

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Globe,
  Plus,
  Trash2,
  Pencil,
  Power,
  PowerOff,
  Server,
  Upload,
  FileUp,
  X,
  AlertTriangle,
  CheckCircle,
  MapPin,
  Signal,
  ArrowDownCircle,
  ArrowUpCircle,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchVpnClientServers,
  fetchVpnClientStats,
  fetchVpnClientStatus,
  createVpnClientServer,
  updateVpnClientServer,
  deleteVpnClientServer,
  activateVpnClientServer,
  deactivateVpnClientServer,
  importVpnClientConfig,
  clearMockServers,
} from "../services/vpnClientApi";
import type {
  VpnClientServer,
  VpnClientStats,
  VpnClientStatus,
  VpnClientServerCreate,
  VpnClientServerUpdate,
} from "../services/vpnClientApi";

// --- Ülke kodu -> bayrak emoji ---
function countryCodeToFlag(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return "";
  const code = countryCode.toUpperCase();
  const offset = 0x1f1e6;
  const A = "A".charCodeAt(0);
  return (
    String.fromCodePoint(code.charCodeAt(0) - A + offset) +
    String.fromCodePoint(code.charCodeAt(1) - A + offset)
  );
}

// --- Byte formatla ---
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

// --- bps formatla ---
function formatBps(bps: number): string {
  if (bps === 0) return "0 bps";
  if (bps < 1000) return bps + " bps";
  if (bps < 1000000) return (bps / 1000).toFixed(1) + " Kbps";
  if (bps < 1000000000) return (bps / 1000000).toFixed(1) + " Mbps";
  return (bps / 1000000000).toFixed(2) + " Gbps";
}

// --- Sure formatla ---
function formatUptime(seconds: number): string {
  if (seconds <= 0) return "--";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}s ${m}dk`;
  if (m > 0) return `${m}dk ${s}sn`;
  return `${s}sn`;
}

// --- Form yapilari ---
interface ServerFormData {
  name: string;
  country: string;
  country_code: string;
  endpoint: string;
  public_key: string;
  private_key: string;
  preshared_key: string;
  interface_address: string;
  allowed_ips: string;
  dns_servers: string;
  mtu: string;
  persistent_keepalive: string;
}

const emptyServerForm: ServerFormData = {
  name: "",
  country: "",
  country_code: "",
  endpoint: "",
  public_key: "",
  private_key: "",
  preshared_key: "",
  interface_address: "",
  allowed_ips: "0.0.0.0/0, ::/0",
  dns_servers: "1.1.1.1, 8.8.8.8",
  mtu: "1420",
  persistent_keepalive: "25",
};

interface ImportFormData {
  name: string;
  country: string;
  country_code: string;
  config_text: string;
}

const emptyImportForm: ImportFormData = {
  name: "",
  country: "",
  country_code: "",
  config_text: "",
};

export function VpnClientPage() {
  const { connected } = useWebSocket();
  const [servers, setServers] = useState<VpnClientServer[]>([]);
  const [stats, setStats] = useState<VpnClientStats | null>(null);
  const [vpnStatus, setVpnStatus] = useState<VpnClientStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Sunucu ekleme/düzenleme modal
  const [serverModalOpen, setServerModalOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<VpnClientServer | null>(
    null
  );
  const [serverForm, setServerForm] =
    useState<ServerFormData>(emptyServerForm);
  const [submitting, setSubmitting] = useState(false);

  // Import modal
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importForm, setImportForm] =
    useState<ImportFormData>(emptyImportForm);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  const loadData = useCallback(async () => {
    try {
      const [serversData, statsData, statusData] = await Promise.all([
        fetchVpnClientServers(),
        fetchVpnClientStats(),
        fetchVpnClientStatus(),
      ]);
      setServers(serversData);
      setStats(statsData);
      setVpnStatus(statusData);
      setError(null);
    } catch (err) {
      setError("VPN istemci verileri yüklenemedi");
      console.error("VPN Client veri yükleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  // --- Sunucu aktif/pasif ---
  const handleActivate = async (id: number) => {
    try {
      const result = await activateVpnClientServer(id);
      setFeedback({
        type: "success",
        message: result.message || "VPN bağlantısi başlatiliyor...",
      });
      await loadData();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || "Sunucu aktif edilemedi.";
      setFeedback({ type: "error", message: msg });
    }
  };

  const handleDeactivate = async (id: number) => {
    try {
      const result = await deactivateVpnClientServer(id);
      setFeedback({
        type: "success",
        message: result.message || "VPN bağlantısi kapatiliyor...",
      });
      await loadData();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || "Sunucu deaktif edilemedi.";
      setFeedback({ type: "error", message: msg });
    }
  };

  // --- Sunucu silme ---
  const handleDelete = async (id: number) => {
    try {
      await deleteVpnClientServer(id);
      setFeedback({ type: "success", message: "Sunucu silindi." });
      await loadData();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        "Sunucu silinemedi. Aktif sunucu silinemez.";
      setFeedback({ type: "error", message: msg });
    }
  };

  // --- Mock temizle ---
  const handleClearMock = async () => {
    try {
      const result = await clearMockServers();
      setFeedback({
        type: "success",
        message: `${result.deleted} test sunucusu temizlendi.`,
      });
      await loadData();
    } catch (err) {
      console.error("Mock temizleme hatasi:", err);
    }
  };

  // --- Sunucu ekleme/düzenleme modal ---
  const openCreateModal = () => {
    setEditingServer(null);
    setServerForm(emptyServerForm);
    setServerModalOpen(true);
  };

  const openEditModal = (server: VpnClientServer) => {
    setEditingServer(server);
    setServerForm({
      name: server.name,
      country: server.country,
      country_code: server.country_code,
      endpoint: server.endpoint,
      public_key: server.public_key,
      private_key: "",
      preshared_key: "",
      interface_address: server.interface_address || "",
      allowed_ips: server.allowed_ips,
      dns_servers: server.dns_servers || "",
      mtu: server.mtu.toString(),
      persistent_keepalive: server.persistent_keepalive.toString(),
    });
    setServerModalOpen(true);
  };

  const closeServerModal = () => {
    setServerModalOpen(false);
    setEditingServer(null);
    setServerForm(emptyServerForm);
  };

  const handleServerSubmit = async () => {
    if (!serverForm.name.trim() || !serverForm.endpoint.trim()) return;
    setSubmitting(true);
    try {
      if (editingServer) {
        const payload: VpnClientServerUpdate = {};
        if (serverForm.name.trim()) payload.name = serverForm.name.trim();
        if (serverForm.country.trim())
          payload.country = serverForm.country.trim();
        if (serverForm.country_code.trim())
          payload.country_code = serverForm.country_code
            .trim()
            .toUpperCase();
        if (serverForm.endpoint.trim())
          payload.endpoint = serverForm.endpoint.trim();
        if (serverForm.public_key.trim())
          payload.public_key = serverForm.public_key.trim();
        if (serverForm.private_key.trim())
          payload.private_key = serverForm.private_key.trim();
        if (serverForm.preshared_key.trim())
          payload.preshared_key = serverForm.preshared_key.trim();
        if (serverForm.interface_address.trim())
          payload.interface_address = serverForm.interface_address.trim();
        if (serverForm.allowed_ips.trim())
          payload.allowed_ips = serverForm.allowed_ips.trim();
        if (serverForm.dns_servers.trim())
          payload.dns_servers = serverForm.dns_servers.trim();
        payload.mtu = parseInt(serverForm.mtu, 10) || 1420;
        payload.persistent_keepalive =
          parseInt(serverForm.persistent_keepalive, 10) || 25;

        await updateVpnClientServer(editingServer.id, payload);
        setFeedback({
          type: "success",
          message: `"${serverForm.name}" güncellendi.`,
        });
      } else {
        const payload: VpnClientServerCreate = {
          name: serverForm.name.trim(),
          country: serverForm.country.trim() || "Bilinmiyor",
          country_code:
            serverForm.country_code.trim().toUpperCase() || "XX",
          endpoint: serverForm.endpoint.trim(),
          public_key: serverForm.public_key.trim(),
          private_key: serverForm.private_key.trim() || undefined,
          preshared_key: serverForm.preshared_key.trim() || undefined,
          interface_address:
            serverForm.interface_address.trim() || undefined,
          allowed_ips: serverForm.allowed_ips.trim() || "0.0.0.0/0, ::/0",
          dns_servers: serverForm.dns_servers.trim() || undefined,
          mtu: parseInt(serverForm.mtu, 10) || 1420,
          persistent_keepalive:
            parseInt(serverForm.persistent_keepalive, 10) || 25,
        };
        await createVpnClientServer(payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" eklendi.`,
        });
      }
      closeServerModal();
      await loadData();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || "Sunucu kaydedilirken hata oluştu.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  };

  // --- Config import ---
  const openImportModal = () => {
    setImportForm(emptyImportForm);
    setImportModalOpen(true);
  };

  const closeImportModal = () => {
    setImportModalOpen(false);
    setImportForm(emptyImportForm);
  };

  // --- .conf dosya yükleme ---
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) {
        // Import modal'i ac ve config'i doldur
        const nameFromFile = file.name.replace(/\.conf$/i, "");
        setImportForm({
          name: nameFromFile,
          country: "",
          country_code: "",
          config_text: text,
        });
        setImportModalOpen(true);
      }
    };
    reader.readAsText(file);
    // Input'u sıfırla (ayni dosya tekrar yuklenebilsin)
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleImportSubmit = async () => {
    if (!importForm.name.trim() || !importForm.config_text.trim()) return;
    setImporting(true);
    try {
      await importVpnClientConfig({
        name: importForm.name.trim(),
        country: importForm.country.trim() || undefined,
        country_code: importForm.country_code.trim().toUpperCase() || undefined,
        config_text: importForm.config_text.trim(),
      });
      setFeedback({
        type: "success",
        message: `"${importForm.name.trim()}" iceri aktarildi.`,
      });
      closeImportModal();
      await loadData();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        "Config iceri aktarilirken hata oluştu.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const inputClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors";
  const labelClass =
    "block text-xs text-gray-400 mb-1 uppercase tracking-wider";

  const hasMockServers = servers.some((s) =>
    s.public_key.startsWith("mock_")
  );

  return (
    <div className="space-y-6">
      <TopBar title="Dış VPN İstemci" connected={connected} />

      {/* Gizli dosya input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".conf"
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Hata mesaji */}
      {error && (
        <div className="bg-neon-red/10 border border-neon-red/30 rounded-xl p-4 text-neon-red text-sm">
          {error}
        </div>
      )}

      {/* Geri bildirim */}
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

      {/* Bağlantı Durumu Banneri */}
      {vpnStatus?.connected && (
        <GlassCard neonColor="green">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <Signal size={20} className="text-neon-green animate-pulse" />
              <div>
                <p className="text-sm font-medium text-neon-green">
                  VPN Bağlantısi Aktif
                </p>
                <p className="text-xs text-gray-400">
                  {vpnStatus.active_server}
                  {vpnStatus.active_country_code && vpnStatus.active_country_code !== "XX"
                    ? ` ${countryCodeToFlag(vpnStatus.active_country_code)} ${vpnStatus.active_country}`
                    : vpnStatus.active_country ? ` (${vpnStatus.active_country})` : ""}
                  {" üzerinden trafik yonlendiriliyor"}
                  {vpnStatus.uptime_seconds > 0 && (
                    <span className="ml-2 text-neon-green/70">
                      ({formatUptime(vpnStatus.uptime_seconds)})
                    </span>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              {vpnStatus.speed_rx_bps > 0 || vpnStatus.speed_tx_bps > 0 ? (
                <>
                  <div className="flex items-center gap-1.5 text-xs">
                    <ArrowDownCircle size={14} className="text-neon-cyan" />
                    <span className="font-mono text-neon-cyan font-medium">
                      {formatBps(vpnStatus.speed_rx_bps)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs">
                    <ArrowUpCircle size={14} className="text-neon-magenta" />
                    <span className="font-mono text-neon-magenta font-medium">
                      {formatBps(vpnStatus.speed_tx_bps)}
                    </span>
                  </div>
                </>
              ) : null}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-gray-500">Toplam:</span>
                <span className="font-mono text-gray-300">
                  ↓{formatBytes(vpnStatus.transfer_rx)} ↑{formatBytes(vpnStatus.transfer_tx)}
                </span>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* İstatistik Kartlari */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          <StatCard
            title="Toplam Sunucu"
            value={stats.total_servers}
            icon={<Server size={18} />}
            neonColor="cyan"
          />
          <StatCard
            title="Aktif Sunucu"
            value={stats.active_server || "Yok"}
            icon={<Signal size={18} />}
            neonColor={stats.active_server ? "green" : "red"}
          />
          <StatCard
            title="Aktif Ülke"
            value={
              stats.active_country && stats.active_country !== "Bilinmiyor"
                ? `${countryCodeToFlag(stats.active_country)} ${stats.active_country}`
                : "Yok"
            }
            icon={<MapPin size={18} />}
            neonColor="magenta"
          />
          <StatCard
            title="Indirme"
            value={vpnStatus?.connected ? formatBytes(vpnStatus.session_total_rx || vpnStatus.transfer_rx) : "--"}
            icon={<ArrowDownCircle size={18} />}
            neonColor="cyan"
          />
          <StatCard
            title="Yukleme"
            value={vpnStatus?.connected ? formatBytes(vpnStatus.session_total_tx || vpnStatus.transfer_tx) : "--"}
            icon={<ArrowUpCircle size={18} />}
            neonColor="magenta"
          />
        </div>
      )}

      {/* Buton Satıri */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-sm font-semibold text-gray-300">
          VPN Sunuculari ({servers.length})
        </h3>
        <div className="flex gap-2 flex-wrap">
          {hasMockServers && (
            <button
              onClick={handleClearMock}
              className="flex items-center gap-2 px-3 py-2 bg-gray-700/50 hover:bg-gray-700 border border-gray-600 text-gray-400 rounded-xl text-xs transition-all"
            >
              <Trash2 size={14} />
              Test Verilerini Temizle
            </button>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all"
          >
            <FileUp size={16} />
            .conf Yukle
          </button>
          <button
            onClick={openImportModal}
            className="flex items-center gap-2 px-4 py-2 bg-neon-magenta/10 hover:bg-neon-magenta/20 border border-neon-magenta/30 text-neon-magenta rounded-xl text-sm transition-all"
          >
            <Upload size={16} />
            Yapistir
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
          >
            <Plus size={16} />
            Manuel Ekle
          </button>
        </div>
      </div>

      {/* Sunucu Listesi */}
      {servers.length === 0 ? (
        <GlassCard>
          <div className="text-center py-12">
            <Globe size={48} className="mx-auto text-gray-600 mb-4" />
            <p className="text-gray-400 mb-2">
              Henüz VPN sunucusu eklenmemiş
            </p>
            <p className="text-xs text-gray-500 mb-6">
              Surfshark, NordVPN veya herhangi bir WireGuard .conf dosyasi
              yukleyerek başlayabilirsiniz.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all"
              >
                <FileUp size={16} />
                .conf Dosyasi Yukle
              </button>
              <button
                onClick={openCreateModal}
                className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
              >
                <Plus size={16} />
                Manuel Ekle
              </button>
            </div>
          </div>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers.map((server) => (
            <GlassCard
              key={server.id}
              neonColor={server.is_active ? "green" : undefined}
              className="relative"
            >
              {/* Aktif rözet */}
              <div className="absolute top-3 right-3">
                <NeonBadge
                  label={server.is_active ? "AKTIF" : "PASIF"}
                  variant={server.is_active ? "green" : "red"}
                  pulse={server.is_active}
                />
              </div>

              {/* Bayrak + Ülke + Ad */}
              <div className="flex items-start gap-3 mb-4 pr-20">
                <span className="text-3xl leading-none">
                  {countryCodeToFlag(server.country_code)}
                </span>
                <div className="min-w-0">
                  <h4 className="text-base font-semibold text-white truncate">
                    {server.name}
                  </h4>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {server.country} ({server.country_code})
                  </p>
                </div>
              </div>

              {/* Sunucu Detaylari */}
              <div className="space-y-1.5 mb-4 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Endpoint</span>
                  <span className="font-mono text-gray-300 truncate ml-2 max-w-[180px]">
                    {server.endpoint || "--"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Adres</span>
                  <span className="font-mono text-gray-300">
                    {server.interface_address || "--"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">DNS</span>
                  <span className="font-mono text-gray-300 truncate ml-2 max-w-[180px]">
                    {server.dns_servers || "--"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">AllowedIPs</span>
                  <span className="font-mono text-gray-300 truncate ml-2 max-w-[180px]">
                    {server.allowed_ips}
                  </span>
                </div>
              </div>

              {/* İşlem Butonlari */}
              <div className="flex items-center gap-2 pt-3 border-t border-glass-border">
                {server.is_active ? (
                  <button
                    onClick={() => handleDeactivate(server.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-neon-red/10 hover:bg-neon-red/20 border border-neon-red/30 text-neon-red rounded-lg text-xs transition-all"
                  >
                    <PowerOff size={13} />
                    Bağlantıyi Kes
                  </button>
                ) : (
                  <button
                    onClick={() => handleActivate(server.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-lg text-xs transition-all"
                  >
                    <Power size={13} />
                    Baglan
                  </button>
                )}

                <div className="flex-1" />

                <button
                  onClick={() => openEditModal(server)}
                  className="p-1.5 text-gray-500 hover:text-neon-cyan hover:bg-neon-cyan/10 rounded-lg transition-all"
                  title="Düzenle"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={() => handleDelete(server.id)}
                  className="p-1.5 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                  title="Sil"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </GlassCard>
          ))}
        </div>
      )}

      {/* Bilgi Kutusu */}
      <GlassCard>
        <div className="flex items-start gap-3">
          <AlertTriangle
            size={18}
            className="text-neon-amber mt-0.5 flex-shrink-0"
          />
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-1">
              Dış VPN İstemci Nasıl Çalışır?
            </h4>
            <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
              <li>
                Surfshark, NordVPN veya herhangi bir WireGuard saglayicisindan
                .conf dosyanizi edinin
              </li>
              <li>
                ".conf Yukle" veya "Yapistir" ile sisteme ekleyin
              </li>
              <li>
                "Baglan" butonuyla VPN tunelini aktive edin
              </li>
              <li>
                Pi gateway olarak calistiginda (eth0=WAN, eth1=LAN)
                tum ev agi trafiği VPN üzerinden yonlendirilir
              </li>
              <li>
                Ayni anda sadece bir VPN sunucusu aktif olabilir
              </li>
            </ul>
          </div>
        </div>
      </GlassCard>

      {/* ========== SUNUCU EKLEME / DUZENLEME MODAL ========== */}
      {serverModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={closeServerModal}
          />
          <div className="relative w-full max-w-2xl bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Server size={20} className="text-neon-cyan" />
                {editingServer
                  ? "Sunucu Düzenle"
                  : "Yeni VPN Sunucusu Ekle"}
              </h3>
              <button
                onClick={closeServerModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form */}
            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>
                    Sunucu Adi <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={serverForm.name}
                    onChange={(e) =>
                      setServerForm((p) => ({ ...p, name: e.target.value }))
                    }
                    placeholder="örn. Surfshark Hollanda"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>
                    Endpoint <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={serverForm.endpoint}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        endpoint: e.target.value,
                      }))
                    }
                    placeholder="örn. nl-ams.surfshark.com:51820"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Ülke</label>
                  <input
                    type="text"
                    value={serverForm.country}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        country: e.target.value,
                      }))
                    }
                    placeholder="örn. Hollanda"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Ülke Kodu (2 harf)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={serverForm.country_code}
                      onChange={(e) =>
                        setServerForm((p) => ({
                          ...p,
                          country_code: e.target.value
                            .toUpperCase()
                            .slice(0, 2),
                        }))
                      }
                      placeholder="NL"
                      maxLength={2}
                      className={inputClass}
                    />
                    <span className="text-2xl">
                      {countryCodeToFlag(serverForm.country_code)}
                    </span>
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className={labelClass}>
                    Public Key (Sunucu) <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={serverForm.public_key}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        public_key: e.target.value,
                      }))
                    }
                    placeholder="[Peer] altindaki PublicKey"
                    className={inputClass}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className={labelClass}>
                    Private Key (Sizin) <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="password"
                    value={serverForm.private_key}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        private_key: e.target.value,
                      }))
                    }
                    placeholder="[Interface] altindaki PrivateKey"
                    className={inputClass}
                  />
                  {editingServer && (
                    <p className="text-xs text-gray-500 mt-1">
                      Bos birakirsaniz mevcut key korunur
                    </p>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label className={labelClass}>
                    Preshared Key (Opsiyonel)
                  </label>
                  <input
                    type="password"
                    value={serverForm.preshared_key}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        preshared_key: e.target.value,
                      }))
                    }
                    placeholder="Varsa PresharedKey"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Interface Adresi</label>
                  <input
                    type="text"
                    value={serverForm.interface_address}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        interface_address: e.target.value,
                      }))
                    }
                    placeholder="örn. 10.14.0.2/16"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>Allowed IPs</label>
                  <input
                    type="text"
                    value={serverForm.allowed_ips}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        allowed_ips: e.target.value,
                      }))
                    }
                    placeholder="0.0.0.0/0, ::/0"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>DNS Sunuculari</label>
                  <input
                    type="text"
                    value={serverForm.dns_servers}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        dns_servers: e.target.value,
                      }))
                    }
                    placeholder="1.1.1.1, 8.8.8.8"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>MTU</label>
                  <input
                    type="number"
                    value={serverForm.mtu}
                    onChange={(e) =>
                      setServerForm((p) => ({ ...p, mtu: e.target.value }))
                    }
                    placeholder="1420"
                    min={1280}
                    max={1500}
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className={labelClass}>
                    Persistent Keepalive (sn)
                  </label>
                  <input
                    type="number"
                    value={serverForm.persistent_keepalive}
                    onChange={(e) =>
                      setServerForm((p) => ({
                        ...p,
                        persistent_keepalive: e.target.value,
                      }))
                    }
                    placeholder="25"
                    min={0}
                    max={300}
                    className={inputClass}
                  />
                </div>
              </div>
            </div>

            {/* Alt Butonlar */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closeServerModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handleServerSubmit}
                disabled={
                  submitting ||
                  !serverForm.name.trim() ||
                  !serverForm.endpoint.trim()
                }
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                ) : null}
                {editingServer ? "Güncelle" : "Sunucu Ekle"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== CONFIG IMPORT / YAPISTIR MODAL ========== */}
      {importModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={closeImportModal}
          />
          <div className="relative w-full max-w-xl bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Upload size={20} className="text-neon-magenta" />
                WireGuard Config Iceri Aktar
              </h3>
              <button
                onClick={closeImportModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <p className="text-xs text-gray-400">
                WireGuard .conf dosyasinin icerigini asagiya yapıştırin. Tum
                alanlar (PrivateKey, PublicKey, Endpoint, vb.) otomatik
                cikarilacaktir.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className={labelClass}>
                    Sunucu Adi <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={importForm.name}
                    onChange={(e) =>
                      setImportForm((p) => ({
                        ...p,
                        name: e.target.value,
                      }))
                    }
                    placeholder="örn. Surfshark NL-01"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Ülke</label>
                  <input
                    type="text"
                    value={importForm.country}
                    onChange={(e) =>
                      setImportForm((p) => ({
                        ...p,
                        country: e.target.value,
                      }))
                    }
                    placeholder="örn. Hollanda"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Ülke Kodu</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={importForm.country_code}
                      onChange={(e) =>
                        setImportForm((p) => ({
                          ...p,
                          country_code: e.target.value
                            .toUpperCase()
                            .slice(0, 2),
                        }))
                      }
                      placeholder="NL"
                      maxLength={2}
                      className={inputClass}
                    />
                    <span className="text-xl">
                      {countryCodeToFlag(importForm.country_code)}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <label className={labelClass}>
                  WireGuard Yapılandirma (.conf){" "}
                  <span className="text-neon-red">*</span>
                </label>
                <textarea
                  value={importForm.config_text}
                  onChange={(e) =>
                    setImportForm((p) => ({
                      ...p,
                      config_text: e.target.value,
                    }))
                  }
                  placeholder={`[Interface]\nPrivateKey = ...\nAddress = 10.14.0.2/16\nDNS = 162.252.172.57\n\n[Peer]\nPublicKey = ...\nAllowedIPs = 0.0.0.0/0\nEndpoint = nl-ams-wg-001.surfshark.com:51820`}
                  rows={12}
                  className="w-full bg-surface-800 border border-glass-border rounded-xl px-4 py-3 text-xs font-mono text-neon-green placeholder-gray-600 focus:outline-none focus:border-neon-magenta/50 resize-none transition-colors leading-relaxed"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closeImportModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handleImportSubmit}
                disabled={
                  importing ||
                  !importForm.name.trim() ||
                  !importForm.config_text.trim()
                }
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/20 rounded-xl hover:bg-neon-magenta/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-magenta rounded-full animate-spin" />
                ) : (
                  <Upload size={16} />
                )}
                Iceri Aktar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
