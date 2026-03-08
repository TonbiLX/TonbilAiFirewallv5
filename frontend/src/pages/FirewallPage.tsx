// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// Güvenlik Duvarı sayfası: kural yönetimi, aktif bağlantılar, port tarama, istatistikler

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Shield,
  ShieldOff,
  ShieldAlert,
  Plus,
  Trash2,
  Search,
  Wifi,
  Pencil,
  Filter,
  X,
  Globe,
  RefreshCw,
  ArrowUpDown,
  Fingerprint,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import { DdosProtectionTab } from "../components/firewall/DdosProtectionTab";
import { SecuritySettingsTab } from "../components/firewall/SecuritySettingsTab";
import { IpReputationTab } from "../components/firewall/IpReputationTab";
import {
  fetchFirewallRules,
  createFirewallRule,
  updateFirewallRule,
  deleteFirewallRule,
  toggleFirewallRule,
  scanPorts,
  fetchFirewallStats,
  fetchActiveConnections,
  fetchConnectionCount,
} from "../services/firewallApi";
import type {
  FirewallRule,
  FirewallStats,
  PortScanResult,
  ActiveConnection,
} from "../types";

interface RuleForm {
  name: string;
  description: string;
  direction: "inbound" | "outbound" | "forward";
  protocol: "tcp" | "udp" | "both" | "icmp" | "all";
  port: string;
  port_end: string;
  source_ip: string;
  dest_ip: string;
  action: "accept" | "drop" | "reject";
  priority: string;
  log_packets: boolean;
}

const emptyForm: RuleForm = {
  name: "",
  description: "",
  direction: "inbound",
  protocol: "tcp",
  port: "",
  port_end: "",
  source_ip: "",
  dest_ip: "",
  action: "drop",
  priority: "100",
  log_packets: false,
};

type ActiveTab = "rules" | "connections" | "scanner" | "ddos" | "security" | "reputation";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function FirewallPage() {
  const { connected } = useWebSocket();
  const [rules, setRules] = useState<FirewallRule[]>([]);
  const [stats, setStats] = useState<FirewallStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("rules");

  // Add/Edit Rule form
  const [showForm, setShowForm] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [form, setForm] = useState<RuleForm>(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  // Search & filter
  const [searchText, setSearchText] = useState("");
  const [filterDirection, setFilterDirection] = useState<string>("all");

  // Active connections
  const [connections, setConnections] = useState<ActiveConnection[]>([]);
  const [connCount, setConnCount] = useState<{
    active: number;
    max: number;
  } | null>(null);
  const [connLoading, setConnLoading] = useState(false);
  const [connFilter, setConnFilter] = useState("");

  // Port scanner
  const [scanTarget, setScanTarget] = useState("192.168.1.1");
  const [scanPortRange, setScanPortRange] = useState("1-1024");
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState<PortScanResult[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [rulesRes, statsRes] = await Promise.all([
        fetchFirewallRules(),
        fetchFirewallStats(),
      ]);
      setRules(rulesRes.data);
      setStats(statsRes.data);
      setError(null);
    } catch (err) {
      setError("Güvenlik duvarı verileri yüklenemedi");
      console.error("Firewall veri yükleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConnections = useCallback(async () => {
    setConnLoading(true);
    try {
      const [connRes, countRes] = await Promise.all([
        fetchActiveConnections(),
        fetchConnectionCount(),
      ]);
      const connData = connRes.data;
      setConnections(Array.isArray(connData) ? connData : connData.connections || []);
      setConnCount(countRes.data);
    } catch (err) {
      console.error("Bağlantı verileri yüklenemedi:", err);
    } finally {
      setConnLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Load connections when tab is active
  useEffect(() => {
    if (activeTab === "connections") {
      loadConnections();
      const interval = setInterval(loadConnections, 10000);
      return () => clearInterval(interval);
    }
  }, [activeTab, loadConnections]);

  // Merge nftables hit counts into rules
  const rulesWithHits = useMemo(() => {
    if (!stats?.rule_hit_counts) return rules;
    return rules.map((rule) => {
      const hit = stats.rule_hit_counts?.[rule.id];
      if (hit) {
        return { ...rule, hit_count: hit.packets };
      }
      return rule;
    });
  }, [rules, stats]);

  // Filtered rules
  const filteredRules = useMemo(() => {
    let filtered = rulesWithHits;
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          (r.description && r.description.toLowerCase().includes(q)) ||
          (r.source_ip && r.source_ip.includes(q)) ||
          (r.dest_ip && r.dest_ip.includes(q)) ||
          (r.port && String(r.port).includes(q))
      );
    }
    if (filterDirection !== "all") {
      filtered = filtered.filter((r) => r.direction === filterDirection);
    }
    return filtered;
  }, [rulesWithHits, searchText, filterDirection]);

  // Filtered connections
  const filteredConnections = useMemo(() => {
    if (!connFilter.trim()) return connections;
    const q = connFilter.toLowerCase();
    return connections.filter(
      (c) =>
        c.src_ip.includes(q) ||
        c.dst_ip.includes(q) ||
        (c.dst_domain && c.dst_domain.toLowerCase().includes(q)) ||
        String(c.dst_port).includes(q) ||
        c.protocol.toLowerCase().includes(q) ||
        c.state.toLowerCase().includes(q)
    );
  }, [connections, connFilter]);

  const handleAddRule = async () => {
    if (!form.name.trim()) return;
    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        direction: form.direction,
        protocol: form.protocol,
        action: form.action,
        priority: parseInt(form.priority, 10) || 100,
        log_packets: form.log_packets,
      };
      if (form.port) payload.port = parseInt(form.port, 10);
      if (form.port_end) payload.port_end = parseInt(form.port_end, 10);
      if (form.source_ip.trim()) payload.source_ip = form.source_ip.trim();
      if (form.dest_ip.trim()) payload.dest_ip = form.dest_ip.trim();

      await createFirewallRule(payload);
      setForm(emptyForm);
      setShowForm(false);
      await loadData();
    } catch (err) {
      console.error("Kural ekleme hatasi:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateRule = async () => {
    if (!form.name.trim() || editingRuleId === null) return;
    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        direction: form.direction,
        protocol: form.protocol,
        action: form.action,
        priority: parseInt(form.priority, 10) || 100,
        log_packets: form.log_packets,
      };
      if (form.port) payload.port = parseInt(form.port, 10);
      else payload.port = null;
      if (form.port_end) payload.port_end = parseInt(form.port_end, 10);
      else payload.port_end = null;
      payload.source_ip = form.source_ip.trim() || null;
      payload.dest_ip = form.dest_ip.trim() || null;

      await updateFirewallRule(editingRuleId, payload);
      setForm(emptyForm);
      setShowForm(false);
      setEditingRuleId(null);
      await loadData();
    } catch (err) {
      console.error("Kural güncelleme hatasi:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditRule = (rule: FirewallRule) => {
    setForm({
      name: rule.name,
      description: rule.description || "",
      direction: rule.direction,
      protocol: rule.protocol,
      port: rule.port ? String(rule.port) : "",
      port_end: rule.port_end ? String(rule.port_end) : "",
      source_ip: rule.source_ip || "",
      dest_ip: rule.dest_ip || "",
      action: rule.action,
      priority: String(rule.priority),
      log_packets: rule.log_packets,
    });
    setEditingRuleId(rule.id);
    setShowForm(true);
  };

  const handleCancelForm = () => {
    setForm(emptyForm);
    setShowForm(false);
    setEditingRuleId(null);
  };

  const handleDeleteRule = async (id: number) => {
    try {
      await deleteFirewallRule(id);
      await loadData();
    } catch (err) {
      console.error("Kural silme hatasi:", err);
    }
  };

  const handleToggleRule = async (id: number) => {
    try {
      await toggleFirewallRule(id);
      await loadData();
    } catch (err) {
      console.error("Kural toggle hatasi:", err);
    }
  };

  const handleScanPorts = async () => {
    if (!scanTarget.trim()) return;
    setScanning(true);
    setScanResults([]);
    try {
      const res = await scanPorts(scanTarget.trim(), scanPortRange.trim());
      setScanResults(res.data);
    } catch (err) {
      console.error("Port tarama hatasi:", err);
    } finally {
      setScanning(false);
    }
  };

  const updateForm = (field: keyof RuleForm, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) return <LoadingSpinner />;

  const inputClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors";
  const selectClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors";
  const labelClass =
    "block text-xs text-gray-400 mb-1 uppercase tracking-wider";

  const tabClass = (tab: ActiveTab) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-all ${
      activeTab === tab
        ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30"
        : "text-gray-400 hover:text-white hover:bg-glass-light"
    }`;

  return (
    <div className="space-y-6">
      <TopBar title="Güvenlik Duvarı" connected={connected} />

      {/* Hata mesaji */}
      {error && (
        <div className="bg-neon-red/10 border border-neon-red/30 rounded-xl p-4 text-neon-red text-sm">
          {error}
        </div>
      )}

      {/* İstatistik Kartlari */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard
            title="Toplam Kural"
            value={stats.total_rules}
            icon={<Shield size={32} />}
            neonColor="cyan"
          />
          <StatCard
            title="Aktif Kural"
            value={stats.active_rules}
            icon={<Shield size={32} />}
            neonColor="green"
          />
          <StatCard
            title="Engellenen Paket (24s)"
            value={stats.blocked_packets_24h.toLocaleString()}
            icon={<ShieldOff size={32} />}
            neonColor="magenta"
          />
          <StatCard
            title="Aktif Bağlantı"
            value={
              stats.active_connections !== undefined
                ? `${stats.active_connections.toLocaleString()} / ${(stats.max_connections || 0).toLocaleString()}`
                : "--"
            }
            icon={<Globe size={32} />}
            neonColor="amber"
          />
          <StatCard
            title="Açık Port"
            value={stats.open_ports.length}
            icon={<Wifi size={32} />}
            neonColor="cyan"
          />
        </div>
      )}

      {/* Açık Portlar Özeti */}
      {stats && stats.open_ports.length > 0 && (
        <GlassCard>
          <h4 className="text-sm font-semibold text-gray-300 mb-3">
            Açık Portlar
          </h4>
          <div className="flex flex-wrap gap-2">
            {stats.open_ports.map((port) => (
              <span
                key={port}
                className="px-2.5 py-1 bg-neon-amber/10 text-neon-amber border border-neon-amber/30 rounded-lg text-xs font-mono"
              >
                :{port}
              </span>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Tab Secici */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("rules")}
          className={tabClass("rules")}
        >
          <div className="flex items-center gap-2">
            <Shield size={16} />
            Kurallar
          </div>
        </button>
        <button
          onClick={() => setActiveTab("connections")}
          className={tabClass("connections")}
        >
          <div className="flex items-center gap-2">
            <Globe size={16} />
            Aktif Bağlantılar
            {connCount && (
              <span className="text-xs bg-glass-light px-1.5 py-0.5 rounded-md">
                {connCount.active.toLocaleString()}
              </span>
            )}
          </div>
        </button>
        <button
          onClick={() => setActiveTab("scanner")}
          className={tabClass("scanner")}
        >
          <div className="flex items-center gap-2">
            <Search size={16} />
            Port Tarayici
          </div>
        </button>
        <button
          onClick={() => setActiveTab("ddos")}
          className={tabClass("ddos")}
        >
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} />
            DDoS Koruma
          </div>
        </button>
        <button
          onClick={() => setActiveTab("security")}
          className={tabClass("security")}
        >
          <div className="flex items-center gap-2">
            <Shield size={16} />
            Güvenlik Ayarları
          </div>
        </button>
        <button
          onClick={() => setActiveTab("reputation")}
          className={tabClass("reputation")}
        >
          <div className="flex items-center gap-2">
            <Fingerprint size={16} />
            IP İtibar
          </div>
        </button>
      </div>

      {/* ===================== KURALLAR TAB ===================== */}
      {activeTab === "rules" && (
        <>
          {/* Arama + Filtre + Kural Ekle */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Arama */}
            <div className="flex-1 min-w-[200px] relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Kural ara (isim, IP, port)..."
                className="w-full bg-surface-800 border border-glass-border rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
              />
              {searchText && (
                <button
                  onClick={() => setSearchText("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Yon Filtresi */}
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-gray-500" />
              <select
                value={filterDirection}
                onChange={(e) => setFilterDirection(e.target.value)}
                className="bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors"
              >
                <option value="all">Tüm Yönler</option>
                <option value="inbound">Gelen</option>
                <option value="outbound">Giden</option>
                <option value="forward">Forward</option>
              </select>
            </div>

            {/* Kural Ekle Butonu */}
            <button
              onClick={() => {
                if (showForm && editingRuleId === null) {
                  handleCancelForm();
                } else {
                  setEditingRuleId(null);
                  setForm(emptyForm);
                  setShowForm(true);
                }
              }}
              className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
            >
              <Plus size={16} />
              {showForm && editingRuleId === null ? "Formu Kapat" : "Kural Ekle"}
            </button>
          </div>

          {/* Inline Kural Formu (Ekleme / Düzenleme) */}
          {showForm && (
            <GlassCard>
              <h4 className="text-sm font-semibold text-gray-300 mb-4">
                {editingRuleId !== null
                  ? "Kural Düzenle"
                  : "Yeni Güvenlik Duvarı Kuralı"}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Ad */}
                <div>
                  <label className={labelClass}>Kural Adi *</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => updateForm("name", e.target.value)}
                    placeholder="örnek: SSH Engelle"
                    className={inputClass}
                  />
                </div>

                {/* Açıklama */}
                <div>
                  <label className={labelClass}>Açıklama</label>
                  <input
                    type="text"
                    value={form.description}
                    onChange={(e) => updateForm("description", e.target.value)}
                    placeholder="Kural açıklaması..."
                    className={inputClass}
                  />
                </div>

                {/* Yon */}
                <div>
                  <label className={labelClass}>Yon</label>
                  <select
                    value={form.direction}
                    onChange={(e) => updateForm("direction", e.target.value)}
                    className={selectClass}
                  >
                    <option value="inbound">Gelen (Inbound)</option>
                    <option value="outbound">Giden (Outbound)</option>
                    <option value="forward">Yonlendirme (Forward)</option>
                  </select>
                </div>

                {/* Protokol */}
                <div>
                  <label className={labelClass}>Protokol</label>
                  <select
                    value={form.protocol}
                    onChange={(e) => updateForm("protocol", e.target.value)}
                    className={selectClass}
                  >
                    <option value="tcp">TCP</option>
                    <option value="udp">UDP</option>
                    <option value="both">TCP + UDP</option>
                    <option value="icmp">ICMP</option>
                    <option value="all">Tümü</option>
                  </select>
                </div>

                {/* Port */}
                <div>
                  <label className={labelClass}>Port (Başlangıç)</label>
                  <input
                    type="number"
                    value={form.port}
                    onChange={(e) => updateForm("port", e.target.value)}
                    placeholder="örnek: 22"
                    min={1}
                    max={65535}
                    className={inputClass}
                  />
                </div>

                {/* Port Bitiş */}
                <div>
                  <label className={labelClass}>
                    Port (Bitiş - Aralık için)
                  </label>
                  <input
                    type="number"
                    value={form.port_end}
                    onChange={(e) => updateForm("port_end", e.target.value)}
                    placeholder="örnek: 80"
                    min={1}
                    max={65535}
                    className={inputClass}
                  />
                </div>

                {/* Kaynak IP */}
                <div>
                  <label className={labelClass}>Kaynak IP</label>
                  <input
                    type="text"
                    value={form.source_ip}
                    onChange={(e) => updateForm("source_ip", e.target.value)}
                    placeholder="örnek: 192.168.1.0/24"
                    className={inputClass}
                  />
                </div>

                {/* Hedef IP */}
                <div>
                  <label className={labelClass}>Hedef IP</label>
                  <input
                    type="text"
                    value={form.dest_ip}
                    onChange={(e) => updateForm("dest_ip", e.target.value)}
                    placeholder="örnek: 10.0.0.1"
                    className={inputClass}
                  />
                </div>

                {/* Aksiyon */}
                <div>
                  <label className={labelClass}>Aksiyon</label>
                  <select
                    value={form.action}
                    onChange={(e) => updateForm("action", e.target.value)}
                    className={selectClass}
                  >
                    <option value="drop">Düşür (Drop)</option>
                    <option value="reject">Reddet (Reject)</option>
                    <option value="accept">Kabul Et (Accept)</option>
                  </select>
                </div>

                {/* Öncelik */}
                <div>
                  <label className={labelClass}>Öncelik</label>
                  <input
                    type="number"
                    value={form.priority}
                    onChange={(e) => updateForm("priority", e.target.value)}
                    placeholder="100"
                    min={1}
                    max={9999}
                    className={inputClass}
                  />
                </div>

                {/* Paket Loglama */}
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.log_packets}
                      onChange={(e) =>
                        updateForm("log_packets", e.target.checked)
                      }
                      className="w-4 h-4 rounded border-glass-border bg-surface-800 text-neon-cyan focus:ring-neon-cyan/50 accent-neon-cyan"
                    />
                    <span className="text-sm text-gray-300">
                      Paketleri Logla
                    </span>
                  </label>
                </div>
              </div>

              {/* Form Butonlari */}
              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-glass-border">
                <button
                  onClick={handleCancelForm}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Iptal
                </button>
                <button
                  onClick={
                    editingRuleId !== null ? handleUpdateRule : handleAddRule
                  }
                  disabled={!form.name.trim() || submitting}
                  className="flex items-center gap-2 px-6 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <div className="w-4 h-4 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
                  ) : editingRuleId !== null ? (
                    <Pencil size={16} />
                  ) : (
                    <Plus size={16} />
                  )}
                  {editingRuleId !== null ? "Güncelle" : "Kural Oluştur"}
                </button>
              </div>
            </GlassCard>
          )}

          {/* Kural Sayısı */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm text-gray-400">
              {filteredRules.length === rulesWithHits.length
                ? `${rulesWithHits.length} kural`
                : `${filteredRules.length} / ${rulesWithHits.length} kural`}
            </h3>
          </div>

          {/* Kural Tablosu */}
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-glass-border">
                    <th className="pb-3 pr-4">Kural Adi</th>
                    <th className="pb-3 pr-4">Yon</th>
                    <th className="pb-3 pr-4">Protokol</th>
                    <th className="pb-3 pr-4">Port</th>
                    <th className="pb-3 pr-4">Kaynak IP</th>
                    <th className="pb-3 pr-4">Hedef IP</th>
                    <th className="pb-3 pr-4">Aksiyon</th>
                    <th className="pb-3 pr-4">Durum</th>
                    <th className="pb-3 pr-4">
                      <div className="flex items-center gap-1">
                        Hit
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th className="pb-3 text-right">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRules.length === 0 && (
                    <tr>
                      <td
                        colSpan={10}
                        className="py-8 text-center text-gray-500"
                      >
                        {searchText || filterDirection !== "all"
                          ? "Filtreye uyan kural bulunamadı"
                          : "Henüz güvenlik duvarı kuralı eklenmemiş"}
                      </td>
                    </tr>
                  )}
                  {filteredRules.map((rule) => (
                    <tr
                      key={rule.id}
                      className={`border-b border-glass-border/50 hover:bg-glass-light transition-colors ${
                        !rule.enabled ? "opacity-50" : ""
                      }`}
                    >
                      {/* Kural Adi */}
                      <td className="py-2.5 pr-4">
                        <div>
                          <p className="font-medium text-white">{rule.name}</p>
                          {rule.description && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              {rule.description}
                            </p>
                          )}
                        </div>
                      </td>

                      {/* Yon */}
                      <td className="py-2.5 pr-4">
                        <NeonBadge
                          label={
                            rule.direction === "inbound"
                              ? "GELEN"
                              : rule.direction === "outbound"
                              ? "GİDEN"
                              : "FORWARD"
                          }
                          variant={
                            rule.direction === "inbound"
                              ? "cyan"
                              : rule.direction === "outbound"
                              ? "magenta"
                              : "amber"
                          }
                        />
                      </td>

                      {/* Protokol */}
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-300 uppercase">
                        {rule.protocol}
                      </td>

                      {/* Port */}
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-300">
                        {rule.port
                          ? rule.port_end
                            ? `${rule.port}-${rule.port_end}`
                            : rule.port
                          : "*"}
                      </td>

                      {/* Kaynak IP */}
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-300">
                        {rule.source_ip || "*"}
                      </td>

                      {/* Hedef IP */}
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-300">
                        {rule.dest_ip || "*"}
                      </td>

                      {/* Aksiyon */}
                      <td className="py-2.5 pr-4">
                        <NeonBadge
                          label={
                            rule.action === "accept"
                              ? "KABUL"
                              : rule.action === "drop"
                              ? "DÜŞÜR"
                              : "REDDET"
                          }
                          variant={
                            rule.action === "accept"
                              ? "green"
                              : rule.action === "reject"
                              ? "amber"
                              : "red"
                          }
                        />
                      </td>

                      {/* Durum Toggle */}
                      <td className="py-2.5 pr-4">
                        <button
                          onClick={() => handleToggleRule(rule.id)}
                          className={`relative w-10 h-5 rounded-full transition-colors ${
                            rule.enabled ? "bg-neon-green/30" : "bg-gray-700"
                          }`}
                        >
                          <span
                            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full transition-transform ${
                              rule.enabled
                                ? "translate-x-5 bg-neon-green shadow-[0_0_8px_rgba(57,255,20,0.5)]"
                                : "bg-gray-500"
                            }`}
                          />
                        </button>
                      </td>

                      {/* Hit Count */}
                      <td className="py-2.5 pr-4 font-mono text-xs text-gray-400">
                        {rule.hit_count > 0 ? (
                          <span className="text-neon-amber">
                            {rule.hit_count.toLocaleString()}
                          </span>
                        ) : (
                          "0"
                        )}
                      </td>

                      {/* Düzenle + Sil */}
                      <td className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleEditRule(rule)}
                            className="p-1.5 text-gray-500 hover:text-neon-cyan hover:bg-neon-cyan/10 rounded-lg transition-all"
                            title="Kuralı Düzenle"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteRule(rule.id)}
                            className="p-1.5 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                            title="Kuralı Sil"
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
        </>
      )}

      {/* ===================== AKTIF BAGLANTILAR TAB ===================== */}
      {activeTab === "connections" && (
        <>
          {/* Bağlantı Özeti */}
          {connCount && (
            <GlassCard>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">
                      Aktif Bağlantı
                    </p>
                    <p className="text-2xl font-bold text-white mt-1">
                      {connCount.active.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">
                      Maksimum
                    </p>
                    <p className="text-2xl font-bold text-gray-400 mt-1">
                      {connCount.max.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">
                      Kullanım
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <div className="w-32 h-2 bg-surface-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-neon-cyan rounded-full transition-all"
                          style={{
                            width: `${Math.min(
                              (connCount.active / connCount.max) * 100,
                              100
                            )}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-mono text-neon-cyan">
                        %
                        {((connCount.active / connCount.max) * 100).toFixed(1)}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={loadConnections}
                  disabled={connLoading}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-glass-light rounded-lg transition-all"
                >
                  <RefreshCw
                    size={14}
                    className={connLoading ? "animate-spin" : ""}
                  />
                  Yenile
                </button>
              </div>
            </GlassCard>
          )}

          {/* Bağlantı Filtresi */}
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
            />
            <input
              type="text"
              value={connFilter}
              onChange={(e) => setConnFilter(e.target.value)}
              placeholder="Bağlantı filtrele (IP, domain, port, protokol, durum)..."
              className="w-full bg-surface-800 border border-glass-border rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
            />
            {connFilter && (
              <button
                onClick={() => setConnFilter("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Sonuç Sayısı */}
          <div className="text-sm text-gray-400">
            {connFilter
              ? `${filteredConnections.length} / ${connections.length} bağlantı`
              : `${connections.length} bağlantı`}
          </div>

          {/* Bağlantı Tablosu */}
          <GlassCard>
            {connLoading && connections.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
                  <span className="text-sm text-gray-400">
                    Bağlantılar yükleniyor...
                  </span>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-glass-border">
                      <th className="pb-3 pr-4">Protokol</th>
                      <th className="pb-3 pr-4">Kaynak</th>
                      <th className="pb-3 pr-4">Hedef</th>
                      <th className="pb-3 pr-4">Domain</th>
                      <th className="pb-3 pr-4">Gönderilen</th>
                      <th className="pb-3 pr-4">Alinan</th>
                      <th className="pb-3">Durum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredConnections.length === 0 && (
                      <tr>
                        <td
                          colSpan={7}
                          className="py-8 text-center text-gray-500"
                        >
                          {connFilter
                            ? "Filtreye uyan bağlantı bulunamadı"
                            : "Aktif bağlantı yok"}
                        </td>
                      </tr>
                    )}
                    {filteredConnections.slice(0, 200).map((conn, idx) => (
                      <tr
                        key={`${conn.protocol}-${conn.src_ip}-${conn.src_port}-${conn.dst_ip}-${conn.dst_port}-${idx}`}
                        className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                      >
                        <td className="py-2 pr-4">
                          <span className="font-mono text-xs uppercase px-1.5 py-0.5 rounded bg-glass-light text-gray-300">
                            {conn.protocol}
                          </span>
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-300">
                          {conn.src_ip}
                          <span className="text-gray-600">
                            :{conn.src_port}
                          </span>
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-300">
                          {conn.dst_ip}
                          <span className="text-gray-600">
                            :{conn.dst_port}
                          </span>
                        </td>
                        <td className="py-2 pr-4 text-xs text-neon-cyan truncate max-w-[200px]">
                          {conn.dst_domain || (
                            <span className="text-gray-600">--</span>
                          )}
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-400">
                          {formatBytes(conn.bytes_sent)}
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-400">
                          {formatBytes(conn.bytes_received)}
                        </td>
                        <td className="py-2">
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              conn.state === "ESTABLISHED"
                                ? "bg-neon-green/10 text-neon-green"
                                : conn.state === "TIME_WAIT"
                                ? "bg-neon-amber/10 text-neon-amber"
                                : conn.state === "SYN_SENT" ||
                                  conn.state === "SYN_RECV"
                                ? "bg-neon-cyan/10 text-neon-cyan"
                                : "bg-glass-light text-gray-400"
                            }`}
                          >
                            {conn.state}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredConnections.length > 200 && (
                  <p className="text-xs text-gray-500 text-center mt-3">
                    İlk 200 bağlantı gösteriliyor (toplam:{" "}
                    {filteredConnections.length})
                  </p>
                )}
              </div>
            )}
          </GlassCard>
        </>
      )}

      {/* ===================== PORT TARAYICI TAB ===================== */}
      {activeTab === "scanner" && (
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Search size={18} className="text-neon-magenta" />
            <h4 className="text-sm font-semibold text-gray-300">
              Port Tarayici
            </h4>
          </div>

          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex-1 min-w-[180px]">
              <label className={labelClass}>Hedef IP</label>
              <input
                type="text"
                value={scanTarget}
                onChange={(e) => setScanTarget(e.target.value)}
                placeholder="192.168.1.1"
                className={inputClass}
              />
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className={labelClass}>Port Aralığı</label>
              <input
                type="text"
                value={scanPortRange}
                onChange={(e) => setScanPortRange(e.target.value)}
                placeholder="1-1024"
                className={inputClass}
              />
            </div>
            <button
              onClick={handleScanPorts}
              disabled={scanning || !scanTarget.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-neon-magenta/10 hover:bg-neon-magenta/20 border border-neon-magenta/30 text-neon-magenta rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {scanning ? (
                <div className="w-4 h-4 border-2 border-neon-magenta/30 border-t-neon-magenta rounded-full animate-spin" />
              ) : (
                <Search size={16} />
              )}
              {scanning ? "Taraniyor..." : "Tarama Başlat"}
            </button>
          </div>

          {/* Tarama Sonuçlari */}
          {scanResults.length > 0 && (
            <div className="mt-6">
              <h5 className="text-xs text-gray-400 uppercase tracking-wider mb-3">
                Tarama Sonuçlari ({scanResults.length} port)
              </h5>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-glass-border">
                      <th className="pb-2 pr-4">Port</th>
                      <th className="pb-2 pr-4">Protokol</th>
                      <th className="pb-2 pr-4">Durum</th>
                      <th className="pb-2">Servis</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scanResults.map((result) => (
                      <tr
                        key={`${result.port}-${result.protocol}`}
                        className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                      >
                        <td className="py-2 pr-4 font-mono text-neon-cyan">
                          {result.port}
                        </td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-300 uppercase">
                          {result.protocol}
                        </td>
                        <td className="py-2 pr-4">
                          <NeonBadge
                            label={
                              result.state === "open"
                                ? "ACIK"
                                : result.state === "closed"
                                ? "KAPALI"
                                : "FILTRELI"
                            }
                            variant={
                              result.state === "open"
                                ? "green"
                                : result.state === "closed"
                                ? "red"
                                : "amber"
                            }
                          />
                        </td>
                        <td className="py-2 text-xs text-gray-400">
                          {result.service || "--"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {scanning && (
            <div className="mt-6 flex items-center justify-center py-8">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-neon-magenta/30 border-t-neon-magenta rounded-full animate-spin" />
                <span className="text-sm text-gray-400">
                  Portlar taranıyor... Lütfen bekleyin.
                </span>
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* ===================== DDOS KORUMA TAB ===================== */}
      {activeTab === "ddos" && <DdosProtectionTab />}

      {/* ===================== GÜVENLİK AYARLARI TAB ===================== */}
      {activeTab === "security" && <SecuritySettingsTab />}

      {/* ===================== IP ITIBAR TAB ===================== */}
      {activeTab === "reputation" && <IpReputationTab />}
    </div>
  );
}
