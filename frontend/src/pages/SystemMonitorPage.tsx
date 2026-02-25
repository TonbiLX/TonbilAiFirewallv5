// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Sistem Monitörü sayfası: RPi5 donanım metrikleri, canlı grafikler, fan kontrolü
// Uyarlanabilir widget grid sistemi ile (react-grid-layout)

import { useState, useEffect, useCallback, ReactNode } from "react";
import {
  Cpu, Thermometer, HardDrive, MemoryStick, Fan, Network,
  Server, Clock, Activity, Gauge, CheckCircle, AlertTriangle,
} from "lucide-react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { WidgetWrapper } from "../components/dashboard/WidgetWrapper";
import { DashboardGrid } from "../components/dashboard/DashboardGrid";
import { WidgetToggleMenu } from "../components/dashboard/WidgetToggleMenu";
import { useWebSocket } from "../hooks/useWebSocket";
import { useSystemMonitorLayout } from "../hooks/useSystemMonitorLayout";
import { SYSMON_WIDGET_REGISTRY } from "../config/systemMonitorWidgetRegistry";
import {
  fetchHardwareInfo,
  fetchMetrics,
  fetchFanConfig,
  updateFanConfig,
} from "../services/systemMonitorApi";
import type {
  SystemHardwareInfo,
  SystemMetricsResponse,
  SystemMetricsHistoryPoint,
  FanConfig,
} from "../types";

const POLL_MS = 5000;
const NEON_CYAN = "#00F0FF";
const NEON_MAGENTA = "#FF00E5";
const NEON_GREEN = "#39FF14";
const NEON_AMBER = "#FFB800";

const TIP_STYLE = {
  backgroundColor: "rgba(18, 18, 26, 0.95)",
  border: "1px solid rgba(0, 240, 255, 0.3)",
  borderRadius: "12px",
  color: "#fff",
};

export function SystemMonitorPage() {
  const { connected } = useWebSocket();
  const [loading, setLoading] = useState(true);
  const [hwInfo, setHwInfo] = useState<SystemHardwareInfo | null>(null);
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null);
  const [fanCfg, setFanCfg] = useState<FanConfig | null>(null);
  const [history, setHistory] = useState<SystemMetricsHistoryPoint[]>([]);

  // Fan kontrol state
  const [slider, setSlider] = useState(128);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  // Grid layout
  const {
    layouts, visibleWidgets, onLayoutChange, onBreakpointChange,
    toggleWidget, resetLayout,
  } = useSystemMonitorLayout();

  // Feedback temizle
  useEffect(() => {
    if (feedback) {
      const t = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(t);
    }
  }, [feedback]);

  // Uptime formatla
  const fmtUptime = (s: number) => {
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (d > 0) return `${d}g ${h}s ${m}dk`;
    if (h > 0) return `${h}s ${m}dk`;
    return `${m}dk`;
  };

  // Chart X ekseni
  const fmtTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch { return ""; }
  };

  // Statik bilgi (bir kez)
  useEffect(() => {
    fetchHardwareInfo().then(setHwInfo).catch(() => {});
    fetchFanConfig().then((c) => { setFanCfg(c); setSlider(c.manual_pwm); }).catch(() => {});
  }, []);

  // Polling
  const poll = useCallback(async () => {
    try {
      const data = await fetchMetrics();
      setMetrics(data);
      setHistory(data.history);
    } catch { /* */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => clearInterval(iv);
  }, [poll]);

  // Fan mod değiştir
  const toggleFanMode = async () => {
    if (!fanCfg) return;
    setSaving(true);
    try {
      const newMode = fanCfg.mode === "auto" ? "manual" : "auto";
      const u = await updateFanConfig({ mode: newMode });
      setFanCfg(u);
      setSlider(u.manual_pwm);
      setFeedback({ type: "ok", msg: `Fan: ${newMode === "auto" ? "Otomatik" : "Manuel"}` });
    } catch { setFeedback({ type: "err", msg: "Fan modu değiştirilemedi." }); }
    finally { setSaving(false); }
  };

  // Fan PWM uygula
  const applyPwm = async () => {
    setSaving(true);
    try {
      const u = await updateFanConfig({ mode: "manual", manual_pwm: slider });
      setFanCfg(u);
      setFeedback({ type: "ok", msg: `Fan: ${Math.round(slider / 255 * 100)}% (PWM ${slider})` });
    } catch { setFeedback({ type: "err", msg: "Fan hizi ayarlanamadi." }); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingSpinner />;

  const cur = metrics?.current;
  const cpuU = cur?.cpu?.usage_percent ?? 0;
  const cpuT = cur?.cpu?.temperature_c ?? 0;
  const cpuF = cur?.cpu?.frequency_mhz ?? 0;
  const memP = cur?.memory?.usage_percent ?? 0;
  const diskP = cur?.disk?.usage_percent ?? 0;
  const fanRpm = cur?.fan?.rpm ?? 0;
  const uptime = cur?.uptime_seconds ?? 0;
  const netTotal = (cur?.network?.reduce((s, n) => s + n.rx_rate_kbps + n.tx_rate_kbps, 0) ?? 0);

  const tempColor: "cyan" | "green" | "amber" = cpuT >= 70 ? "amber" : cpuT >= 55 ? "amber" : "green";

  const chartData = history.map((p) => ({ ...p, time: fmtTime(p.timestamp) }));

  // --- Widget render fonksiyonları ---

  const renderHwInfo = () => (
    <WidgetWrapper title="Donanım Bilgileri" icon={<Server size={14} />} neonColor="cyan">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { l: "Model", v: hwInfo?.model ?? "..." },
          { l: "CPU", v: `${hwInfo?.cpu_model ?? "?"} (${hwInfo?.cpu_cores ?? 0} cekirdek)` },
          { l: "Maks Frekans", v: `${hwInfo?.cpu_max_freq_mhz?.toFixed(0) ?? 0} MHz` },
          { l: "Toplam RAM", v: `${((hwInfo?.ram_total_mb ?? 0) / 1024).toFixed(1)} GB` },
          { l: "Toplam Disk", v: `${hwInfo?.disk_total_gb?.toFixed(1) ?? 0} GB` },
          { l: "Isletim Sistemi", v: hwInfo?.os_info ?? "?" },
        ].map((item) => (
          <div key={item.l}>
            <p className="text-xs text-gray-500 uppercase tracking-wider">{item.l}</p>
            <p className="text-sm font-medium mt-1 truncate" title={item.v}>{item.v}</p>
          </div>
        ))}
      </div>
    </WidgetWrapper>
  );

  const renderUptime = () => (
    <WidgetWrapper title="Sistem Süresi" icon={<Clock size={14} />} neonColor="green">
      <p className="text-4xl font-bold neon-text-green text-center py-4">
        {fmtUptime(uptime)}
      </p>
      <p className="text-center text-sm text-gray-400">
        Anlik Frekans: <span className="text-white font-mono">{cpuF.toFixed(0)} MHz</span>
      </p>
    </WidgetWrapper>
  );

  const renderStatCards = () => (
    <WidgetWrapper title="İstatistik Kartları" icon={<Cpu size={14} />}>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 h-full">
        <StatCard title="CPU Kullanım" value={`%${cpuU.toFixed(1)}`} icon={<Cpu size={28} />} neonColor="cyan" />
        <StatCard title="Sıcaklık" value={`${cpuT.toFixed(1)}°C`} icon={<Thermometer size={28} />} neonColor={tempColor} />
        <div className="glass-card hoverable border border-glass-border rounded-2xl p-4" style={{ borderColor: "rgba(255, 0, 229, 0.15)" }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 uppercase tracking-wider">RAM</p>
              <p className="text-3xl font-bold mt-1 neon-text">%{memP.toFixed(1)}</p>
              <p className="text-xs text-gray-500 mt-1 font-mono">
                {(cur?.memory?.used_mb ?? 0).toFixed(0)} / {(cur?.memory?.total_mb ?? 0).toFixed(0)} MB
              </p>
            </div>
            <div className="text-neon-cyan opacity-70"><MemoryStick size={28} /></div>
          </div>
        </div>
        <StatCard title="Disk" value={`%${diskP.toFixed(1)}`} icon={<HardDrive size={28} />} neonColor="amber" />
        <StatCard title="Fan" value={`${fanRpm} RPM`} icon={<Fan size={28} />} neonColor="green" />
        <StatCard title="Ag I/O" value={`${(netTotal / 1000).toFixed(1)} Mbps`} icon={<Network size={28} />} neonColor="cyan" />
      </div>
    </WidgetWrapper>
  );

  const renderCpuChart = () => (
    <WidgetWrapper title="CPU Kullanım Geçmişi (son 5 dk)" icon={<Activity size={14} />} neonColor="cyan">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#555" fontSize={10} />
          <YAxis stroke="#555" fontSize={10} domain={[0, 100]} unit="%" />
          <Tooltip contentStyle={TIP_STYLE} />
          <defs>
            <linearGradient id="cpuG" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={NEON_CYAN} stopOpacity={0.3} />
              <stop offset="95%" stopColor={NEON_CYAN} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="cpu_usage" stroke={NEON_CYAN}
            strokeWidth={2} fill="url(#cpuG)" dot={false} name="CPU %" />
        </AreaChart>
      </ResponsiveContainer>
    </WidgetWrapper>
  );

  const renderTempChart = () => (
    <WidgetWrapper title="CPU Sıcaklık Geçmişi" icon={<Thermometer size={14} />} neonColor="amber">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#555" fontSize={10} />
          <YAxis stroke="#555" fontSize={10} domain={[30, 85]} unit="°C" />
          <Tooltip contentStyle={TIP_STYLE} />
          <defs>
            <linearGradient id="tempG" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={NEON_AMBER} stopOpacity={0.3} />
              <stop offset="95%" stopColor={NEON_AMBER} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="cpu_temp" stroke={NEON_AMBER}
            strokeWidth={2} fill="url(#tempG)" dot={false} name="Sıcaklık °C" />
        </AreaChart>
      </ResponsiveContainer>
    </WidgetWrapper>
  );

  const renderNetChart = () => (
    <WidgetWrapper title="Ağ Veri Akışı" icon={<Network size={14} />} neonColor="cyan">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#555" fontSize={10} />
          <YAxis stroke="#555" fontSize={10} unit=" kbps" />
          <Tooltip contentStyle={TIP_STYLE} />
          <Line type="monotone" dataKey="net_rx_kbps" stroke={NEON_CYAN}
            strokeWidth={2} dot={false} name="Indirme (RX)" />
          <Line type="monotone" dataKey="net_tx_kbps" stroke={NEON_MAGENTA}
            strokeWidth={2} dot={false} name="Yukleme (TX)" />
        </LineChart>
      </ResponsiveContainer>
    </WidgetWrapper>
  );

  const renderMemoryDetail = () => (
    <WidgetWrapper title="Bellek (RAM)" icon={<MemoryStick size={14} />} neonColor="magenta">
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Kullanilan</span>
          <span className="font-bold">{cur?.memory?.used_mb?.toFixed(0) ?? 0} MB</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Toplam</span>
          <span className="font-bold">{cur?.memory?.total_mb?.toFixed(0) ?? 0} MB</span>
        </div>
        <div className="w-full h-3 bg-dark-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${memP}%`,
              background: `linear-gradient(90deg, #FF00E580, #FF00E5)`,
              boxShadow: `0 0 10px #FF00E560`,
            }} />
        </div>
        <p className="text-xs text-center text-gray-400">{memP.toFixed(1)}%</p>
      </div>
    </WidgetWrapper>
  );

  const renderDiskDetail = () => (
    <WidgetWrapper title="Disk" icon={<HardDrive size={14} />} neonColor="amber">
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Kullanilan</span>
          <span className="font-bold">{cur?.disk?.used_gb?.toFixed(1) ?? 0} GB</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Toplam</span>
          <span className="font-bold">{cur?.disk?.total_gb?.toFixed(1) ?? 0} GB</span>
        </div>
        <div className="w-full h-3 bg-dark-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${diskP}%`,
              background: `linear-gradient(90deg, #FFB80080, #FFB800)`,
              boxShadow: `0 0 10px #FFB80060`,
            }} />
        </div>
        <p className="text-xs text-center text-gray-400">{diskP.toFixed(1)}%</p>
      </div>
    </WidgetWrapper>
  );

  const renderFanControl = () => (
    <WidgetWrapper title="Fan Kontrolü" icon={<Fan size={14} />} neonColor="green">
      <div className="flex items-center justify-between mb-3">
        <NeonBadge
          label={fanCfg?.mode === "auto" ? "OTOMATIK" : "MANUEL"}
          variant={fanCfg?.mode === "auto" ? "green" : "amber"}
        />
      </div>

      {/* RPM */}
      <div className="text-center py-2">
        <p className="text-3xl font-bold neon-text-green">{fanRpm}</p>
        <p className="text-xs text-gray-400">RPM</p>
      </div>

      {/* Mod toggle */}
      <button
        onClick={toggleFanMode}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl
                 border border-glass-border text-sm hover:bg-glass-light transition-all mb-3
                 disabled:opacity-50"
      >
        <Gauge size={16} className={fanCfg?.mode === "auto" ? "text-neon-green" : "text-gray-400"} />
        {fanCfg?.mode === "auto" ? "Otomatik Mod Aktif" : "Manuel Mod Aktif"}
      </button>

      {/* Manuel slider */}
      {fanCfg?.mode === "manual" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">PWM</span>
            <span className="font-mono text-white">{slider} / 255 ({Math.round(slider / 255 * 100)}%)</span>
          </div>
          <input
            type="range" min={0} max={255} value={slider}
            onChange={(e) => setSlider(Number(e.target.value))}
            className="w-full h-2 bg-dark-800 rounded-full accent-[#39FF14] cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-gray-500">
            <span>KAPALI</span><span>DUSUK</span><span>ORTA</span><span>YUKSEK</span><span>MAKS</span>
          </div>
          <button
            onClick={applyPwm}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                     bg-neon-green/10 text-neon-green border border-neon-green/20
                     rounded-xl text-sm font-medium hover:bg-neon-green/20
                     transition-all disabled:opacity-50"
          >
            <Gauge size={16} />
            {saving ? "Ayarlaniyor..." : "Uygula"}
          </button>
        </div>
      )}

      {/* Otomatik mod esikleri */}
      {fanCfg?.mode === "auto" && (
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">Dusuk Esik</span>
            <span className="font-mono">{fanCfg.auto_temp_low}°C (Fan OFF)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Orta Esik</span>
            <span className="font-mono">{fanCfg.auto_temp_mid}°C (%50)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Yuksek Esik</span>
            <span className="font-mono">{fanCfg.auto_temp_high}°C (%100)</span>
          </div>
        </div>
      )}
    </WidgetWrapper>
  );

  const renderNetInterfaces = () => (
    <WidgetWrapper title="Ağ Arayüzleri" icon={<Network size={14} />} neonColor="cyan">
      {cur?.network && cur.network.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {cur.network.map((iface) => (
            <div key={iface.interface}
              className="bg-dark-800/50 rounded-xl p-4 border border-glass-border">
              <p className="font-mono text-sm font-bold text-neon-cyan mb-2">{iface.interface}</p>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">RX Hizi</span>
                  <span className="text-neon-green font-mono">{iface.rx_rate_kbps.toFixed(1)} kbps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">TX Hizi</span>
                  <span className="text-neon-magenta font-mono">{iface.tx_rate_kbps.toFixed(1)} kbps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Toplam RX</span>
                  <span className="font-mono">{(iface.rx_bytes / 1024 / 1024).toFixed(1)} MB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Toplam TX</span>
                  <span className="font-mono">{(iface.tx_bytes / 1024 / 1024).toFixed(1)} MB</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-sm text-center py-4">Ağ arayüzü bulunamadı</p>
      )}
    </WidgetWrapper>
  );

  // Widget renderers map
  const widgetRenderers: Record<string, ReactNode> = {
    "hw-info": renderHwInfo(),
    "uptime": renderUptime(),
    "stat-cards": renderStatCards(),
    "cpu-chart": renderCpuChart(),
    "temp-chart": renderTempChart(),
    "net-chart": renderNetChart(),
    "memory-detail": renderMemoryDetail(),
    "disk-detail": renderDiskDetail(),
    "fan-control": renderFanControl(),
    "net-interfaces": renderNetInterfaces(),
  };

  return (
    <div>
      <TopBar
        title="Sistem Monitörü"
        connected={connected}
        actions={
          <WidgetToggleMenu
            visibleWidgets={visibleWidgets}
            onToggle={toggleWidget}
            onReset={resetLayout}
            widgetRegistry={SYSMON_WIDGET_REGISTRY}
          />
        }
      />

      {/* Feedback */}
      {feedback && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
          feedback.type === "ok"
            ? "bg-neon-green/10 text-neon-green border-neon-green/20"
            : "bg-neon-red/10 text-neon-red border-neon-red/20"
        }`}>
          {feedback.type === "ok" ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          {feedback.msg}
        </div>
      )}

      <DashboardGrid
        layouts={layouts}
        visibleWidgets={visibleWidgets}
        onLayoutChange={onLayoutChange}
        onBreakpointChange={onBreakpointChange}
        widgetRenderers={widgetRenderers}
        widgetRegistry={SYSMON_WIDGET_REGISTRY}
      />
    </div>
  );
}
