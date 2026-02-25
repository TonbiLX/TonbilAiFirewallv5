// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// VPN (WireGuard) yönetim sayfası: gercek config dosyalarindan okuma,
// peer listesi, config indirme, QR kodu gosterimi

import { useState, useEffect, useCallback } from "react";
import {
  Globe,
  Key,
  Download,
  Upload,
  Shield,
  Wifi,
  WifiOff,
  X,
  Copy,
  Check,
  QrCode,
  Power,
  PowerOff,
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchVpnConfig,
  fetchVpnPeers,
  fetchPeerConfig,
  fetchVpnStats,
  startVpnServer,
  stopVpnServer,
  addVpnPeer,
  removeVpnPeer,
} from "../services/vpnApi";
import type { VpnConfig, VpnPeer, VpnStats, VpnPeerConfig } from "../types";

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function VpnPage() {
  const { connected } = useWebSocket();
  const [config, setConfig] = useState<VpnConfig | null>(null);
  const [peers, setPeers] = useState<VpnPeer[]>([]);
  const [stats, setStats] = useState<VpnStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Feedback banner
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Add peer modal
  const [addPeerOpen, setAddPeerOpen] = useState(false);
  const [newPeerName, setNewPeerName] = useState("");
  const [addingPeer, setAddingPeer] = useState(false);

  // Peer config modal
  const [configModal, setConfigModal] = useState<VpnPeerConfig | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  const loadData = useCallback(async () => {
    try {
      const [configRes, peersRes, statsRes] = await Promise.all([
        fetchVpnConfig(),
        fetchVpnPeers(),
        fetchVpnStats(),
      ]);
      setConfig(configRes.data);
      setPeers(peersRes.data);
      setStats(statsRes.data);
      setError(null);
    } catch (err) {
      setError("VPN verileri yüklenemedi");
      console.error("VPN veri yükleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleShowConfig = async (peerName: string) => {
    try {
      const res = await fetchPeerConfig(peerName);
      setConfigModal(res.data);
      setCopied(false);
    } catch (err) {
      console.error("Peer config yükleme hatasi:", err);
    }
  };

  const handleCopyConfig = async () => {
    if (!configModal) return;
    try {
      await navigator.clipboard.writeText(configModal.config_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Kopyalama hatasi:", err);
    }
  };

  const handleDownloadConfig = () => {
    if (!configModal) return;
    const blob = new Blob([configModal.config_text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${configModal.peer_name}.conf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- Sunucu Başlat/Durdur ---
  const handleStartServer = async () => {
    setActionLoading(true);
    try {
      await startVpnServer();
      setFeedback({ type: "success", message: "VPN sunucusu başlatıldı." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Sunucu başlatilamadi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopServer = async () => {
    setActionLoading(true);
    try {
      await stopVpnServer();
      setFeedback({ type: "success", message: "VPN sunucusu durduruldu." });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Sunucu durdurulamadi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setActionLoading(false);
    }
  };

  // --- Peer Ekle ---
  const handleAddPeer = async () => {
    if (!newPeerName.trim()) return;
    setAddingPeer(true);
    try {
      const res = await addVpnPeer(newPeerName.trim());
      setFeedback({ type: "success", message: `"${newPeerName.trim()}" peer eklendi.` });
      setAddPeerOpen(false);
      setNewPeerName("");
      await loadData();
      // Yeni peer'in config'ini goster (private key tek seferlik)
      if (res.data?.name) {
        try {
          const configRes = await fetchPeerConfig(res.data.name);
          setConfigModal(configRes.data);
          setCopied(false);
        } catch {
          // Config gosterilemezse sorun degil
        }
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Peer eklenemedi.";
      setFeedback({ type: "error", message: msg });
    } finally {
      setAddingPeer(false);
    }
  };

  // --- Peer Sil ---
  const handleRemovePeer = async (peerName: string) => {
    if (!confirm(`"${peerName}" peer'i silinecek. Emin misiniz?`)) return;
    try {
      await removeVpnPeer(peerName);
      setFeedback({ type: "success", message: `"${peerName}" peer silindi.` });
      await loadData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Peer silinemedi.";
      setFeedback({ type: "error", message: msg });
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar title="VPN (WireGuard)" connected={connected} />

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

      {/* Sunucu Durumu */}
      {config && (
        <GlassCard neonColor={config.enabled ? "green" : undefined}>
          <div className="flex items-center gap-3 mb-4">
            <Shield size={20} className="text-neon-cyan" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              WireGuard Sunucu Durumu
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Durum */}
            <div className="p-3 bg-surface-800 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Durum</p>
              <div className="flex items-center gap-2">
                {config.enabled ? (
                  <>
                    <Wifi size={14} className="text-neon-green" />
                    <span className="text-sm font-medium text-neon-green">
                      Aktif
                    </span>
                  </>
                ) : (
                  <>
                    <WifiOff size={14} className="text-gray-500" />
                    <span className="text-sm font-medium text-gray-500">
                      Pasif
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Public Key */}
            <div className="p-3 bg-surface-800 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Public Key</p>
              <p
                className="text-xs font-mono text-gray-300 truncate"
                title={config.server_public_key}
              >
                {config.server_public_key
                  ? `${config.server_public_key.substring(0, 20)}...`
                  : "Oluşturulmadı"}
              </p>
            </div>

            {/* Listen Port */}
            <div className="p-3 bg-surface-800 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Dinleme Portu</p>
              <p className="text-sm font-mono text-neon-cyan">
                {config.listen_port}
              </p>
            </div>

            {/* Sunucu Adresi */}
            <div className="p-3 bg-surface-800 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Sunucu Adresi</p>
              <p className="text-sm font-mono text-gray-300">
                {config.server_address}
              </p>
            </div>
          </div>

          {/* Başlat / Durdur Butonu */}
          <div className="mt-4 pt-4 border-t border-glass-border flex items-center gap-3">
            {config.enabled ? (
              <button
                onClick={handleStopServer}
                disabled={actionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-neon-red/10 hover:bg-neon-red/20 border border-neon-red/30 text-neon-red rounded-xl text-sm transition-all disabled:opacity-50"
              >
                {actionLoading ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-red rounded-full animate-spin" />
                ) : (
                  <PowerOff size={16} />
                )}
                Sunucuyu Durdur
              </button>
            ) : (
              <button
                onClick={handleStartServer}
                disabled={actionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-xl text-sm transition-all disabled:opacity-50"
              >
                {actionLoading ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-green rounded-full animate-spin" />
                ) : (
                  <Power size={16} />
                )}
                Sunucuyu Başlat
              </button>
            )}
            <span className="text-xs text-gray-500">
              {config.enabled
                ? "WireGuard VPN sunucusu calisiyor"
                : "WireGuard VPN sunucusu durmus"}
            </span>
          </div>
        </GlassCard>
      )}

      {/* VPN İstatistik Kartlari */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Bagli Peer"
            value={stats.connected_peers}
            icon={<Wifi size={32} />}
            neonColor="green"
          />
          <StatCard
            title="Toplam Peer"
            value={stats.total_peers}
            icon={<Globe size={32} />}
            neonColor="cyan"
          />
          <StatCard
            title="Indirilen"
            value={formatBytes(stats.total_transfer_rx)}
            icon={<Download size={32} />}
            neonColor="magenta"
          />
          <StatCard
            title="Gönderilen"
            value={formatBytes(stats.total_transfer_tx)}
            icon={<Upload size={32} />}
            neonColor="amber"
          />
        </div>
      )}

      {/* Peer Listesi Baslik */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">
          VPN Peerleri ({peers.length})
        </h3>
        <button
          onClick={() => {
            setNewPeerName("");
            setAddPeerOpen(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
        >
          <Plus size={16} />
          Peer Ekle
        </button>
      </div>

      {/* Peer Listesi Tablosu */}
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-glass-border">
                <th className="pb-3 pr-4">Peer Adi</th>
                <th className="pb-3 pr-4">Durum</th>
                <th className="pb-3 pr-4">Adres</th>
                <th className="pb-3 pr-4">Endpoint</th>
                <th className="pb-3 pr-4">Son Handshake</th>
                <th className="pb-3 pr-4">Transfer</th>
                <th className="pb-3 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {peers.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    WireGuard config dizininde peer bulunamadı
                  </td>
                </tr>
              )}
              {peers.map((peer) => (
                <tr
                  key={peer.name}
                  className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                >
                  {/* Peer Adi */}
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <Globe size={14} className="text-neon-cyan" />
                      <span className="font-medium text-white">
                        {peer.name}
                      </span>
                    </div>
                  </td>

                  {/* Durum */}
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${peer.is_connected ? 'bg-neon-green animate-pulse' : 'bg-gray-600'}`} />
                      <span className={`text-xs ${peer.is_connected ? 'text-neon-green' : 'text-gray-500'}`}>
                        {peer.is_connected ? "Bagli" : "Çevrimdışı"}
                      </span>
                    </div>
                  </td>

                  {/* Adres (Allowed IPs) */}
                  <td className="py-3 pr-4 font-mono text-xs text-gray-300">
                    {peer.allowed_ips || "--"}
                  </td>

                  {/* Endpoint */}
                  <td className="py-3 pr-4 font-mono text-xs text-gray-300">
                    {peer.endpoint || "--"}
                  </td>

                  {/* Son Handshake */}
                  <td className="py-3 pr-4 text-xs text-gray-400">
                    {peer.last_handshake && peer.last_handshake !== "0"
                      ? peer.last_handshake
                      : "--"}
                  </td>

                  {/* Transfer */}
                  <td className="py-3 pr-4 text-xs">
                    {(peer.transfer_rx > 0 || peer.transfer_tx > 0) ? (
                      <div className="space-y-0.5">
                        <span className="text-pink-400">{"\u2193"} {formatBytes(peer.transfer_rx)}</span>
                        <span className="text-cyan-400 ml-2">{"\u2191"} {formatBytes(peer.transfer_tx)}</span>
                      </div>
                    ) : (
                      <span className="text-gray-600">--</span>
                    )}
                  </td>

                  {/* İşlemler */}
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleShowConfig(peer.name)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-neon-cyan bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 rounded-lg transition-all"
                        title="Config Goster / Indir"
                      >
                        <Download size={13} />
                        Config
                      </button>
                      <button
                        onClick={() => handleRemovePeer(peer.name)}
                        className="p-1.5 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                        title="Peer'i Sil"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Kullanım Bilgisi */}
      <GlassCard>
        <div className="flex items-start gap-3">
          <Key size={18} className="text-neon-cyan mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-2">
              Nasil Baglanilir?
            </h4>
            <ol className="text-xs text-gray-400 space-y-1.5 list-decimal list-inside">
              <li>
                Telefonunuza veya bilgisayarınıza{" "}
                <span className="text-white">WireGuard uygulamasini</span>{" "}
                indirin
              </li>
              <li>
                Yukaridaki listeden kendinize ait peer'in{" "}
                <span className="text-white">Config</span> butonuna tiklayin
              </li>
              <li>
                <span className="text-white">.conf dosyasini indirin</span> veya{" "}
                <span className="text-white">QR kodu</span> tarayin
              </li>
              <li>
                WireGuard uygulamasında "Tünel Ekle" seçeneğiyle config'i
                yükleyin
              </li>
              <li>
                Bağlantıyı aktive edin - artık ev ağınıza uzaktan erişebilirsiniz
              </li>
            </ol>
          </div>
        </div>
      </GlassCard>

      {/* Peer Ekle Modal */}
      {addPeerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setAddPeerOpen(false)}
          />
          <div className="relative w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Plus size={18} className="text-neon-cyan" />
                <h3 className="text-base font-semibold text-white">
                  Yeni VPN Peer Ekle
                </h3>
              </div>
              <button
                onClick={() => setAddPeerOpen(false)}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-gray-400 mb-4">
              Peer adı giriniz. WireGuard anahtarları otomatik oluşturulacaktır.
              Oluşturulan config bir kere gösterilir, kaydetmeyi unutmayın.
            </p>

            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">
                Peer Adi <span className="text-neon-red">*</span>
              </label>
              <input
                type="text"
                value={newPeerName}
                onChange={(e) => setNewPeerName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddPeer()}
                placeholder="örn. telefon, laptop, tablet"
                className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setAddPeerOpen(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Iptal
              </button>
              <button
                onClick={handleAddPeer}
                disabled={addingPeer || !newPeerName.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addingPeer ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                ) : (
                  <Plus size={14} />
                )}
                Peer Oluştur
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Peer Config Modal */}
      {configModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Overlay */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setConfigModal(null)}
          />

          {/* Modal */}
          <div className="relative w-full max-w-xl bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl p-6 shadow-2xl">
            {/* Baslik */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Key size={18} className="text-neon-cyan" />
                <h3 className="text-base font-semibold text-white">
                  WireGuard Config: {configModal.peer_name}
                </h3>
              </div>
              <button
                onClick={() => setConfigModal(null)}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              >
                <X size={18} />
              </button>
            </div>

            {/* Açıklama */}
            <p className="text-xs text-gray-400 mb-3">
              Bu yapılandırmayı WireGuard istemcisine kopyalayın, .conf dosyasi
              olarak kaydedin veya QR kodu tarayın.
            </p>

            {/* Config Code Block */}
            <div className="relative">
              <pre className="bg-surface-800 border border-glass-border rounded-xl p-4 text-xs font-mono text-neon-green overflow-x-auto whitespace-pre leading-relaxed max-h-60 overflow-y-auto">
                {configModal.config_text}
              </pre>

              {/* Kopyala Butonu */}
              <button
                onClick={handleCopyConfig}
                className={`absolute top-2 right-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
                  copied
                    ? "bg-neon-green/10 text-neon-green border border-neon-green/30"
                    : "bg-white/5 text-gray-400 border border-white/10 hover:text-white hover:bg-white/10"
                }`}
              >
                {copied ? (
                  <>
                    <Check size={12} />
                    Kopyalandi
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Kopyala
                  </>
                )}
              </button>
            </div>

            {/* QR Kodu */}
            {configModal.qr_data && (
              <div className="mt-4 flex flex-col items-center">
                <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                  <QrCode size={14} />
                  QR Kodu ile Bağlan
                </p>
                <div className="bg-white p-3 rounded-xl">
                  <img
                    src={`data:image/png;base64,${configModal.qr_data}`}
                    alt={`${configModal.peer_name} QR`}
                    className="w-48 h-48"
                  />
                </div>
              </div>
            )}

            {/* Modal Altligi */}
            <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-glass-border">
              <button
                onClick={() => setConfigModal(null)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Kapat
              </button>
              <button
                onClick={handleDownloadConfig}
                className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
              >
                <Download size={14} />
                .conf Indir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
