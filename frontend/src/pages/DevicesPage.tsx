// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihazlar sayfası: tab filtre, siralama, online sure, bağlantı gecmisi,
// profil atama, hostname düzenleme, bant genisligi

import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Monitor,
  Wifi,
  WifiOff,
  Ban,
  Pencil,
  Check,
  X,
  Search,
  Users,
  Gauge,
  CheckCircle,
  AlertTriangle,
  ShieldBan,
  ShieldAlert,
  Pin,
  Clock,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  History,
  Smartphone,
  Tv,
  Laptop,
  Cpu,
  Gamepad2,
  Glasses,
  Router,
  RefreshCw,
  Loader2,
  ShieldX,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchDevices,
  updateDevice,
  blockDevice,
  unblockDevice,
  fetchDeviceConnectionHistory,
  setDeviceBandwidthLimit,
  scanDevices,
  fetchExternalDnsConnections,
} from "../services/deviceApi";
import { fetchProfiles } from "../services/profileApi";
import { createStaticLease } from "../services/dhcpApi";
import type { Device, Profile, DeviceConnectionLog } from "../types";

// --- Cihaz tipi ikonu ---
function getDeviceIcon(device: Device) {
  const t = device.device_type;
  if (t === "phone") return Smartphone;
  if (t === "tv") return Tv;
  if (t === "computer") return Laptop;
  if (t === "console") return Gamepad2;
  if (t === "vr_headset") return Glasses;
  if (t === "iot") return Cpu;
  if (t === "network_device") return Router;
  return Monitor;
}

// --- Risk renkleri ---
function getRiskColor(level: string) {
  if (level === "dangerous") return "text-red-400";
  if (level === "suspicious") return "text-amber-400";
  return "";
}

// --- Profil tip renkleri ---
const profileTypeVariant: Record<string, "amber" | "cyan" | "magenta"> = {
  child: "amber",
  adult: "cyan",
  guest: "magenta",
};

const profileTypeLabel: Record<string, string> = {
  child: "Çocuk",
  adult: "Yetişkin",
  guest: "Misafir",
};

// --- Online sure formatlama ---
function formatOnlineTime(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return "0dk";
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}g`);
  if (hours > 0) parts.push(`${hours}s`);
  if (minutes > 0 || parts.length === 0) parts.push(`${minutes}dk`);
  return parts.join(" ");
}

function formatActiveSession(lastOnlineStart: string | null): string {
  if (!lastOnlineStart) return "";
  const start = new Date(lastOnlineStart).getTime();
  const now = Date.now();
  const diffSec = Math.floor((now - start) / 1000);
  if (diffSec < 60) return "< 1dk";
  return formatOnlineTime(diffSec);
}

// --- Siralama secenekleri ---
const sortOptions = [
  { value: "last_seen", label: "Son Görülen" },
  { value: "hostname", label: "Hostname" },
  { value: "ip_address", label: "IP Adresi" },
  { value: "first_seen", label: "İlk Görülme" },
  { value: "is_online", label: "Durum" },
];

export function DevicesPage() {
  const { connected } = useWebSocket();
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  // Tab filtre
  const [activeTab, setActiveTab] = useState<"all" | "online" | "offline">("all");

  // Siralama
  const [sortBy, setSortBy] = useState("last_seen");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Arama
  const [searchQuery, setSearchQuery] = useState("");

  // Bağlantı gecmisi
  const [expandedDeviceId, setExpandedDeviceId] = useState<number | null>(null);
  const [connectionHistory, setConnectionHistory] = useState<DeviceConnectionLog[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Satır ici düzenleme durumlari
  const [editingHostnameId, setEditingHostnameId] = useState<number | null>(null);
  const [editHostnameValue, setEditHostnameValue] = useState("");
  const [editingBandwidthId, setEditingBandwidthId] = useState<number | null>(null);
  const [editBandwidthValue, setEditBandwidthValue] = useState("");

  // Ag taramasi
  const [scanning, setScanning] = useState(false);

  // Dis Baglantilar
  const [extConnOpen, setExtConnOpen] = useState(false);
  const [extConnections, setExtConnections] = useState<any[]>([]);
  const [extConnLoading, setExtConnLoading] = useState(false);

  const loadExternalConnections = useCallback(async () => {
    setExtConnLoading(true);
    try {
      const res = await fetchExternalDnsConnections(1);
      setExtConnections(res.data.connections || []);
    } catch {
      setExtConnections([]);
    } finally {
      setExtConnLoading(false);
    }
  }, []);

  const toggleExtConn = () => {
    const next = !extConnOpen;
    setExtConnOpen(next);
    if (next && extConnections.length === 0) loadExternalConnections();
  };

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // --- Veri yükleme ---
  const loadData = useCallback(async () => {
    try {
      const status = activeTab === "all" ? undefined : activeTab;
      const [deviceRes, profileRes] = await Promise.all([
        fetchDevices({ sort_by: sortBy, sort_order: sortOrder, status }),
        fetchProfiles(),
      ]);
      setDevices(deviceRes.data);
      setProfiles(profileRes.data);
    } catch (err) {
      console.error("Cihaz/profil verisi alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  // --- Ag taramasi ---
  const handleScanDevices = async () => {
    setScanning(true);
    try {
      const res = await scanDevices();
      setFeedback({
        type: "success",
        message: `Ag taramasi tamamlandi: ${res.data.online} online, ${res.data.offline} offline, ${res.data.total} toplam`,
      });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Ag taramasi basarisiz oldu." });
    } finally {
      setScanning(false);
    }
  };

  // --- Geri bildirim zamanlayici ---
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // --- Bağlantı gecmisi ---
  const toggleHistory = async (deviceId: number) => {
    if (expandedDeviceId === deviceId) {
      setExpandedDeviceId(null);
      setConnectionHistory([]);
      return;
    }
    setExpandedDeviceId(deviceId);
    setHistoryLoading(true);
    try {
      const res = await fetchDeviceConnectionHistory(deviceId, 10);
      setConnectionHistory(res.data);
    } catch (err) {
      console.error("Bağlantı gecmisi alinamadi:", err);
      setConnectionHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  // --- Profil ad donusturme ---
  const getProfileName = (profileId: number | null): string | null => {
    if (!profileId) return null;
    const profile = profiles.find((p) => p.id === profileId);
    return profile ? profile.name : null;
  };

  const getProfileType = (profileId: number | null): string | null => {
    if (!profileId) return null;
    const profile = profiles.find((p) => p.id === profileId);
    return profile ? profile.profile_type : null;
  };

  // --- Engelle / Engel Kaldir ---
  const handleBlock = async (id: number) => {
    try {
      await blockDevice(id);
      setFeedback({ type: "success", message: "Cihaz engellendi." });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Cihaz engellenirken hata oluştu." });
    }
  };

  const handleUnblock = async (id: number) => {
    try {
      await unblockDevice(id);
      setFeedback({ type: "success", message: "Cihaz engeli kaldırıldı." });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Engel kaldırılırken hata oluştu." });
    }
  };

  // --- IP Sabitle ---
  const handlePinIp = async (device: Device) => {
    if (!device.mac_address || !device.ip_address) return;
    try {
      await createStaticLease({
        mac_address: device.mac_address,
        ip_address: device.ip_address,
        hostname: device.hostname || undefined,
      });
      setFeedback({
        type: "success",
        message: `${device.ip_address} adresi ${device.hostname || device.mac_address} için sabitlendi.`,
      });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "IP sabitlenirken hata oluştu." });
    }
  };

  // --- Profil atama ---
  const handleProfileAssign = async (deviceId: number, profileId: number | null) => {
    try {
      await updateDevice(deviceId, { profile_id: profileId });
      setFeedback({ type: "success", message: "Profil ataması güncellendi." });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Profil atanırken hata oluştu." });
    }
  };

  // --- Hostname düzenleme ---
  const startEditHostname = (device: Device) => {
    setEditingHostnameId(device.id);
    setEditHostnameValue(device.hostname || "");
  };

  const cancelEditHostname = () => {
    setEditingHostnameId(null);
    setEditHostnameValue("");
  };

  const saveHostname = async (deviceId: number) => {
    try {
      await updateDevice(deviceId, { hostname: editHostnameValue.trim() || null });
      setEditingHostnameId(null);
      setEditHostnameValue("");
      setFeedback({ type: "success", message: "Hostname güncellendi." });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Hostname güncellenirken hata oluştu." });
    }
  };

  // --- Bant genişliği düzenleme ---
  const startEditBandwidth = (device: Device) => {
    setEditingBandwidthId(device.id);
    setEditBandwidthValue(device.bandwidth_limit_mbps?.toString() || "");
  };

  const cancelEditBandwidth = () => {
    setEditingBandwidthId(null);
    setEditBandwidthValue("");
  };

  const saveBandwidth = async (deviceId: number) => {
    try {
      const val = editBandwidthValue.trim();
      const limitMbps = val ? parseInt(val, 10) : null;

      if (val && (isNaN(limitMbps!) || limitMbps! < 0)) {
        setFeedback({ type: "error", message: "Geçerli bir Mbps değeri girin (bos = limitsiz)." });
        return;
      }

      await setDeviceBandwidthLimit(deviceId, limitMbps && limitMbps > 0 ? limitMbps : null);
      setEditingBandwidthId(null);
      setEditBandwidthValue("");
      setFeedback({
        type: "success",
        message: limitMbps && limitMbps > 0
          ? `Bant genişliği ${limitMbps} Mbps olarak sınırlandırıldı.`
          : "Bant genişliği sınırı kaldırıldı.",
      });
      await loadData();
    } catch (err) {
      setFeedback({ type: "error", message: "Bant genişliği güncellenirken hata oluştu." });
    }
  };

  // --- Arama filtresi (client-side) ---
  const filteredDevices = devices.filter((device) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      (device.hostname || "").toLowerCase().includes(query) ||
      (device.ip_address || "").toLowerCase().includes(query) ||
      (device.mac_address || "").toLowerCase().includes(query) ||
      (device.manufacturer || "").toLowerCase().includes(query)
    );
  });

  // Sayimlar
  const onlineCount = devices.filter((d) => d.is_online).length;
  const offlineCount = devices.filter((d) => !d.is_online).length;

  // --- Loading ekrani ---
  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar
        title="Cihazlar"
        connected={connected}
        actions={
          <button
            onClick={handleScanDevices}
            disabled={scanning}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
              scanning
                ? "bg-neon-cyan/10 text-neon-cyan/60 border-neon-cyan/20 cursor-wait"
                : "bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30 hover:bg-neon-cyan/20 hover:shadow-[0_0_15px_rgba(0,240,255,0.15)]"
            }`}
          >
            {scanning ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <RefreshCw size={16} />
            )}
            {scanning ? "Taraniyor..." : "Cihazlari Tara"}
          </button>
        }
      />

      {/* Tab bar + Arama + Siralama */}
      <div className="flex flex-col gap-4">
        {/* Tab butonlari */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === "all"
                ? "bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30"
                : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10"
            }`}
          >
            Tümü ({devices.length})
          </button>
          <button
            onClick={() => setActiveTab("online")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === "online"
                ? "bg-neon-green/20 text-neon-green border border-neon-green/30"
                : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10"
            }`}
          >
            Çevrimiçi ({onlineCount})
          </button>
          <button
            onClick={() => setActiveTab("offline")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === "offline"
                ? "bg-neon-red/20 text-neon-red border border-neon-red/30"
                : "bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10"
            }`}
          >
            Çevrimdışı ({offlineCount})
          </button>
        </div>

        {/* Arama + Siralama */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative w-full sm:w-72">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Hostname, IP, MAC ile ara..."
              className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 backdrop-blur-xl"
            />
          </div>

          {/* Siralama */}
          <div className="flex items-center gap-2">
            <ArrowUpDown size={14} className="text-gray-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-surface-800 border border-white/10 rounded-lg px-2 py-2 text-xs text-white focus:outline-none focus:border-neon-cyan/50"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
              className="p-2 bg-white/5 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              title={sortOrder === "asc" ? "Artan" : "Azalan"}
            >
              {sortOrder === "asc" ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
        </div>
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

      {/* Cihaz listesi */}
      {filteredDevices.length === 0 ? (
        <GlassCard>
          <p className="text-gray-500 text-center py-8">
            {searchQuery
              ? "Aramanızla eşleşen cihaz bulunamadı."
              : "Kayıtlı cihaz bulunamadı."}
          </p>
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {filteredDevices.map((device) => {
            const profileName = getProfileName(device.profile_id);
            const profileType = getProfileType(device.profile_id);
            const isEditingHostname = editingHostnameId === device.id;
            const isEditingBandwidth = editingBandwidthId === device.id;
            const isExpanded = expandedDeviceId === device.id;

            return (
              <GlassCard key={device.id} hoverable>
                <div className="flex flex-col">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                    {/* Sol: Cihaz bilgileri */}
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="flex-shrink-0 relative">
                        {React.createElement(getDeviceIcon(device), {
                          size: 32,
                          className: device.is_online ? "text-neon-green" : "text-gray-600",
                        })}
                        {device.risk_level === "dangerous" && (
                          <ShieldAlert size={14} className="absolute -top-1 -right-1 text-red-400" />
                        )}
                        {device.risk_level === "suspicious" && (
                          <AlertTriangle size={14} className="absolute -top-1 -right-1 text-amber-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        {/* Hostname satiri */}
                        {isEditingHostname ? (
                          <div className="flex items-center gap-2 mb-1">
                            <input
                              type="text"
                              value={editHostnameValue}
                              onChange={(e) => setEditHostnameValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveHostname(device.id);
                                if (e.key === "Escape") cancelEditHostname();
                              }}
                              className="bg-surface-800 border border-neon-cyan/30 rounded-lg px-2 py-1 text-sm text-white focus:outline-none focus:border-neon-cyan/50 w-48"
                              autoFocus
                            />
                            <button
                              onClick={() => saveHostname(device.id)}
                              className="p-1 text-neon-green hover:bg-neon-green/10 rounded transition-colors"
                            >
                              <Check size={14} />
                            </button>
                            <button
                              onClick={cancelEditHostname}
                              className="p-1 text-gray-400 hover:bg-white/10 rounded transition-colors"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 mb-1">
                            <p
                              className="font-semibold truncate cursor-pointer hover:text-neon-cyan transition-colors"
                              onClick={() => navigate(`/devices/${device.id}`)}
                              title="Detay sayfasına git"
                            >
                              {device.hostname || "Bilinmeyen Cihaz"}
                            </p>
                            {device.is_iptv && (
                              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 shrink-0">
                                <Tv size={10} />
                                IPTV
                              </span>
                            )}
                            <button
                              onClick={() => startEditHostname(device)}
                              className="p-1 text-gray-500 hover:text-neon-cyan transition-colors"
                              title="Hostname düzenle"
                            >
                              <Pencil size={12} />
                            </button>
                          </div>
                        )}
                        <p className="text-xs text-gray-400">
                          {device.ip_address} | {device.mac_address}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <p className="text-xs text-gray-500">
                            {device.manufacturer}
                            {device.detected_os && <span className="text-neon-cyan/60"> · {device.detected_os}</span>}
                          </p>
                          {/* Online sure */}
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <Clock size={10} />
                            <span>
                              Toplam: {formatOnlineTime(device.total_online_seconds || 0)}
                            </span>
                            {device.is_online && device.last_online_start && (
                              <span className="text-neon-green">
                                (aktif: {formatActiveSession(device.last_online_start)})
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Orta: Profil atama + bant genisligi */}
                    <div className="flex flex-wrap items-center gap-3 lg:gap-4">
                      {/* Profil rözeti ve dropdown */}
                      <div className="flex items-center gap-2">
                        <Users size={14} className="text-gray-500" />
                        <select
                          value={device.profile_id?.toString() || ""}
                          onChange={(e) =>
                            handleProfileAssign(
                              device.id,
                              e.target.value ? parseInt(e.target.value) : null
                            )
                          }
                          className="bg-surface-800 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-neon-cyan/50 min-w-[120px]"
                        >
                          <option value="">Profil Yok</option>
                          {profiles.map((p) => (
                            <option key={p.id} value={p.id.toString()}>
                              {p.name} ({profileTypeLabel[p.profile_type]})
                            </option>
                          ))}
                        </select>
                        {profileName && profileType && (
                          <NeonBadge
                            label={profileName}
                            variant={profileTypeVariant[profileType] || "cyan"}
                          />
                        )}
                      </div>

                      {/* Bant genişliği */}
                      <div className="flex items-center gap-2">
                        <Gauge size={14} className="text-gray-500" />
                        {isEditingBandwidth ? (
                          <div className="flex items-center gap-1">
                            <input
                              type="number"
                              min="0"
                              step="0.5"
                              value={editBandwidthValue}
                              onChange={(e) => setEditBandwidthValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveBandwidth(device.id);
                                if (e.key === "Escape") cancelEditBandwidth();
                              }}
                              className="bg-surface-800 border border-neon-cyan/30 rounded-lg px-2 py-1 text-xs text-white focus:outline-none w-20"
                              placeholder="Mbps"
                              autoFocus
                            />
                            <button
                              onClick={() => saveBandwidth(device.id)}
                              className="p-1 text-neon-green hover:bg-neon-green/10 rounded transition-colors"
                            >
                              <Check size={12} />
                            </button>
                            <button
                              onClick={cancelEditBandwidth}
                              className="p-1 text-gray-400 hover:bg-white/10 rounded transition-colors"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => startEditBandwidth(device)}
                            className="text-xs text-gray-400 hover:text-neon-cyan transition-colors flex items-center gap-1"
                            title="Bant genişliği limiti"
                          >
                            {device.bandwidth_limit_mbps
                              ? `${device.bandwidth_limit_mbps} Mbps`
                              : "Limitsiz"}
                            <Pencil size={10} />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Sag: Durum + Butonlar */}
                    <div className="flex items-center gap-2">
                      {device.is_online ? (
                        <NeonBadge label="Çevrimiçi" variant="green" pulse />
                      ) : (
                        <NeonBadge label="Çevrimdışı" variant="red" />
                      )}
                      {/* Bağlantı gecmisi */}
                      <button
                        onClick={() => toggleHistory(device.id)}
                        className={`p-2 rounded-lg transition-all border ${
                          isExpanded
                            ? "bg-neon-cyan/10 text-neon-cyan border-neon-cyan/20"
                            : "bg-white/5 text-gray-400 border-white/10 hover:text-neon-cyan hover:bg-neon-cyan/10"
                        }`}
                        title="Bağlantı Geçmişi"
                      >
                        <History size={16} />
                      </button>
                      {device.ip_address && (
                        device.mac_address &&
                        !device.mac_address.startsWith("AA:00:") &&
                        !device.mac_address.startsWith("DD:0T:") ? (
                          <button
                            onClick={() => handlePinIp(device)}
                            className="p-2 rounded-lg bg-neon-amber/5 text-gray-400 hover:text-neon-amber hover:bg-neon-amber/10 transition-all border border-white/10 hover:border-neon-amber/20"
                            title="IP Sabitle (Statik Kiralama)"
                          >
                            <Pin size={16} />
                          </button>
                        ) : (
                          <button
                            onClick={() =>
                              setFeedback({
                                type: "error",
                                message: `${device.hostname || device.ip_address} cihazinin MAC adresi henüz tespit edilemedi. DHCP ile IP aldiginda buton aktif olacak.`,
                              })
                            }
                            className="p-2 rounded-lg bg-white/5 text-gray-600 transition-all border border-white/5 cursor-not-allowed opacity-50"
                            title="MAC adresi bekleniyor - DHCP ile IP aldiginda aktif olacak"
                          >
                            <Pin size={16} />
                          </button>
                        )
                      )}
                      <button
                        onClick={() => navigate(`/devices/${device.id}/services`)}
                        className="p-2 rounded-lg bg-neon-cyan/5 text-gray-400 hover:text-neon-cyan hover:bg-neon-cyan/10 transition-all border border-white/10 hover:border-neon-cyan/20"
                        title="Servis Engelleme"
                      >
                        <ShieldBan size={16} />
                      </button>
                      {device.is_blocked ? (
                        <button
                          onClick={() => handleUnblock(device.id)}
                          className="p-2 rounded-lg bg-neon-red/10 text-neon-red hover:bg-neon-red/20 transition-all border border-neon-red/20"
                          title="Engeli kaldir"
                        >
                          <Ban size={16} />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleBlock(device.id)}
                          className="p-2 rounded-lg bg-white/5 text-gray-400 hover:text-neon-red hover:bg-neon-red/10 hover:border-neon-red/20 transition-all border border-white/10"
                          title="Engelle"
                        >
                          <Ban size={16} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Bağlantı gecmisi genisleyen bolum */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                        <History size={14} />
                        Bağlantı Geçmişi (Son 10)
                      </h4>
                      {historyLoading ? (
                        <div className="flex items-center justify-center py-4">
                          <div className="w-5 h-5 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
                        </div>
                      ) : connectionHistory.length === 0 ? (
                        <p className="text-xs text-gray-500 py-2">
                          Henüz bağlantı geçmişi bulunmuyor.
                        </p>
                      ) : (
                        <div className="space-y-1.5">
                          {connectionHistory.map((log) => (
                            <div
                              key={log.id}
                              className="flex items-center gap-3 text-xs px-3 py-2 bg-white/[0.03] rounded-lg"
                            >
                              {log.event_type === "connect" ? (
                                <Wifi size={12} className="text-neon-green flex-shrink-0" />
                              ) : (
                                <WifiOff size={12} className="text-neon-red flex-shrink-0" />
                              )}
                              <span
                                className={`font-medium ${
                                  log.event_type === "connect"
                                    ? "text-neon-green"
                                    : "text-neon-red"
                                }`}
                              >
                                {log.event_type === "connect" ? "Bağlandı" : "Ayrıldı"}
                              </span>
                              {log.ip_address && (
                                <span className="text-gray-500">{log.ip_address}</span>
                              )}
                              {log.session_duration_seconds != null && (
                                <span className="text-gray-400">
                                  Oturum: {formatOnlineTime(log.session_duration_seconds)}
                                </span>
                              )}
                              <span className="text-gray-600 ml-auto">
                                {log.timestamp
                                  ? new Date(log.timestamp).toLocaleString("tr-TR")
                                  : ""}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}

      {/* Dis Baglantilar Paneli */}
      <div className="mt-6">
        <GlassCard>
          <div
            className="flex items-center justify-between cursor-pointer select-none"
            onClick={toggleExtConn}
          >
            <div className="flex items-center gap-2">
              <ShieldX className="w-5 h-5 text-amber-400" />
              <span className="text-amber-400 font-bold text-sm">Dış Bağlantılar</span>
              <span className="text-xs text-gray-400">(DoT / DoH / DNS Bypass)</span>
              {extConnections.length > 0 && (
                <span className="bg-red-500/20 text-red-400 text-xs font-bold px-2 py-0.5 rounded-full">
                  {extConnections.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {extConnOpen && (
                <button
                  onClick={(e) => { e.stopPropagation(); loadExternalConnections(); }}
                  className="text-cyan-400 hover:text-cyan-300 p-1"
                  title="Yenile"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              )}
              {extConnOpen ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
            </div>
          </div>

          {extConnOpen && (
            <div className="mt-4">
              {extConnLoading ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                </div>
              ) : extConnections.length === 0 ? (
                <p className="text-gray-500 text-sm">Son 1 saatte DoT/DoH/Bypass bağlantısı tespit edilmedi.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-400 text-xs border-b border-white/10">
                        <th className="text-left pb-2">Tespit Türü</th>
                        <th className="text-left pb-2">Cihaz</th>
                        <th className="text-left pb-2">MAC Adresi</th>
                        <th className="text-left pb-2">Cihaz Tipi</th>
                        <th className="text-left pb-2">Hedef IP</th>
                        <th className="text-left pb-2">Port</th>
                        <th className="text-left pb-2">Son Görülme</th>
                      </tr>
                    </thead>
                    <tbody>
                      {extConnections.map((conn: any, i: number) => {
                        const typeColors: Record<string, string> = {
                          dot: "text-purple-400 bg-purple-400/10 border-purple-400/30",
                          doh: "text-amber-400 bg-amber-400/10 border-amber-400/30",
                          dns_bypass: "text-red-400 bg-red-400/10 border-red-400/30",
                        };
                        const typeLabels: Record<string, string> = {
                          dot: "DoT", doh: "DoH", dns_bypass: "DNS Bypass",
                        };
                        const cls = typeColors[conn.detection_type] || "text-gray-400";
                        return (
                          <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                            <td className="py-2">
                              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${cls}`}>
                                {typeLabels[conn.detection_type] || conn.detection_type}
                              </span>
                            </td>
                            <td className="py-2 text-white">{conn.hostname || conn.device_ip || "-"}</td>
                            <td className="py-2 text-gray-400 font-mono text-xs">{conn.mac_address || "-"}</td>
                            <td className="py-2 text-gray-400">{conn.os_type || "-"}</td>
                            <td className="py-2 text-cyan-400 font-mono text-xs">{conn.dst_ip}</td>
                            <td className="py-2 text-gray-400">{conn.dst_port}</td>
                            <td className="py-2 text-gray-500 text-xs">
                              {conn.last_seen ? new Date(conn.last_seen).toLocaleString("tr-TR") : "-"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
