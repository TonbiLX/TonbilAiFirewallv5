// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz detay sayfası: trafik, DNS, aktif bağlantılar, bandwidth grafiği + yonetim aksiyonlari

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Wifi, WifiOff, Upload, Download, Network, Globe,
  Activity, Clock, Shield, Smartphone, Tv, Laptop, Cpu, Gamepad2,
  MonitorSmartphone, Router, RefreshCw, ArrowUpRight, ArrowDownLeft,
  Ban, Pencil, Check, X, Users, Gauge, Pin, ShieldBan, History,
  CheckCircle, AlertTriangle, ShieldAlert, Glasses, Monitor,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { GlassCard } from '../components/common/GlassCard';
import { StatCard } from '../components/common/StatCard';
import { NeonBadge } from '../components/common/NeonBadge';
import {
  fetchDevices, updateDevice, blockDevice, unblockDevice,
  fetchDeviceConnectionHistory, setDeviceBandwidthLimit,
} from '../services/deviceApi';
import { fetchProfiles } from '../services/profileApi';
import { createStaticLease } from '../services/dhcpApi';
import { fetchDeviceServices } from '../services/serviceBlockApi';
import {
  fetchDeviceTrafficHistory, fetchDeviceActiveConnections,
  fetchDeviceTopDestinations, fetchDeviceDnsQueries,
  fetchPerDeviceTraffic, fetchLiveFlows,
} from '../services/trafficApi';
import type { Device, ActiveConnection, TopDestination, DeviceTrafficHistory, Profile, DeviceConnectionLog, DeviceBlockedService, LiveFlow } from '../types';

// Byte formatla
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// bps formatla
function formatBps(bps: number): string {
  if (bps === 0) return '0 bps';
  if (bps < 1000) return bps + ' bps';
  if (bps < 1000000) return (bps / 1000).toFixed(1) + ' Kbps';
  if (bps < 1000000000) return (bps / 1000000).toFixed(1) + ' Mbps';
  return (bps / 1000000000).toFixed(2) + ' Gbps';
}

// Online sure formatlama
function formatOnlineTime(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return '0dk';
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}g`);
  if (hours > 0) parts.push(`${hours}s`);
  if (minutes > 0 || parts.length === 0) parts.push(`${minutes}dk`);
  return parts.join(' ');
}

// Cihaz tipi ikonu (header icin)
function getDeviceIcon(deviceType: string | null) {
  switch (deviceType) {
    case 'phone': return <Smartphone size={20} />;
    case 'tv': return <Tv size={20} />;
    case 'computer': return <Laptop size={20} />;
    case 'iot': return <Cpu size={20} />;
    case 'game_console': return <Gamepad2 size={20} />;
    case 'tablet': return <MonitorSmartphone size={20} />;
    default: return <Router size={20} />;
  }
}

// Profil tip renkleri
const profileTypeVariant: Record<string, 'amber' | 'cyan' | 'magenta'> = {
  child: 'amber', adult: 'cyan', guest: 'magenta',
};
const profileTypeLabel: Record<string, string> = {
  child: 'Cocuk', adult: 'Yetiskin', guest: 'Misafir',
};

type TabType = 'overview' | 'traffic' | 'dns' | 'connections' | 'management';

export function DeviceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const deviceId = parseInt(id || '0');

  // --- Mevcut state ---
  const [device, setDevice] = useState<Device | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [trafficHistory, setTrafficHistory] = useState<DeviceTrafficHistory[]>([]);
  const [connections, setConnections] = useState<ActiveConnection[]>([]);
  const [topDestinations, setTopDestinations] = useState<TopDestination[]>([]);
  const [dnsQueries, setDnsQueries] = useState<any[]>([]);
  const [trafficSummary, setTrafficSummary] = useState<any>(null);
  const [deviceFlows, setDeviceFlows] = useState<LiveFlow[]>([]);
  const [loading, setLoading] = useState(true);

  // --- Yonetim state ---
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [connectionHistory, setConnectionHistory] = useState<DeviceConnectionLog[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [editingHostname, setEditingHostname] = useState(false);
  const [editHostnameValue, setEditHostnameValue] = useState('');
  const [editingBandwidth, setEditingBandwidth] = useState(false);
  const [editBandwidthValue, setEditBandwidthValue] = useState('');
  const [blockedServices, setBlockedServices] = useState<DeviceBlockedService[]>([]);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // --- Veri yukleme ---
  const loadDevice = useCallback(async () => {
    try {
      const res = await fetchDevices();
      const dev = res.data.find((d: Device) => d.id === deviceId);
      if (dev) setDevice(dev);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  const loadOverview = useCallback(async () => {
    try {
      const [histRes, topRes, perDevRes] = await Promise.all([
        fetchDeviceTrafficHistory(deviceId, 24),
        fetchDeviceTopDestinations(deviceId, 24),
        fetchPerDeviceTraffic('24h'),
      ]);
      setTrafficHistory(histRes.data);
      setTopDestinations(topRes.data);
      const summary = perDevRes.data.find((d: any) => d.device_id === deviceId);
      setTrafficSummary(summary);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  const loadConnections = useCallback(async () => {
    try {
      const res = await fetchDeviceActiveConnections(deviceId);
      setConnections(res.data);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  const loadDns = useCallback(async () => {
    try {
      const res = await fetchDeviceDnsQueries(deviceId, 100);
      setDnsQueries(res.data);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  const loadProfiles = useCallback(async () => {
    try {
      const res = await fetchProfiles();
      setProfiles(res.data);
    } catch (e) { console.error(e); }
  }, []);

  const loadConnectionHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await fetchDeviceConnectionHistory(deviceId, 10);
      setConnectionHistory(res.data);
    } catch (e) { console.error(e); }
    finally { setHistoryLoading(false); }
  }, [deviceId]);

  const loadBlockedServices = useCallback(async () => {
    try {
      const data = await fetchDeviceServices(deviceId);
      setBlockedServices(data);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  const loadDeviceFlows = useCallback(async () => {
    try {
      const { data } = await fetchLiveFlows({ device_id: deviceId, sort: 'bytes_desc' });
      setDeviceFlows(data);
    } catch (e) { console.error(e); }
  }, [deviceId]);

  // --- useEffect'ler ---
  useEffect(() => {
    setLoading(true);
    Promise.all([loadDevice(), loadOverview(), loadProfiles()]).finally(() => setLoading(false));
  }, [loadDevice, loadOverview, loadProfiles]);

  useEffect(() => {
    if (activeTab === 'traffic') loadDeviceFlows();
    if (activeTab === 'connections') loadConnections();
    if (activeTab === 'dns') loadDns();
    if (activeTab === 'management') {
      loadConnectionHistory();
      loadBlockedServices();
    }
  }, [activeTab, loadDeviceFlows, loadConnections, loadDns, loadConnectionHistory, loadBlockedServices]);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeTab === 'overview') loadOverview();
      if (activeTab === 'connections') loadConnections();
    }, 15000);
    return () => clearInterval(interval);
  }, [activeTab, loadOverview, loadConnections]);

  // Canli akis yenileme (5s) - sadece trafik tabinda
  useEffect(() => {
    if (activeTab !== 'traffic') return;
    const interval = setInterval(loadDeviceFlows, 5000);
    return () => clearInterval(interval);
  }, [activeTab, loadDeviceFlows]);

  // Feedback zamanlayicisi
  useEffect(() => {
    if (feedback) {
      const t = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(t);
    }
  }, [feedback]);

  // --- Aksiyon handler'lari ---
  const handleBlock = async () => {
    if (!device) return;
    try {
      await blockDevice(device.id);
      setFeedback({ type: 'success', message: 'Cihaz engellendi.' });
      await loadDevice();
    } catch {
      setFeedback({ type: 'error', message: 'Cihaz engellenirken hata olustu.' });
    }
  };

  const handleUnblock = async () => {
    if (!device) return;
    try {
      await unblockDevice(device.id);
      setFeedback({ type: 'success', message: 'Cihaz engeli kaldirildi.' });
      await loadDevice();
    } catch {
      setFeedback({ type: 'error', message: 'Engel kaldirilirken hata olustu.' });
    }
  };

  const handlePinIp = async () => {
    if (!device?.mac_address || !device?.ip_address) return;
    try {
      await createStaticLease({
        mac_address: device.mac_address,
        ip_address: device.ip_address,
        hostname: device.hostname || undefined,
      });
      setFeedback({
        type: 'success',
        message: `${device.ip_address} adresi ${device.hostname || device.mac_address} icin sabitlendi.`,
      });
    } catch {
      setFeedback({ type: 'error', message: 'IP sabitlenirken hata olustu.' });
    }
  };

  const handleProfileAssign = async (profileId: number | null) => {
    if (!device) return;
    try {
      await updateDevice(device.id, { profile_id: profileId });
      setFeedback({ type: 'success', message: 'Profil atamasi guncellendi.' });
      await loadDevice();
    } catch {
      setFeedback({ type: 'error', message: 'Profil atanirken hata olustu.' });
    }
  };

  const startEditHostname = () => {
    if (!device) return;
    setEditingHostname(true);
    setEditHostnameValue(device.hostname || '');
  };

  const saveHostname = async () => {
    if (!device) return;
    try {
      await updateDevice(device.id, { hostname: editHostnameValue.trim() || null });
      setEditingHostname(false);
      setEditHostnameValue('');
      setFeedback({ type: 'success', message: 'Hostname guncellendi.' });
      await loadDevice();
    } catch {
      setFeedback({ type: 'error', message: 'Hostname guncellenirken hata olustu.' });
    }
  };

  const startEditBandwidth = () => {
    if (!device) return;
    setEditingBandwidth(true);
    setEditBandwidthValue(device.bandwidth_limit_mbps?.toString() || '');
  };

  const saveBandwidth = async () => {
    if (!device) return;
    try {
      const val = editBandwidthValue.trim();
      const limitMbps = val ? parseInt(val, 10) : null;
      if (val && (isNaN(limitMbps!) || limitMbps! < 0)) {
        setFeedback({ type: 'error', message: 'Gecerli bir Mbps degeri girin (bos = limitsiz).' });
        return;
      }
      await setDeviceBandwidthLimit(device.id, limitMbps && limitMbps > 0 ? limitMbps : null);
      setEditingBandwidth(false);
      setEditBandwidthValue('');
      setFeedback({
        type: 'success',
        message: limitMbps && limitMbps > 0
          ? `Bant genisligi ${limitMbps} Mbps olarak sinirlandirildi.`
          : 'Bant genisligi siniri kaldirildi.',
      });
      await loadDevice();
    } catch {
      setFeedback({ type: 'error', message: 'Bant genisligi guncellenirken hata olustu.' });
    }
  };

  // --- Loading / Not found ---
  if (loading && !device) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cyan-400" />
      </div>
    );
  }

  if (!device) {
    return (
      <div className="p-6">
        <button onClick={() => navigate('/devices')} className="flex items-center gap-2 text-cyan-400 mb-4">
          <ArrowLeft size={18} /> Geri
        </button>
        <p className="text-gray-400">Cihaz bulunamadi.</p>
      </div>
    );
  }

  const tabs: { key: TabType; label: string }[] = [
    { key: 'overview', label: 'Genel' },
    { key: 'traffic', label: 'Trafik' },
    { key: 'dns', label: 'DNS' },
    { key: 'connections', label: 'Baglantilar' },
    { key: 'management', label: 'Yonetim' },
  ];

  const canPinIp = device.ip_address && device.mac_address &&
    !device.mac_address.startsWith('AA:00:') && !device.mac_address.startsWith('DD:0T:');

  const blockedCount = blockedServices.filter(s => s.blocked).length;

  return (
    <div className="p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button onClick={() => navigate('/devices')} className="p-2 rounded-lg hover:bg-white/5 text-cyan-400">
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-cyan-400">{getDeviceIcon(device.device_type)}</span>
            <h1 className="text-xl font-bold text-white truncate">
              {device.hostname || device.ip_address || device.mac_address}
            </h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {device.is_online
              ? <span className="flex items-center gap-1 text-green-400"><Wifi size={14} /> Online</span>
              : <span className="flex items-center gap-1 text-gray-500"><WifiOff size={14} /> Offline</span>
            }
            <span className="text-gray-500">|</span>
            <span className="text-gray-400">{device.ip_address}</span>
            <span className="text-gray-500 hidden md:inline">|</span>
            <span className="text-gray-500 text-xs hidden md:inline">{device.mac_address}</span>
          </div>
        </div>

        {/* Hizli aksiyon butonlari */}
        <div className="flex items-center gap-2">
          {/* IP Sabitle */}
          {device.ip_address && (
            canPinIp ? (
              <button
                onClick={handlePinIp}
                className="p-2 rounded-lg bg-neon-amber/5 text-gray-400 hover:text-amber-400 hover:bg-amber-500/10 transition-all border border-white/10 hover:border-amber-500/20"
                title="IP Sabitle (Statik Kiralama)"
              >
                <Pin size={16} />
              </button>
            ) : (
              <button
                className="p-2 rounded-lg bg-white/5 text-gray-600 border border-white/5 cursor-not-allowed opacity-50"
                title="MAC adresi bekleniyor"
              >
                <Pin size={16} />
              </button>
            )
          )}
          {/* Servis Engelleme */}
          <button
            onClick={() => navigate(`/devices/${device.id}/services`)}
            className="p-2 rounded-lg bg-cyan-500/5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all border border-white/10 hover:border-cyan-500/20"
            title="Servis Engelleme"
          >
            <ShieldBan size={16} />
          </button>
          {/* Engelle / Kaldir */}
          {device.is_blocked ? (
            <button
              onClick={handleUnblock}
              className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all border border-red-500/20"
              title="Engeli kaldir"
            >
              <Ban size={16} />
            </button>
          ) : (
            <button
              onClick={handleBlock}
              className="p-2 rounded-lg bg-white/5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/20 transition-all border border-white/10"
              title="Engelle"
            >
              <Ban size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Feedback mesaji */}
      {feedback && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
          feedback.type === 'success'
            ? 'bg-green-500/10 text-green-400 border-green-500/20'
            : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
          {feedback.type === 'success' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          {feedback.message}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-black/20 rounded-lg p-1 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'bg-cyan-500/20 text-cyan-400'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ========== GENEL ========== */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard title="Upload" value={formatBytes(trafficSummary?.upload_bytes || 0)} icon={<Upload size={20} />} neonColor="cyan" />
            <StatCard title="Download" value={formatBytes(trafficSummary?.download_bytes || 0)} icon={<Download size={20} />} neonColor="magenta" />
            <StatCard title="Hiz" value={formatBps((trafficSummary?.upload_bps || 0) + (trafficSummary?.download_bps || 0))} icon={<Activity size={20} />} neonColor="green" />
            <StatCard title="Baglanti" value={String(trafficSummary?.connection_count || 0)} icon={<Network size={20} />} neonColor="amber" />
          </div>

          {trafficHistory.length > 1 && (
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Bandwidth Trendi</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trafficHistory}>
                    <defs>
                      <linearGradient id="upGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#00f0ff" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="downGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ff00e5" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#ff00e5" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="timestamp" tickFormatter={(v) => new Date(v).toLocaleTimeString('tr', { hour: '2-digit', minute: '2-digit' })} stroke="#555" fontSize={11} />
                    <YAxis tickFormatter={(v) => formatBps(v)} stroke="#555" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: 8 }}
                      labelFormatter={(v) => new Date(v).toLocaleString('tr')}
                      formatter={(value: number, name: string) => [formatBps(value), name === 'upload_bps' ? 'Upload' : 'Download']}
                    />
                    <Area type="monotone" dataKey="upload_bps" stroke="#00f0ff" fill="url(#upGrad)" strokeWidth={2} />
                    <Area type="monotone" dataKey="download_bps" stroke="#ff00e5" fill="url(#downGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </GlassCard>
          )}

          {topDestinations.length > 0 && (
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">En Cok Erisilen Hedefler</h3>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {topDestinations.slice(0, 15).map((dest, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/5">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <Globe size={14} className="text-cyan-400 flex-shrink-0" />
                      <span className="text-sm text-gray-200 truncate">{dest.domain}</span>
                      {dest.category && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-white/10 text-gray-400 flex-shrink-0">{dest.category}</span>
                      )}
                    </div>
                    <span className="text-sm text-gray-400 ml-2 flex-shrink-0">{formatBytes(dest.total_bytes)}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      )}

      {/* ========== TRAFIK ========== */}
      {activeTab === 'traffic' && (
        <div className="space-y-4">
          <GlassCard>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Hedef Bazinda Trafik Dagilimi</h3>
            {topDestinations.length > 0 ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topDestinations.slice(0, 10)} layout="vertical">
                    <XAxis type="number" tickFormatter={(v) => formatBytes(v)} stroke="#555" fontSize={11} />
                    <YAxis dataKey="domain" type="category" width={150} stroke="#555" fontSize={11} tick={{ fill: '#aaa' }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: 8 }}
                      formatter={(value: number) => [formatBytes(value)]}
                    />
                    <Bar dataKey="bytes_received" fill="#ff00e5" name="Download" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="bytes_sent" fill="#00f0ff" name="Upload" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-500 text-sm py-4">Trafik verisi bulunamadi.</p>
            )}
          </GlassCard>

          {/* Canli Veri Akisi */}
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Activity size={14} className="text-neon-cyan" />
                Canli Veri Akisi
              </h3>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-gray-500 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  {deviceFlows.length} aktif akis
                </span>
                <button
                  onClick={loadDeviceFlows}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-gray-400 hover:text-neon-cyan bg-glass-light border border-glass-border hover:border-neon-cyan/30 transition-all"
                  title="Yenile"
                >
                  <RefreshCw size={12} />
                  Yenile
                </button>
              </div>
            </div>
            {deviceFlows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-white/10 text-xs uppercase tracking-wider">
                      <th className="text-center py-2 px-1 w-8">Yon</th>
                      <th className="text-left py-2 px-2">Hedef</th>
                      <th className="text-left py-2 px-2">Proto</th>
                      <th className="text-left py-2 px-2">Uygulama</th>
                      <th className="text-left py-2 px-2">Durum</th>
                      <th className="text-right py-2 px-2">
                        <Upload size={10} className="inline mr-0.5" />Giden
                      </th>
                      <th className="text-right py-2 px-2">
                        <Download size={10} className="inline mr-0.5" />Gelen
                      </th>
                      <th className="text-right py-2 px-2">Toplam</th>
                      <th className="text-right py-2 px-2">Hiz</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deviceFlows.map((flow) => {
                      const bytesTotal = flow.bytes_sent + flow.bytes_received;
                      const isLarge = bytesTotal >= 10_000_000;
                      return (
                        <tr key={flow.flow_id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                          <td className="py-1.5 px-1 text-center" title={flow.direction === "inbound" ? "Gelen" : "Giden"}>
                            {flow.direction === "inbound" ? (
                              <ArrowDownLeft size={14} className="text-pink-400 inline-block" />
                            ) : (
                              <ArrowUpRight size={14} className="text-cyan-400 inline-block" />
                            )}
                          </td>
                          <td className="py-1.5 px-2 font-mono text-xs">
                            <div>
                              <span className="text-gray-200">{flow.dst_domain || flow.dst_ip}</span>
                              <span className="text-gray-500">:{flow.dst_port}</span>
                              {flow.dst_domain && flow.dst_domain !== flow.dst_ip && (
                                <span className="block text-gray-600 text-[10px]">{flow.dst_ip}</span>
                              )}
                            </div>
                          </td>
                          <td className="py-1.5 px-2 text-xs text-gray-400">{flow.protocol}</td>
                          <td className="py-1.5 px-2 text-xs">
                            {flow.app_name ? (
                              <span className="text-neon-cyan font-medium">{flow.app_name}</span>
                            ) : flow.service_name ? (
                              <span className="text-gray-400">{flow.service_name}</span>
                            ) : (
                              <span className="text-gray-600">--</span>
                            )}
                          </td>
                          <td className="py-1.5 px-2 text-xs">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                              flow.state === 'ESTABLISHED' ? 'bg-green-500/10 text-green-400' :
                              flow.state === 'SYN_SENT' || flow.state === 'SYN_RECV' ? 'bg-yellow-500/10 text-yellow-400' :
                              flow.state === 'TIME_WAIT' || flow.state === 'CLOSE_WAIT' ? 'bg-gray-500/10 text-gray-500' :
                              'bg-gray-500/10 text-gray-400'
                            }`}>
                              {flow.state || '--'}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-xs text-right text-cyan-400">{formatBytes(flow.bytes_sent)}</td>
                          <td className="py-1.5 px-2 text-xs text-right text-pink-400">{formatBytes(flow.bytes_received)}</td>
                          <td className="py-1.5 px-2 text-xs text-right">
                            {isLarge ? (
                              <span className="text-pink-400 font-semibold animate-pulse">{formatBytes(bytesTotal)}</span>
                            ) : (
                              <span className="text-gray-300">{formatBytes(bytesTotal)}</span>
                            )}
                          </td>
                          <td className="py-1.5 px-2 text-xs text-right">
                            {(flow.bps_in > 0 || flow.bps_out > 0) ? (
                              <div className="whitespace-nowrap">
                                <span className="text-pink-400 text-[10px]">{formatBps(flow.bps_in)}</span>
                                <span className="text-gray-600 mx-0.5">/</span>
                                <span className="text-cyan-400 text-[10px]">{formatBps(flow.bps_out)}</span>
                              </div>
                            ) : (
                              <span className="text-gray-600">--</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="mt-2 text-[10px] text-gray-600 text-right">
                  5 saniyede yenileniyor
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Activity size={32} className="mx-auto mb-2 opacity-20" />
                <p className="text-xs">Bu cihazin aktif veri akisi bulunamadi</p>
              </div>
            )}
          </GlassCard>
        </div>
      )}

      {/* ========== DNS ========== */}
      {activeTab === 'dns' && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">DNS Sorgu Gecmisi</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-white/10">
                  <th className="text-left py-2 px-2">Zaman</th>
                  <th className="text-left py-2 px-2">Domain</th>
                  <th className="text-left py-2 px-2">Tip</th>
                  <th className="text-left py-2 px-2">Durum</th>
                  <th className="text-left py-2 px-2">Yanit</th>
                </tr>
              </thead>
              <tbody>
                {dnsQueries.map((q: any) => (
                  <tr key={q.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-1.5 px-2 text-gray-400 text-xs">
                      {q.timestamp ? new Date(q.timestamp).toLocaleTimeString('tr') : '-'}
                    </td>
                    <td className="py-1.5 px-2 text-gray-200 truncate max-w-[200px]">{q.domain}</td>
                    <td className="py-1.5 px-2 text-gray-400">{q.query_type}</td>
                    <td className="py-1.5 px-2">
                      {q.blocked
                        ? <span className="text-red-400 text-xs px-1.5 py-0.5 rounded bg-red-500/10">Engel</span>
                        : <span className="text-green-400 text-xs px-1.5 py-0.5 rounded bg-green-500/10">Izin</span>
                      }
                    </td>
                    <td className="py-1.5 px-2 text-gray-500 text-xs">{q.response_ip || '-'}</td>
                  </tr>
                ))}
                {dnsQueries.length === 0 && (
                  <tr><td colSpan={5} className="text-gray-500 text-center py-4">DNS sorgusu bulunamadi.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* ========== BAGLANTILAR ========== */}
      {activeTab === 'connections' && (
        <GlassCard>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Aktif Baglantilar ({connections.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-white/10">
                  <th className="text-left py-2 px-2">Protokol</th>
                  <th className="text-left py-2 px-2">Hedef</th>
                  <th className="text-left py-2 px-2">Port</th>
                  <th className="text-left py-2 px-2">Domain</th>
                  <th className="text-right py-2 px-2">Gonderilen</th>
                  <th className="text-right py-2 px-2">Alinan</th>
                  <th className="text-left py-2 px-2">Durum</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((conn, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-1.5 px-2 text-cyan-400 text-xs font-mono">{conn.protocol}</td>
                    <td className="py-1.5 px-2 text-gray-300 text-xs font-mono">{conn.dst_ip}</td>
                    <td className="py-1.5 px-2 text-gray-400 text-xs">{conn.dst_port}</td>
                    <td className="py-1.5 px-2 text-gray-200 truncate max-w-[180px]">
                      {conn.dst_domain || <span className="text-gray-600">-</span>}
                    </td>
                    <td className="py-1.5 px-2 text-cyan-400 text-xs text-right">{formatBytes(conn.bytes_sent)}</td>
                    <td className="py-1.5 px-2 text-pink-400 text-xs text-right">{formatBytes(conn.bytes_received)}</td>
                    <td className="py-1.5 px-2">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        conn.state === 'ESTABLISHED' ? 'bg-green-500/10 text-green-400' :
                        conn.state === 'TIME_WAIT' ? 'bg-yellow-500/10 text-yellow-400' :
                        'bg-gray-500/10 text-gray-400'
                      }`}>
                        {conn.state || 'N/A'}
                      </span>
                    </td>
                  </tr>
                ))}
                {connections.length === 0 && (
                  <tr><td colSpan={7} className="text-gray-500 text-center py-4">Aktif baglanti bulunamadi.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* ========== YONETIM ========== */}
      {activeTab === 'management' && (
        <div className="space-y-4">
          {/* Satir 1: Cihaz Bilgileri + Cihaz Durumu yan yana */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Cihaz Bilgileri */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Pencil size={14} className="text-cyan-400" /> Cihaz Bilgileri
              </h3>
              <div className="space-y-4">
                {/* Hostname */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Hostname</span>
                  {editingHostname ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={editHostnameValue}
                        onChange={(e) => setEditHostnameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') saveHostname();
                          if (e.key === 'Escape') { setEditingHostname(false); setEditHostnameValue(''); }
                        }}
                        className="bg-white/5 border border-cyan-500/30 rounded-lg px-2 py-1 text-sm text-white focus:outline-none focus:border-cyan-500/50 w-48"
                        autoFocus
                      />
                      <button onClick={saveHostname} className="p-1 text-green-400 hover:bg-green-500/10 rounded"><Check size={14} /></button>
                      <button onClick={() => { setEditingHostname(false); setEditHostnameValue(''); }} className="p-1 text-gray-400 hover:bg-white/10 rounded"><X size={14} /></button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-white">{device.hostname || 'Bilinmeyen Cihaz'}</span>
                      <button onClick={startEditHostname} className="p-1 text-gray-500 hover:text-cyan-400 transition-colors"><Pencil size={12} /></button>
                    </div>
                  )}
                </div>

                {/* Profil atama */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Profil</span>
                  <div className="flex items-center gap-2">
                    <Users size={14} className="text-gray-500" />
                    <select
                      value={device.profile_id?.toString() || ''}
                      onChange={(e) => handleProfileAssign(e.target.value ? parseInt(e.target.value) : null)}
                      className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 min-w-[130px]"
                    >
                      <option value="">Profil Yok</option>
                      {profiles.map(p => (
                        <option key={p.id} value={p.id.toString()}>
                          {p.name} ({profileTypeLabel[p.profile_type] || p.profile_type})
                        </option>
                      ))}
                    </select>
                    {device.profile_id && (() => {
                      const prof = profiles.find(p => p.id === device.profile_id);
                      return prof ? <NeonBadge label={prof.name} variant={profileTypeVariant[prof.profile_type] || 'cyan'} /> : null;
                    })()}
                  </div>
                </div>

                {/* Bant genisligi */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Bant Genisligi</span>
                  {editingBandwidth ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        value={editBandwidthValue}
                        onChange={(e) => setEditBandwidthValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') saveBandwidth();
                          if (e.key === 'Escape') { setEditingBandwidth(false); setEditBandwidthValue(''); }
                        }}
                        className="bg-white/5 border border-cyan-500/30 rounded-lg px-2 py-1 text-xs text-white focus:outline-none w-20"
                        placeholder="Mbps"
                        autoFocus
                      />
                      <button onClick={saveBandwidth} className="p-1 text-green-400 hover:bg-green-500/10 rounded"><Check size={12} /></button>
                      <button onClick={() => { setEditingBandwidth(false); setEditBandwidthValue(''); }} className="p-1 text-gray-400 hover:bg-white/10 rounded"><X size={12} /></button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Gauge size={14} className="text-gray-500" />
                      <button onClick={startEditBandwidth} className="text-xs text-gray-400 hover:text-cyan-400 transition-colors flex items-center gap-1">
                        {device.bandwidth_limit_mbps ? `${device.bandwidth_limit_mbps} Mbps` : 'Limitsiz'}
                        <Pencil size={10} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </GlassCard>

            {/* Cihaz Durumu + Aksiyonlar */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Shield size={14} className="text-cyan-400" /> Cihaz Durumu
              </h3>
              <div className="space-y-4">
                {/* Engelleme durumu */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Internet Erisimi</span>
                  {device.is_blocked
                    ? <NeonBadge label="Engelli" variant="red" />
                    : <NeonBadge label="Aktif" variant="green" />
                  }
                </div>

                {/* Online durumu */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Cevrimici Durum</span>
                  {device.is_online
                    ? <NeonBadge label="Cevrimici" variant="green" pulse />
                    : <NeonBadge label="Cevrimdisi" variant="red" />
                  }
                </div>

                {/* Online sure */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Toplam Online</span>
                  <span className="text-sm text-gray-300 flex items-center gap-1">
                    <Clock size={12} className="text-gray-500" />
                    {formatOnlineTime(device.total_online_seconds || 0)}
                  </span>
                </div>

                {/* Engelle / Kaldir butonu */}
                {device.is_blocked ? (
                  <button
                    onClick={handleUnblock}
                    className="w-full py-2.5 rounded-xl text-sm font-medium bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 transition-all flex items-center justify-center gap-2"
                  >
                    <Ban size={16} /> Engeli Kaldir
                  </button>
                ) : (
                  <button
                    onClick={handleBlock}
                    className="w-full py-2.5 rounded-xl text-sm font-medium bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
                  >
                    <Ban size={16} /> Cihazi Engelle
                  </button>
                )}

                {/* IP Sabitle butonu */}
                {device.ip_address && (
                  <button
                    onClick={canPinIp ? handlePinIp : undefined}
                    disabled={!canPinIp}
                    className={`w-full py-2.5 rounded-xl text-sm font-medium border flex items-center justify-center gap-2 transition-all ${
                      canPinIp
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20'
                        : 'bg-white/5 text-gray-600 border-white/10 cursor-not-allowed opacity-50'
                    }`}
                  >
                    <Pin size={16} /> IP Sabitle ({device.ip_address})
                  </button>
                )}
              </div>
            </GlassCard>
          </div>

          {/* Satir 2: Servis Engelleme + Cihaz Detaylari yan yana */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Servis Engelleme Ozeti */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <ShieldBan size={14} className="text-cyan-400" /> Servis Engelleme
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Engelli Servisler</span>
                  <span className="text-sm">
                    <span className="text-red-400 font-bold">{blockedCount}</span>
                    <span className="text-gray-500"> / {blockedServices.length}</span>
                  </span>
                </div>

                {blockedCount > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {blockedServices.filter(s => s.blocked).slice(0, 12).map(s => (
                      <span key={s.service_id} className="text-xs px-2 py-1 rounded-lg bg-red-500/10 text-red-400 border border-red-500/15">
                        {s.name}
                      </span>
                    ))}
                    {blockedCount > 12 && (
                      <span className="text-xs px-2 py-1 rounded-lg bg-white/5 text-gray-500">
                        +{blockedCount - 12} daha
                      </span>
                    )}
                  </div>
                )}

                {blockedCount === 0 && (
                  <p className="text-xs text-gray-500 py-2">Engellenen servis bulunmuyor.</p>
                )}

                <button
                  onClick={() => navigate(`/devices/${device.id}/services`)}
                  className="w-full py-2.5 rounded-xl text-sm font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 transition-all flex items-center justify-center gap-2"
                >
                  <ShieldBan size={16} /> Tum Servisleri Yonet
                </button>
              </div>
            </GlassCard>

            {/* Cihaz Detaylari */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Activity size={14} className="text-cyan-400" /> Cihaz Detaylari
              </h3>
              <div className="space-y-3">
                {[
                  { label: 'MAC Adresi', value: device.mac_address },
                  { label: 'IP Adresi', value: device.ip_address || '-' },
                  { label: 'Uretici', value: device.manufacturer || '-' },
                  { label: 'Isletim Sistemi', value: device.detected_os || '-' },
                  { label: 'Cihaz Tipi', value: device.device_type || '-' },
                  { label: 'Ilk Gorulen', value: device.first_seen ? new Date(device.first_seen).toLocaleString('tr-TR') : '-' },
                  { label: 'Son Gorulen', value: device.last_seen ? new Date(device.last_seen).toLocaleString('tr-TR') : '-' },
                ].map((row, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">{row.label}</span>
                    <span className="text-sm text-gray-300 font-mono">{row.value}</span>
                  </div>
                ))}
                {/* Risk seviyesi */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wide">Risk</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-300">{device.risk_score ?? 0}/100</span>
                    <NeonBadge
                      label={device.risk_level === 'dangerous' ? 'Tehlikeli' : device.risk_level === 'suspicious' ? 'Suphelii' : 'Guvenli'}
                      variant={device.risk_level === 'dangerous' ? 'red' : device.risk_level === 'suspicious' ? 'amber' : 'green'}
                    />
                  </div>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Satir 3: Baglanti Gecmisi */}
          <GlassCard>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <History size={14} className="text-cyan-400" /> Baglanti Gecmisi (Son 10)
            </h3>
            {historyLoading ? (
              <div className="flex items-center justify-center py-6">
                <div className="w-5 h-5 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
              </div>
            ) : connectionHistory.length === 0 ? (
              <p className="text-xs text-gray-500 py-4 text-center">Henuz baglanti gecmisi bulunmuyor.</p>
            ) : (
              <div className="space-y-1.5">
                {connectionHistory.map((log) => (
                  <div key={log.id} className="flex items-center gap-3 text-xs px-3 py-2 bg-white/[0.03] rounded-lg">
                    {log.event_type === 'connect'
                      ? <Wifi size={12} className="text-green-400 flex-shrink-0" />
                      : <WifiOff size={12} className="text-red-400 flex-shrink-0" />
                    }
                    <span className={`font-medium ${log.event_type === 'connect' ? 'text-green-400' : 'text-red-400'}`}>
                      {log.event_type === 'connect' ? 'Baglandi' : 'Ayrildi'}
                    </span>
                    {log.ip_address && <span className="text-gray-500">{log.ip_address}</span>}
                    {log.session_duration_seconds != null && (
                      <span className="text-gray-400">Oturum: {formatOnlineTime(log.session_duration_seconds)}</span>
                    )}
                    <span className="text-gray-600 ml-auto">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString('tr-TR') : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        </div>
      )}
    </div>
  );
}
