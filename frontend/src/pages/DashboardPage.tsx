// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dinamik Dashboard: react-grid-layout ile sürükle-bırak, boyutlandır, gizle/göster

import { useEffect, useState, useMemo, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  Wifi, ShieldBan, Shield, Search, Globe, Ban, Users,
  Upload, Download, Activity, ArrowUpDown, ArrowUp, ArrowDown,
} from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { TopBar } from "../components/layout/TopBar";
import { useWebSocket } from "../hooks/useWebSocket";
import { useDashboard } from "../hooks/useDashboard";
import { useDashboardLayout } from "../hooks/useDashboardLayout";
import { DashboardGrid } from "../components/dashboard/DashboardGrid";
import { WidgetWrapper } from "../components/dashboard/WidgetWrapper";
import { WidgetToggleMenu } from "../components/dashboard/WidgetToggleMenu";

interface BwPoint {
  time: string;
  up: number;
  down: number;
}

type SortCol = "hostname" | "upload" | "download" | "total";
type SortDir = "asc" | "desc";

function formatBps(bps: number): string {
  if (bps === 0) return "0";
  if (bps < 1000) return bps + " bps";
  if (bps < 1000000) return (bps / 1000).toFixed(1) + " Kbps";
  if (bps < 1000000000) return (bps / 1000000).toFixed(1) + " Mbps";
  return (bps / 1000000000).toFixed(2) + " Gbps";
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function DashboardPage() {
  const { data: wsData, connected } = useWebSocket();
  const { summary } = useDashboard();
  const navigate = useNavigate();
  const [bwHistory, setBwHistory] = useState<BwPoint[]>([]);
  const [sortCol, setSortCol] = useState<SortCol>("total");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const {
    layouts, visibleWidgets, onLayoutChange, onBreakpointChange,
    toggleWidget, resetLayout,
  } = useDashboardLayout();

  useEffect(() => {
    if (wsData?.bandwidth) {
      const now = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setBwHistory((prev) => [
        ...prev.slice(-29),
        { time: now, up: wsData.bandwidth.total_upload_bps, down: wsData.bandwidth.total_download_bps },
      ]);
    }
  }, [wsData]);

  const totalQueries = wsData?.dns?.total_queries_24h ?? summary?.dns?.total_queries_24h ?? 0;
  const blockedQueries = wsData?.dns?.blocked_queries_24h ?? summary?.dns?.blocked_queries_24h ?? 0;
  const blockPct = wsData?.dns?.block_percentage ?? summary?.dns?.block_percentage ?? 0;
  const queriesPerMin = wsData?.dns?.queries_per_min ?? 0;
  const uploadBps = wsData?.bandwidth?.total_upload_bps ?? 0;
  const downloadBps = wsData?.bandwidth?.total_download_bps ?? 0;

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir(col === "hostname" ? "asc" : "desc");
    }
  };

  const SortIcon = ({ col }: { col: SortCol }) => {
    if (sortCol !== col) return <ArrowUpDown size={10} className="opacity-30" />;
    return sortDir === "asc" ? (
      <ArrowUp size={10} className="text-neon-cyan" />
    ) : (
      <ArrowDown size={10} className="text-neon-cyan" />
    );
  };

  const sortedDevices = useMemo(() => {
    if (!wsData?.devices) return [];
    const onlineDevices = wsData.devices.filter((d: any) => d.is_online);
    return [...onlineDevices].sort((a: any, b: any) => {
      const bwA = wsData.bandwidth?.devices?.[String(a.id)];
      const bwB = wsData.bandwidth?.devices?.[String(b.id)];
      let cmp = 0;
      switch (sortCol) {
        case "hostname":
          cmp = (a.hostname || "").localeCompare(b.hostname || "", "tr");
          break;
        case "upload":
          cmp = (bwA?.upload_bps ?? 0) - (bwB?.upload_bps ?? 0);
          break;
        case "download":
          cmp = (bwA?.download_bps ?? 0) - (bwB?.download_bps ?? 0);
          break;
        case "total":
          cmp = ((bwA?.upload_total ?? 0) + (bwA?.download_total ?? 0)) -
                ((bwB?.upload_total ?? 0) + (bwB?.download_total ?? 0));
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [wsData?.devices, wsData?.bandwidth, sortCol, sortDir]);

  // === WIDGET RENDER FONKSİYONLARI ===

  const renderConnectionStatus = () => (
    <WidgetWrapper title="Bağlantı" icon={<Wifi size={14} />} hideHeader>
      <div className="flex items-center gap-2 text-xs h-full px-2">
        <div
          className={`w-2 h-2 rounded-full ${
            connected ? "bg-neon-green animate-pulse-neon" : "bg-neon-red"
          }`}
        />
        <span className="text-gray-400">
          {connected ? "Canlı Veri Akışı" : "Bağlantı Bekleniyor..."}
        </span>
      </div>
    </WidgetWrapper>
  );

  const renderStatCards = () => (
    <WidgetWrapper title="İstatistikler" icon={<Activity size={14} />} hideHeader>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 h-full items-center px-1">
        <StatCard title="Upload" value={formatBps(uploadBps)} icon={<Upload size={18} />} neonColor="cyan" />
        <StatCard title="Download" value={formatBps(downloadBps)} icon={<Download size={18} />} neonColor="magenta" />
        <StatCard title="DNS Sorgusu" value={totalQueries.toLocaleString("tr-TR")} icon={<Search size={18} />} neonColor="green" />
        <StatCard title="Engellenen" value={blockedQueries.toLocaleString("tr-TR")} icon={<ShieldBan size={18} />} neonColor="amber" />
        <StatCard title="Cihaz" value={wsData?.device_count ?? summary?.devices?.online ?? 0} icon={<Wifi size={18} />} neonColor="cyan" />
      </div>
    </WidgetWrapper>
  );

  const renderBandwidthChart = () => (
    <WidgetWrapper title="Gerçek Zamanlı Bandwidth" icon={<Activity size={14} />} neonColor="cyan">
      <div className="h-full">
        {bwHistory.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={bwHistory}>
              <defs>
                <linearGradient id="bwUpGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#00f0ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bwDownGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ff00e5" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#ff00e5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" stroke="#555" fontSize={9} tickLine={false} />
              <YAxis tickFormatter={(v: number) => formatBps(v)} stroke="#555" fontSize={9} tickLine={false} width={55} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #333", borderRadius: 8, fontSize: 12 }}
                formatter={(value: number, name: string) => [formatBps(value), name === "up" ? "Upload" : "Download"]}
              />
              <Area type="monotone" dataKey="up" stroke="#00f0ff" fill="url(#bwUpGrad)" strokeWidth={1.5} />
              <Area type="monotone" dataKey="down" stroke="#ff00e5" fill="url(#bwDownGrad)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500 text-xs">
            Bandwidth verisi bekleniyor...
          </div>
        )}
      </div>
    </WidgetWrapper>
  );

  const renderDeviceTraffic = () => (
    <WidgetWrapper title="Cihaz Trafiği" icon={<Activity size={14} />} neonColor="cyan">
      {sortedDevices.length > 0 ? (
        <div className="h-full overflow-y-auto overflow-x-auto scrollbar-thin">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-800/90 backdrop-blur-sm z-10">
              <tr className="text-gray-400 border-b border-white/10">
                <th className="text-left py-1.5 px-1 cursor-pointer select-none hover:text-gray-200 transition-colors" onClick={() => handleSort("hostname")}>
                  <span className="inline-flex items-center gap-1">Cihaz <SortIcon col="hostname" /></span>
                </th>
                <th className="text-right py-1.5 px-1 cursor-pointer select-none hover:text-gray-200 transition-colors" onClick={() => handleSort("upload")}>
                  <span className="inline-flex items-center gap-1 justify-end">Upload <SortIcon col="upload" /></span>
                </th>
                <th className="text-right py-1.5 px-1 cursor-pointer select-none hover:text-gray-200 transition-colors" onClick={() => handleSort("download")}>
                  <span className="inline-flex items-center gap-1 justify-end">Download <SortIcon col="download" /></span>
                </th>
                <th className="text-right py-1.5 px-1 cursor-pointer select-none hover:text-gray-200 transition-colors" onClick={() => handleSort("total")}>
                  <span className="inline-flex items-center gap-1 justify-end">Toplam <SortIcon col="total" /></span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDevices.map((dev: any) => {
                const bw = wsData?.bandwidth?.devices?.[String(dev.id)];
                return (
                  <tr key={dev.id} className="border-b border-white/5 hover:bg-white/5 cursor-pointer" onClick={() => navigate(`/devices/${dev.id}`)}>
                    <td className="py-1 px-1"><span className="text-gray-200 truncate block max-w-[130px]">{dev.hostname}</span></td>
                    <td className="py-1 px-1 text-right text-cyan-400">{bw ? formatBps(bw.upload_bps) : "-"}</td>
                    <td className="py-1 px-1 text-right text-pink-400">{bw ? formatBps(bw.download_bps) : "-"}</td>
                    <td className="py-1 px-1 text-right text-gray-400">{bw ? formatBytes(bw.upload_total + bw.download_total) : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500 text-xs">Cihaz bekleniyor...</p>
      )}
    </WidgetWrapper>
  );

  const renderDnsSummary = () => (
    <WidgetWrapper title="DNS Özet" icon={<Search size={14} />} neonColor="green">
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs"><span className="text-gray-400">Sorgu/dk</span><span className="font-bold neon-text">{queriesPerMin}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Engelleme</span><span className="font-bold text-neon-red">%{blockPct}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Engelli Domain</span><span className="font-bold">{(summary?.dns?.total_blocked_domains ?? 0).toLocaleString("tr-TR")}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Aktif Liste</span><span className="font-bold">{summary?.dns?.active_blocklists ?? 0}</span></div>
      </div>
    </WidgetWrapper>
  );

  const renderDeviceStatus = () => (
    <WidgetWrapper title="Cihaz Durumu" icon={<Wifi size={14} />} neonColor="amber">
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs"><span className="text-gray-400">Toplam</span><span className="font-bold">{summary?.devices?.total ?? 0}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Çevrimiçi</span><span className="font-bold text-neon-green">{summary?.devices?.online ?? 0}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Engelli</span><span className="font-bold text-neon-red">{summary?.devices?.blocked ?? 0}</span></div>
      </div>
    </WidgetWrapper>
  );

  const renderVpnStatus = () => (
    <WidgetWrapper title="VPN Durumu" icon={<Shield size={14} />} neonColor="cyan">
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-gray-400">Sunucu</span>
          <NeonBadge label={wsData?.vpn?.enabled ?? summary?.vpn?.enabled ? "AKTİF" : "PASİF"} variant={wsData?.vpn?.enabled ?? summary?.vpn?.enabled ? "green" : "red"} />
        </div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Bağlı Peer</span><span className="font-bold text-neon-green">{wsData?.vpn?.connected_peers ?? summary?.vpn?.connected_peers ?? 0}</span></div>
        <div className="flex justify-between text-xs"><span className="text-gray-400">Toplam Peer</span><span className="font-bold">{wsData?.vpn?.total_peers ?? summary?.vpn?.total_peers ?? 0}</span></div>
        {(summary?.vpn?.total_rx ?? 0) + (summary?.vpn?.total_tx ?? 0) > 0 && (
          <div className="flex justify-between text-xs"><span className="text-gray-400">Transfer</span><span className="font-bold text-gray-300">↓{formatBytes(summary?.vpn?.total_rx ?? 0)} ↑{formatBytes(summary?.vpn?.total_tx ?? 0)}</span></div>
        )}
      </div>
    </WidgetWrapper>
  );

  const renderTopDomains = () => (
    <WidgetWrapper title="En Çok Sorgulanan" icon={<Globe size={14} className="text-neon-cyan" />}>
      {summary?.top_queried_domains && summary.top_queried_domains.length > 0 ? (
        <div className="space-y-1">
          {summary.top_queried_domains.map((d: any, i: number) => (
            <div key={d.domain} className="flex items-center justify-between py-1 border-b border-glass-border/50 last:border-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-xs text-gray-500 w-3">{i + 1}</span>
                <span className="text-xs truncate">{d.domain}</span>
              </div>
              <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{d.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-xs">Henüz veri yok</p>
      )}
    </WidgetWrapper>
  );

  const renderTopBlocked = () => (
    <WidgetWrapper title="En Çok Engellenen" icon={<Ban size={14} className="text-neon-red" />} neonColor="magenta">
      {summary?.top_blocked_domains && summary.top_blocked_domains.length > 0 ? (
        <div className="space-y-1">
          {summary.top_blocked_domains.map((d: any, i: number) => (
            <div key={d.domain} className="flex items-center justify-between py-1 border-b border-glass-border/50 last:border-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-xs text-gray-500 w-3">{i + 1}</span>
                <span className="text-xs truncate text-neon-red/80">{d.domain}</span>
              </div>
              <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{d.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-xs">Henüz engellenen yok</p>
      )}
    </WidgetWrapper>
  );

  const renderConnectedDevices = () => (
    <WidgetWrapper title="Bağlı Cihazlar" icon={<Users size={14} className="text-neon-green" />} neonColor="green">
      {wsData?.devices && wsData.devices.length > 0 ? (
        <div className="space-y-1">
          {wsData.devices.map((dev: any) => (
            <div key={dev.mac} className="flex items-center justify-between py-1 border-b border-glass-border/50 last:border-0">
              <div className="min-w-0">
                <p className="text-xs font-medium truncate">{dev.hostname}</p>
                <p className="text-[10px] text-gray-500">{dev.ip}</p>
              </div>
              <NeonBadge label={dev.is_online ? "ON" : "OFF"} variant={dev.is_online ? "green" : "red"} />
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-xs">Cihaz bekleniyor...</p>
      )}
    </WidgetWrapper>
  );

  const renderTopClients = () => (
    <WidgetWrapper title="En Aktif İstemciler (24s)" icon={<Wifi size={14} className="text-neon-cyan" />}>
      {summary?.top_clients && summary.top_clients.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
          {summary.top_clients.map((c: any) => {
            const maxCount = summary.top_clients[0]?.query_count || 1;
            const pct = Math.round((c.query_count / maxCount) * 100);
            return (
              <div key={c.client_ip} className="relative bg-glass-card/50 rounded-lg p-2 overflow-hidden">
                <div className="absolute bottom-0 left-0 h-0.5 bg-neon-cyan/40 rounded" style={{ width: `${pct}%` }} />
                <p className="text-xs font-mono">{c.client_ip}</p>
                <p className="text-base font-bold neon-text">{c.query_count.toLocaleString("tr-TR")}</p>
                <p className="text-[10px] text-gray-500">sorgu</p>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-gray-500 text-xs">Henüz veri yok</p>
      )}
    </WidgetWrapper>
  );

  // Widget ID -> render fonksiyonu eşlemesi
  const widgetRenderers: Record<string, ReactNode> = {
    "connection-status": renderConnectionStatus(),
    "stat-cards": renderStatCards(),
    "bandwidth-chart": renderBandwidthChart(),
    "device-traffic": renderDeviceTraffic(),
    "dns-summary": renderDnsSummary(),
    "device-status": renderDeviceStatus(),
    "vpn-status": renderVpnStatus(),
    "top-domains": renderTopDomains(),
    "top-blocked": renderTopBlocked(),
    "connected-devices": renderConnectedDevices(),
    "top-clients": renderTopClients(),
  };

  return (
    <div>
      <TopBar
        title="Dashboard"
        connected={connected}
        actions={
          <WidgetToggleMenu
            visibleWidgets={visibleWidgets}
            onToggle={toggleWidget}
            onReset={resetLayout}
          />
        }
      />

      <DashboardGrid
        layouts={layouts}
        visibleWidgets={visibleWidgets}
        onLayoutChange={onLayoutChange}
        onBreakpointChange={onBreakpointChange}
        widgetRenderers={widgetRenderers}
      />
    </div>
  );
}
