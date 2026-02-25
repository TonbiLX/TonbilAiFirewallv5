// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Saat & Tarih Ayarları sayfası: canlı saat, timezone değiştirme, NTP ayarları

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Clock,
  Globe,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Search,
  Radio,
  Wifi,
  WifiOff,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchTimeStatus,
  fetchTimezones,
  fetchNtpServers,
  setTimezone,
  setNtpServer,
  syncNow,
} from "../services/systemTimeApi";
import type { SystemTimeStatus } from "../types";

export function SystemTimePage() {
  const { connected } = useWebSocket();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<SystemTimeStatus | null>(null);
  const [timezones, setTimezones] = useState<Record<string, string[]>>({});
  const [ntpServers, setNtpServers] = useState<Array<{ id: string; name: string; address: string }>>([]);

  // Canlı saat
  const [liveTime, setLiveTime] = useState<Date>(new Date());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Form state'leri
  const [selectedTimezone, setSelectedTimezone] = useState("");
  const [timezoneSearch, setTimezoneSearch] = useState("");
  const [selectedNtpServer, setSelectedNtpServer] = useState("");
  const [customNtpServer, setCustomNtpServer] = useState("");

  // İşlem durumu
  const [tzSaving, setTzSaving] = useState(false);
  const [ntpSaving, setNtpSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // Canlı saat güncelleme
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setLiveTime(new Date());
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Ilk veri yükleme
  const loadData = useCallback(async () => {
    try {
      const [st, tz, ntp] = await Promise.all([
        fetchTimeStatus(),
        fetchTimezones(),
        fetchNtpServers(),
      ]);
      setStatus(st);
      setTimezones(tz);
      setNtpServers(ntp);
      if (st.timezone) setSelectedTimezone(st.timezone);
      if (st.ntp_server) {
        const predefined = ntp.find((s: { address: string }) => s.address === st.ntp_server);
        if (predefined) {
          setSelectedNtpServer(predefined.address);
        } else {
          setSelectedNtpServer("custom");
          setCustomNtpServer(st.ntp_server);
        }
      }
    } catch (err) {
      console.error("Saat bilgisi alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Timezone filtreleme
  const filteredTimezones = (() => {
    const result: Record<string, string[]> = {};
    const search = timezoneSearch.toLowerCase();
    for (const [region, tzList] of Object.entries(timezones)) {
      const filtered = tzList.filter((tz) => tz.toLowerCase().includes(search));
      if (filtered.length > 0) {
        result[region] = filtered;
      }
    }
    return result;
  })();

  // Tum timezone'lari duz liste olarak (select için)
  const allTimezonesList = Object.entries(filteredTimezones)
    .sort(([a], [b]) => a.localeCompare(b))
    .flatMap(([region, tzs]) => tzs.map((tz) => ({ region, tz })));

  const handleSetTimezone = async () => {
    if (!selectedTimezone) return;
    setTzSaving(true);
    try {
      await setTimezone(selectedTimezone);
      setFeedback({ type: "success", message: `Saat dilimi '${selectedTimezone}' olarak ayarlandi.` });
      await loadData();
    } catch (err) {
      console.error("Timezone ayarlanamadi:", err);
      setFeedback({ type: "error", message: "Saat dilimi ayarlanirken hata oluştu." });
    } finally {
      setTzSaving(false);
    }
  };

  const handleSetNtpServer = async () => {
    const server = selectedNtpServer === "custom" ? customNtpServer.trim() : selectedNtpServer;
    if (!server) return;
    setNtpSaving(true);
    try {
      await setNtpServer(server);
      setFeedback({ type: "success", message: `NTP sunucusu '${server}' olarak ayarlandi.` });
      await loadData();
    } catch (err) {
      console.error("NTP sunucusu ayarlanamadi:", err);
      setFeedback({ type: "error", message: "NTP sunucusu ayarlanirken hata oluştu." });
    } finally {
      setNtpSaving(false);
    }
  };

  const handleSyncNow = async () => {
    setSyncing(true);
    try {
      await syncNow();
      setFeedback({ type: "success", message: "NTP senkronizasyonu tamamlandi." });
      await loadData();
    } catch (err) {
      console.error("NTP senkronizasyonu başarısız:", err);
      setFeedback({ type: "error", message: "NTP senkronizasyonu sırasında hata oluştu." });
    } finally {
      setSyncing(false);
    }
  };

  // Zamani timezone'a göre goster
  const formatLiveTime = () => {
    try {
      return liveTime.toLocaleString("tr-TR", {
        timeZone: status?.timezone || "UTC",
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return liveTime.toLocaleString("tr-TR");
    }
  };

  const formatLiveTimeBig = () => {
    try {
      return liveTime.toLocaleTimeString("tr-TR", {
        timeZone: status?.timezone || "UTC",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return liveTime.toLocaleTimeString("tr-TR");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar title="Saat & Tarih Ayarları" connected={connected} />

      {/* Geri bildirim mesaji */}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sol kolon: Sistem Zamani */}
        <GlassCard>
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Clock size={24} className="text-neon-cyan" />
              <h3 className="text-lg font-semibold">Sistem Zamani</h3>
            </div>

            {/* Canlı saat */}
            <div className="text-center py-6">
              <p className="text-5xl font-bold neon-text font-mono tracking-wider">
                {formatLiveTimeBig()}
              </p>
              <p className="text-gray-400 mt-3 text-sm">
                {formatLiveTime()}
              </p>
            </div>

            {/* Durum bilgileri */}
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-glass-border/50">
                <span className="text-sm text-gray-400">Saat Dilimi</span>
                <NeonBadge label={status?.timezone || "UTC"} variant="cyan" />
              </div>
              <div className="flex items-center justify-between py-2 border-b border-glass-border/50">
                <span className="text-sm text-gray-400">UTC Offset</span>
                <span className="text-sm text-white font-mono">{status?.utc_offset || "--"}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-glass-border/50">
                <span className="text-sm text-gray-400">NTP Durumu</span>
                <div className="flex items-center gap-2">
                  {status?.ntp_synced ? (
                    <>
                      <Wifi size={14} className="text-neon-green" />
                      <NeonBadge label="SENKRON" variant="green" />
                    </>
                  ) : status?.ntp_enabled ? (
                    <>
                      <RefreshCw size={14} className="text-neon-amber animate-spin" />
                      <NeonBadge label="BEKLENIYOR" variant="amber" />
                    </>
                  ) : (
                    <>
                      <WifiOff size={14} className="text-neon-red" />
                      <NeonBadge label="DEVRE DISI" variant="red" />
                    </>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-400">NTP Sunucusu</span>
                <span className="text-sm text-white font-mono">{status?.ntp_server || "--"}</span>
              </div>
            </div>

            {/* Senkronize Et butonu */}
            <button
              onClick={handleSyncNow}
              disabled={syncing}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
            >
              <RefreshCw size={18} className={syncing ? "animate-spin" : ""} />
              {syncing ? "Senkronize Ediliyor..." : "Simdi Senkronize Et"}
            </button>
          </div>
        </GlassCard>

        {/* Sag kolon: Ayarlar */}
        <div className="space-y-6">
          {/* Saat Dilimi */}
          <GlassCard>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Globe size={24} className="text-neon-cyan" />
                <h3 className="text-lg font-semibold">Saat Dilimi</h3>
              </div>

              {/* Aranabilir timezone secici */}
              <div>
                <div className="relative mb-2">
                  <Search
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="text"
                    value={timezoneSearch}
                    onChange={(e) => setTimezoneSearch(e.target.value)}
                    placeholder="Saat dilimi ara... (örn. Istanbul, UTC)"
                    className="w-full pl-10 pr-4 bg-surface-800 border border-glass-border rounded-xl py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                  />
                </div>

                <select
                  value={selectedTimezone}
                  onChange={(e) => setSelectedTimezone(e.target.value)}
                  size={6}
                  className="w-full bg-surface-800 border border-glass-border rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  {allTimezonesList.map(({ region, tz }) => (
                    <option
                      key={tz}
                      value={tz}
                      className={tz === status?.timezone ? "text-neon-cyan font-bold" : ""}
                    >
                      {tz === status?.timezone ? `* ${tz}` : tz}
                    </option>
                  ))}
                </select>

                {selectedTimezone && selectedTimezone !== status?.timezone && (
                  <p className="text-xs text-neon-cyan mt-2">
                    Secilen: {selectedTimezone}
                  </p>
                )}
              </div>

              <button
                onClick={handleSetTimezone}
                disabled={tzSaving || !selectedTimezone || selectedTimezone === status?.timezone}
                className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                {tzSaving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Ayarlaniyor...
                  </>
                ) : (
                  <>
                    <Globe size={16} />
                    Değiştir
                  </>
                )}
              </button>
            </div>
          </GlassCard>

          {/* NTP Sunucusu */}
          <GlassCard>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Radio size={24} className="text-neon-cyan" />
                <h3 className="text-lg font-semibold">NTP Sunucusu</h3>
              </div>

              {/* Onceden tanimli sunucular */}
              <div className="space-y-2">
                {ntpServers.map((server) => (
                  <label
                    key={server.id}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all ${
                      selectedNtpServer === server.address
                        ? "bg-neon-cyan/10 border-neon-cyan/20 text-neon-cyan"
                        : "border-glass-border text-gray-400 hover:text-white hover:bg-glass-light"
                    }`}
                  >
                    <input
                      type="radio"
                      name="ntp-server"
                      value={server.address}
                      checked={selectedNtpServer === server.address}
                      onChange={(e) => setSelectedNtpServer(e.target.value)}
                      className="accent-cyan-400"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{server.name}</p>
                      <p className="text-xs font-mono opacity-70">{server.address}</p>
                    </div>
                    {status?.ntp_server === server.address && (
                      <NeonBadge label="AKTIF" variant="green" />
                    )}
                  </label>
                ))}

                {/* Özel NTP sunucusu */}
                <label
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all ${
                    selectedNtpServer === "custom"
                      ? "bg-neon-cyan/10 border-neon-cyan/20 text-neon-cyan"
                      : "border-glass-border text-gray-400 hover:text-white hover:bg-glass-light"
                  }`}
                >
                  <input
                    type="radio"
                    name="ntp-server"
                    value="custom"
                    checked={selectedNtpServer === "custom"}
                    onChange={() => setSelectedNtpServer("custom")}
                    className="accent-cyan-400"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Özel Sunucu</p>
                    {selectedNtpServer === "custom" && (
                      <input
                        type="text"
                        value={customNtpServer}
                        onChange={(e) => setCustomNtpServer(e.target.value)}
                        placeholder="ntp.example.com"
                        className="mt-2 w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                      />
                    )}
                  </div>
                </label>
              </div>

              <button
                onClick={handleSetNtpServer}
                disabled={
                  ntpSaving ||
                  (!selectedNtpServer) ||
                  (selectedNtpServer === "custom" && !customNtpServer.trim())
                }
                className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                {ntpSaving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Kaydediliyor...
                  </>
                ) : (
                  <>
                    <Radio size={16} />
                    Kaydet
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
