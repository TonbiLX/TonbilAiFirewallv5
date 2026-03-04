// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// WiFi AP yonetim sayfasi: durum, konfigürasyon, istemciler, misafir agi,
// zamanlama, MAC filtresi — cyberpunk glassmorphism tema

import { useState, useEffect, useCallback } from "react";
import {
  Wifi,
  WifiOff,
  Radio,
  Users,
  Signal,
  Power,
  PowerOff,
  Save,
  Eye,
  EyeOff,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Shield,
  Plus,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchWifiStatus,
  fetchWifiConfig,
  fetchWifiClients,
  fetchWifiChannels,
  enableWifi,
  disableWifi,
  updateWifiConfig,
  updateGuestConfig,
  updateSchedule,
  updateMacFilter,
} from "../services/wifiApi";
import type { WifiStatus, WifiConfig, WifiClient } from "../types";

type TabKey = "main" | "guest" | "schedule" | "mac";

function signalColor(dbm: number): string {
  if (dbm >= -50) return "text-neon-green";
  if (dbm >= -70) return "text-neon-amber";
  return "text-neon-red";
}

function signalLabel(dbm: number): string {
  if (dbm >= -50) return "Mukemmel";
  if (dbm >= -60) return "Iyi";
  if (dbm >= -70) return "Orta";
  return "Zayif";
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}sn`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}dk`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return m > 0 ? `${h}sa ${m}dk` : `${h}sa`;
}

export function WifiPage() {
  const { connected } = useWebSocket();
  const [status, setStatus] = useState<WifiStatus | null>(null);
  const [config, setConfig] = useState<WifiConfig | null>(null);
  const [clients, setClients] = useState<WifiClient[]>([]);
  const [channels, setChannels] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("main");
  const [actionLoading, setActionLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showGuestPassword, setShowGuestPassword] = useState(false);

  // Feedback banner
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Form state (ana ag)
  const [formSsid, setFormSsid] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formChannel, setFormChannel] = useState(6);
  const [formBand, setFormBand] = useState("2.4GHz");
  const [formTxPower, setFormTxPower] = useState(20);
  const [formHidden, setFormHidden] = useState(false);

  // Form state (misafir)
  const [guestEnabled, setGuestEnabled] = useState(false);
  const [guestSsid, setGuestSsid] = useState("");
  const [guestPassword, setGuestPassword] = useState("");

  // Form state (zamanlama)
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [scheduleStart, setScheduleStart] = useState("08:00");
  const [scheduleStop, setScheduleStop] = useState("23:00");

  // Form state (MAC filtre)
  const [macMode, setMacMode] = useState("disabled");
  const [macList, setMacList] = useState<string[]>([]);
  const [newMac, setNewMac] = useState("");

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  const loadData = useCallback(async () => {
    try {
      const [statusRes, configRes, clientsRes, channelsRes] = await Promise.all([
        fetchWifiStatus(),
        fetchWifiConfig(),
        fetchWifiClients(),
        fetchWifiChannels(),
      ]);
      setStatus(statusRes.data);
      setConfig(configRes.data);
      setClients(clientsRes.data);
      setChannels(channelsRes.data);

      // Form state'i config'den doldur
      const c = configRes.data as WifiConfig;
      setFormSsid(c.ssid || "");
      setFormPassword(c.password || "");
      setFormChannel(c.channel || 6);
      setFormBand(c.band || "2.4GHz");
      setFormTxPower(c.tx_power || 20);
      setFormHidden(c.hidden_ssid || false);
      setGuestEnabled(c.guest_enabled || false);
      setGuestSsid(c.guest_ssid || "");
      setGuestPassword(c.guest_password || "");
      setScheduleEnabled(c.schedule_enabled || false);
      setScheduleStart(c.schedule_start || "08:00");
      setScheduleStop(c.schedule_stop || "23:00");
      setMacMode(c.mac_filter_mode || "disabled");
      setMacList(c.mac_filter_list || []);

      setError(null);
    } catch (err) {
      setError("WiFi verileri yuklenemedi");
      console.error("WiFi veri yukleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  // --- Anahtar islemler ---

  const handleToggle = async () => {
    setActionLoading(true);
    try {
      if (status?.enabled) {
        await disableWifi();
        setFeedback({ type: "success", message: "WiFi AP durduruldu." });
      } else {
        await enableWifi();
        setFeedback({ type: "success", message: "WiFi AP baslatildi." });
      }
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Islem basarisiz.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveMain = async () => {
    setActionLoading(true);
    try {
      await updateWifiConfig({
        ssid: formSsid,
        password: formPassword || null,
        channel: formChannel,
        band: formBand,
        tx_power: formTxPower,
        hidden_ssid: formHidden,
      });
      setFeedback({ type: "success", message: "WiFi ayarlari kaydedildi." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Ayarlar kaydedilemedi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveGuest = async () => {
    setActionLoading(true);
    try {
      await updateGuestConfig({
        guest_enabled: guestEnabled,
        guest_ssid: guestSsid || null,
        guest_password: guestPassword || null,
      });
      setFeedback({ type: "success", message: "Misafir agi ayarlari kaydedildi." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Misafir ayarlari kaydedilemedi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    setActionLoading(true);
    try {
      await updateSchedule({
        schedule_enabled: scheduleEnabled,
        schedule_start: scheduleStart,
        schedule_stop: scheduleStop,
      });
      setFeedback({ type: "success", message: "Zamanlama ayarlari kaydedildi." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Zamanlama kaydedilemedi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveMacFilter = async () => {
    setActionLoading(true);
    try {
      await updateMacFilter({
        mac_filter_mode: macMode,
        mac_filter_list: macList,
      });
      setFeedback({ type: "success", message: "MAC filtre ayarlari kaydedildi." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "MAC filtre kaydedilemedi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddMac = () => {
    const mac = newMac.trim().toUpperCase();
    if (mac && /^([0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(mac) && !macList.includes(mac)) {
      setMacList([...macList, mac]);
      setNewMac("");
    }
  };

  const handleRemoveMac = (mac: string) => {
    setMacList(macList.filter((m) => m !== mac));
  };

  // Kanal listesi (seçilen banda göre)
  const availableChannels = formBand === "5GHz"
    ? channels["5GHz"] || [36, 40, 44, 48]
    : channels["2.4GHz"] || [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

  if (loading) return <LoadingSpinner />;

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: "main", label: "Ana Ag", icon: <Wifi size={14} /> },
    { key: "guest", label: "Misafir Agi", icon: <UserPlus size={14} /> },
    { key: "schedule", label: "Zamanlama", icon: <Clock size={14} /> },
    { key: "mac", label: "MAC Filtre", icon: <Shield size={14} /> },
  ];

  return (
    <div className="space-y-6">
      <TopBar title="WiFi Erisim Noktasi" connected={connected} />

      {/* Hata */}
      {error && (
        <div className="bg-neon-red/10 border border-neon-red/30 rounded-xl p-4 text-neon-red text-sm">
          {error}
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          {feedback.message}
        </div>
      )}

      {/* Durum Karti */}
      <GlassCard neonColor={status?.enabled ? "green" : undefined}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Radio size={20} className="text-neon-cyan" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              WiFi Erisim Noktasi Durumu
            </h3>
          </div>
          <button
            onClick={loadData}
            className="p-2 text-gray-400 hover:text-white hover:bg-glass-light rounded-lg transition-all"
            title="Yenile"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="p-3 bg-surface-800 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">Durum</p>
            <div className="flex items-center gap-2">
              {status?.enabled ? (
                <>
                  <Wifi size={14} className="text-neon-green" />
                  <span className="text-sm font-medium text-neon-green">Aktif</span>
                </>
              ) : (
                <>
                  <WifiOff size={14} className="text-gray-500" />
                  <span className="text-sm font-medium text-gray-500">Pasif</span>
                </>
              )}
            </div>
          </div>

          <div className="p-3 bg-surface-800 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">SSID</p>
            <p className="text-sm font-mono text-white truncate">
              {status?.ssid || config?.ssid || "-"}
            </p>
          </div>

          <div className="p-3 bg-surface-800 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">Kanal / Band</p>
            <p className="text-sm font-mono text-neon-cyan">
              {status?.channel || config?.channel || "-"}{" "}
              <span className="text-gray-500">
                ({status?.band || config?.band || "2.4GHz"})
              </span>
            </p>
          </div>

          <div className="p-3 bg-surface-800 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">Bagli Istemci</p>
            <p className="text-sm font-medium text-white">{status?.clients_count || 0}</p>
          </div>
        </div>

        {/* Aç/Kapat */}
        <div className="pt-4 border-t border-glass-border flex items-center gap-3">
          {status?.enabled ? (
            <button
              onClick={handleToggle}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-red/10 hover:bg-neon-red/20 border border-neon-red/30 text-neon-red rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-red rounded-full animate-spin" />
              ) : (
                <PowerOff size={16} />
              )}
              WiFi Kapat
            </button>
          ) : (
            <button
              onClick={handleToggle}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-green rounded-full animate-spin" />
              ) : (
                <Power size={16} />
              )}
              WiFi Ac
            </button>
          )}
          <span className="text-xs text-gray-500">
            {status?.enabled
              ? `hostapd calisiyor (${WIFI_INTERFACE})`
              : "hostapd durduruldu"}
          </span>
        </div>
      </GlassCard>

      {/* Istatistik Kartlari */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Istemciler"
          value={status?.clients_count || 0}
          icon={<Users size={32} />}
          neonColor="cyan"
        />
        <StatCard
          title="Kanal"
          value={status?.channel || config?.channel || "-"}
          icon={<Radio size={32} />}
          neonColor="magenta"
        />
        <StatCard
          title="TX Gucu"
          value={`${status?.tx_power || config?.tx_power || 20} dBm`}
          icon={<Signal size={32} />}
          neonColor="amber"
        />
        <StatCard
          title="Band"
          value={status?.band || config?.band || "2.4GHz"}
          icon={<Wifi size={32} />}
          neonColor="green"
        />
      </div>

      {/* Tab Sistemi */}
      <div className="flex gap-1 p-1 bg-surface-900 rounded-xl border border-glass-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm transition-all flex-1 justify-center ${
              activeTab === tab.key
                ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                : "text-gray-400 hover:text-white hover:bg-glass-light"
            }`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* === TAB: Ana Ag === */}
      {activeTab === "main" && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
            Ana Ag Ayarlari
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* SSID */}
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                SSID (Ag Adi)
              </label>
              <input
                type="text"
                value={formSsid}
                onChange={(e) => setFormSsid(e.target.value)}
                maxLength={32}
                className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
              />
            </div>

            {/* Sifre */}
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Sifre (WPA2)
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={formPassword}
                  onChange={(e) => setFormPassword(e.target.value)}
                  placeholder="8-63 karakter (bos = acik ag)"
                  maxLength={63}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 pr-10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-white"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Band */}
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Frekans Bandi
              </label>
              <select
                value={formBand}
                onChange={(e) => {
                  setFormBand(e.target.value);
                  // Band degisince kanal sifirla
                  setFormChannel(e.target.value === "5GHz" ? 36 : 6);
                }}
                className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
              >
                <option value="2.4GHz">2.4 GHz</option>
                <option value="5GHz">5 GHz</option>
              </select>
            </div>

            {/* Kanal */}
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Kanal
              </label>
              <select
                value={formChannel}
                onChange={(e) => setFormChannel(Number(e.target.value))}
                className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
              >
                {availableChannels.map((ch) => (
                  <option key={ch} value={ch}>
                    Kanal {ch}
                  </option>
                ))}
              </select>
            </div>

            {/* TX Gucu */}
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Yayin Gucu: {formTxPower} dBm
              </label>
              <input
                type="range"
                min={1}
                max={31}
                value={formTxPower}
                onChange={(e) => setFormTxPower(Number(e.target.value))}
                className="w-full accent-neon-cyan"
              />
              <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                <span>1 dBm (Dusuk)</span>
                <span>15 dBm</span>
                <span>31 dBm (Yuksek)</span>
              </div>
            </div>

            {/* Gizli SSID */}
            <div className="md:col-span-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formHidden}
                  onChange={(e) => setFormHidden(e.target.checked)}
                  className="w-4 h-4 rounded border-glass-border bg-surface-800 accent-neon-cyan"
                />
                <span className="text-sm text-gray-300">Gizli SSID (yayin yapma)</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end mt-4 pt-4 border-t border-glass-border">
            <button
              onClick={handleSaveMain}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Kaydet
            </button>
          </div>
        </GlassCard>
      )}

      {/* === TAB: Misafir Agi === */}
      {activeTab === "guest" && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
            Misafir Agi Ayarlari
          </h3>

          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={guestEnabled}
                onChange={(e) => setGuestEnabled(e.target.checked)}
                className="w-4 h-4 rounded border-glass-border bg-surface-800 accent-neon-cyan"
              />
              <span className="text-sm text-gray-300">Misafir agini etkinlestir</span>
            </label>

            {guestEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                    Misafir SSID
                  </label>
                  <input
                    type="text"
                    value={guestSsid}
                    onChange={(e) => setGuestSsid(e.target.value)}
                    maxLength={32}
                    className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                    Misafir Sifresi
                  </label>
                  <div className="relative">
                    <input
                      type={showGuestPassword ? "text" : "password"}
                      value={guestPassword}
                      onChange={(e) => setGuestPassword(e.target.value)}
                      placeholder="8-63 karakter (bos = acik ag)"
                      maxLength={63}
                      className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 pr-10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowGuestPassword(!showGuestPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-white"
                    >
                      {showGuestPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end mt-4 pt-4 border-t border-glass-border">
            <button
              onClick={handleSaveGuest}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Kaydet
            </button>
          </div>
        </GlassCard>
      )}

      {/* === TAB: Zamanlama === */}
      {activeTab === "schedule" && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
            Zamanlama Ayarlari
          </h3>

          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={scheduleEnabled}
                onChange={(e) => setScheduleEnabled(e.target.checked)}
                className="w-4 h-4 rounded border-glass-border bg-surface-800 accent-neon-cyan"
              />
              <span className="text-sm text-gray-300">Zamanlamayi etkinlestir</span>
            </label>

            {scheduleEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                    Baslangic Saati
                  </label>
                  <input
                    type="time"
                    value={scheduleStart}
                    onChange={(e) => setScheduleStart(e.target.value)}
                    className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                    Bitis Saati
                  </label>
                  <input
                    type="time"
                    value={scheduleStop}
                    onChange={(e) => setScheduleStop(e.target.value)}
                    className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
                  />
                </div>
                <div className="md:col-span-2 text-xs text-gray-500">
                  WiFi AP belirtilen saatler arasinda otomatik acilir, disinda kapanir.
                  Gece araligi icin baslangici bitisten buyuk yapin (orn: 22:00 - 08:00).
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end mt-4 pt-4 border-t border-glass-border">
            <button
              onClick={handleSaveSchedule}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Kaydet
            </button>
          </div>
        </GlassCard>
      )}

      {/* === TAB: MAC Filtre === */}
      {activeTab === "mac" && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
            MAC Filtre Ayarlari
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Filtre Modu
              </label>
              <select
                value={macMode}
                onChange={(e) => setMacMode(e.target.value)}
                className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
              >
                <option value="disabled">Devre Disi</option>
                <option value="whitelist">Beyaz Liste (sadece izinliler baglansın)</option>
                <option value="blacklist">Siyah Liste (engellenenler baglanmasin)</option>
              </select>
            </div>

            {macMode !== "disabled" && (
              <>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMac}
                    onChange={(e) => setNewMac(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddMac()}
                    placeholder="AA:BB:CC:DD:EE:FF"
                    maxLength={17}
                    className="flex-1 bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                  />
                  <button
                    onClick={handleAddMac}
                    className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
                  >
                    <Plus size={14} />
                    Ekle
                  </button>
                </div>

                {macList.length > 0 && (
                  <div className="space-y-1">
                    {macList.map((mac) => (
                      <div
                        key={mac}
                        className="flex items-center justify-between px-3 py-2 bg-surface-800 rounded-lg"
                      >
                        <span className="text-sm font-mono text-gray-300">{mac}</span>
                        <button
                          onClick={() => handleRemoveMac(mac)}
                          className="p-1 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {macList.length === 0 && (
                  <p className="text-xs text-gray-500 text-center py-4">
                    Henuz MAC adresi eklenmedi
                  </p>
                )}
              </>
            )}
          </div>

          <div className="flex justify-end mt-4 pt-4 border-t border-glass-border">
            <button
              onClick={handleSaveMacFilter}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {actionLoading ? (
                <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Kaydet
            </button>
          </div>
        </GlassCard>
      )}

      {/* Bagli Istemciler */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Bagli Istemciler ({clients.length})
          </h3>
          <button
            onClick={loadData}
            className="p-2 text-gray-400 hover:text-white hover:bg-glass-light rounded-lg transition-all"
            title="Yenile"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {clients.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            {status?.enabled
              ? "WiFi AP aktif ancak henuz bagli istemci yok"
              : "WiFi AP kapali — istemci baglantisi icin AP'yi baslatin"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-glass-border">
                  <th className="pb-3 pr-4">Cihaz</th>
                  <th className="pb-3 pr-4">IP</th>
                  <th className="pb-3 pr-4">Sinyal</th>
                  <th className="pb-3 pr-4">Hiz</th>
                  <th className="pb-3">Bagli Sure</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((client) => (
                  <tr
                    key={client.mac_address}
                    className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                  >
                    <td className="py-3 pr-4">
                      <div>
                        <span className="font-medium text-white text-sm">
                          {client.hostname || "Bilinmeyen Cihaz"}
                        </span>
                        <p className="text-xs text-gray-500 font-mono">{client.mac_address}</p>
                      </div>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-gray-300">
                      {client.ip_address || "-"}
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <Signal size={14} className={signalColor(client.signal_dbm)} />
                        <div>
                          <span className={`text-xs font-medium ${signalColor(client.signal_dbm)}`}>
                            {client.signal_dbm} dBm
                          </span>
                          <p className="text-[10px] text-gray-500">
                            {signalLabel(client.signal_dbm)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-xs text-gray-300">
                      <div>
                        <span className="text-cyan-400">{"\u2191"} {client.tx_bitrate_mbps} Mbps</span>
                        <br />
                        <span className="text-pink-400">{"\u2193"} {client.rx_bitrate_mbps} Mbps</span>
                      </div>
                    </td>
                    <td className="py-3 text-xs text-gray-400">
                      {formatDuration(client.connected_seconds)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

const WIFI_INTERFACE = "wlan0";
