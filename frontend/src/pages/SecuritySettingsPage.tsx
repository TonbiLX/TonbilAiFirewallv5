// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Guvenlik Ayarlari Sayfasi: 5 tab, cyberpunk glassmorphism UI

import { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert, Globe, Bell, ShieldCheck, Activity,
  Save, RefreshCw, RotateCcw, Trash2, Plus, Check,
  Lock, Search, Shield,
} from "lucide-react";
import { GlassCard } from "../components/common/GlassCard";
import { StatCard } from "../components/common/StatCard";
import {
  fetchSecurityConfig,
  updateSecurityConfig,
  resetSecurityConfig,
  fetchSecurityStats,
} from "../services/securityApi";
import {
  fetchTrustedIps,
  addTrustedIp,
  deleteTrustedIp,
} from "../services/ipManagementApi";
import type { SecurityConfig, SecurityStats, TrustedIp } from "../types";

const TABS = [
  { id: "threat", label: "Tehdit Analizi", icon: ShieldAlert },
  { id: "dns", label: "DNS Güvenlik", icon: Globe },
  { id: "alerts", label: "Uyarı Ayarları", icon: Bell },
  { id: "trusted", label: "Güvenilir IP'ler", icon: ShieldCheck },
  { id: "stats", label: "Canlı İstatistikler", icon: Activity },
] as const;

type TabId = (typeof TABS)[number]["id"];

const QTYPE_OPTIONS = [
  { value: 10, label: "NULL (10)" },
  { value: 11, label: "WKS (11)" },
  { value: 13, label: "HINFO (13)" },
  { value: 252, label: "AXFR (252)" },
  { value: 255, label: "ANY (255)" },
];

export function SecuritySettingsPage() {
  const [tab, setTab] = useState<TabId>("threat");
  const [config, setConfig] = useState<SecurityConfig | null>(null);
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [trustedIps, setTrustedIps] = useState<TrustedIp[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [newIp, setNewIp] = useState("");
  const [newIpDesc, setNewIpDesc] = useState("");

  // Form state (local copy for editing)
  const [form, setForm] = useState<Partial<SecurityConfig>>({});

  const loadConfig = useCallback(async () => {
    try {
      const { data } = await fetchSecurityConfig();
      setConfig(data);
      setForm(data);
    } catch {
      /* ignore */
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const { data } = await fetchSecurityStats();
      setStats(data);
    } catch {
      /* ignore */
    }
  }, []);

  const loadTrustedIps = useCallback(async () => {
    try {
      const { data } = await fetchTrustedIps();
      setTrustedIps(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadConfig(), loadStats(), loadTrustedIps()]);
      setLoading(false);
    })();
  }, [loadConfig, loadStats, loadTrustedIps]);

  // Stats auto-refresh (10s)
  useEffect(() => {
    if (tab !== "stats") return;
    const iv = setInterval(loadStats, 10000);
    return () => clearInterval(iv);
  }, [tab, loadStats]);

  const showFeedback = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleSave = async (fields: Partial<SecurityConfig>) => {
    setSaving(true);
    try {
      // Convert dns_blocked_qtypes array to CSV string for backend
      const payload: Record<string, unknown> = { ...fields };
      if (Array.isArray(payload.dns_blocked_qtypes)) {
        payload.dns_blocked_qtypes = (payload.dns_blocked_qtypes as number[]).join(",");
      }
      const { data } = await updateSecurityConfig(payload);
      setConfig(data);
      setForm(data);
      showFeedback("Ayarlar kaydedildi");
    } catch {
      showFeedback("Kaydetme hatası!");
    }
    setSaving(false);
  };

  const handleReset = async () => {
    if (!confirm("Tüm güvenlik ayarları varsayılana dönecek. Emin misiniz?")) return;
    setSaving(true);
    try {
      const { data } = await resetSecurityConfig();
      setConfig(data);
      setForm(data);
      showFeedback("Varsayılana döndürüldü");
    } catch {
      showFeedback("Sıfırlama hatası!");
    }
    setSaving(false);
  };

  const handleAddTrustedIp = async () => {
    if (!newIp.trim()) return;
    try {
      await addTrustedIp({ ip_address: newIp.trim(), description: newIpDesc.trim() || undefined });
      setNewIp("");
      setNewIpDesc("");
      await loadTrustedIps();
      showFeedback("IP eklendi");
    } catch {
      showFeedback("IP ekleme hatası!");
    }
  };

  const handleDeleteTrustedIp = async (id: number) => {
    try {
      await deleteTrustedIp(id);
      await loadTrustedIps();
      showFeedback("IP silindi");
    } catch {
      showFeedback("Silme hatası!");
    }
  };

  const updateForm = (key: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-neon-cyan" size={32} />
      </div>
    );
  }

  const InputField = ({
    label,
    field,
    type = "number",
    min,
    max,
    step,
    suffix,
  }: {
    label: string;
    field: string;
    type?: string;
    min?: number;
    max?: number;
    step?: number;
    suffix?: string;
  }) => (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type={type}
          min={min}
          max={max}
          step={step}
          value={(form as Record<string, unknown>)[field] as string | number ?? ""}
          onChange={(e) =>
            updateForm(field, type === "number" ? Number(e.target.value) : e.target.value)
          }
          className="w-full bg-black/30 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-neon-cyan focus:outline-none"
        />
        {suffix && <span className="text-xs text-gray-500 whitespace-nowrap">{suffix}</span>}
      </div>
    </div>
  );

  const ToggleField = ({ label, field, desc }: { label: string; field: string; desc?: string }) => (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-sm text-white">{label}</p>
        {desc && <p className="text-xs text-gray-500">{desc}</p>}
      </div>
      <button
        onClick={() => updateForm(field, !(form as Record<string, unknown>)[field])}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          (form as Record<string, unknown>)[field] ? "bg-neon-green/30 border-neon-green" : "bg-gray-700 border-gray-600"
        } border`}
      >
        <span
          className={`absolute left-0 top-0.5 w-5 h-5 rounded-full transition-transform ${
            (form as Record<string, unknown>)[field]
              ? "translate-x-6 bg-neon-green"
              : "translate-x-0.5 bg-gray-400"
          }`}
        />
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-neon-cyan" size={28} />
            Güvenlik Ayarları
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Tehdit analizi, DNS güvenlik ve uyarı eşiklerini yönetin
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle badges */}
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.dga_detection_enabled ? "bg-neon-green/20 text-neon-green border border-neon-green/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            DGA
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.subnet_flood_enabled ? "bg-neon-green/20 text-neon-green border border-neon-green/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            Subnet
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.scan_pattern_enabled ? "bg-neon-green/20 text-neon-green border border-neon-green/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            Tarama
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.dnssec_enabled ? "bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            DNSSEC
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.dns_tunneling_enabled ? "bg-neon-magenta/20 text-neon-magenta border border-neon-magenta/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            Tunneling
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${form.doh_enabled ? "bg-neon-green/20 text-neon-green border border-neon-green/30" : "bg-gray-700 text-gray-400 border border-gray-600"}`}>
            DoH
          </span>
          {stats && (
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-neon-red/20 text-neon-red border border-neon-red/30">
              {stats.blocked_ip_count} Engelli IP
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-neon-amber/10 text-neon-amber border border-neon-amber/30 hover:bg-neon-amber/20 transition-colors"
          >
            <RotateCcw size={14} />
            Varsayılana Dön
          </button>
        </div>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm">
          <Check size={16} />
          {feedback}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-glass-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
              tab === t.id
                ? "border-neon-cyan text-neon-cyan"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            <t.icon size={16} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "threat" && (
        <GlassCard>
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white">Tehdit Analizi Ayarları</h2>

            {/* Rate thresholds */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <InputField label="Dış IP Sorgu/dk Eşiği" field="external_rate_threshold" min={1} max={1000} suffix="sorgu/dk" />
              <InputField label="Yerel Cihaz Sorgu/dk Eşiği" field="local_rate_threshold" min={10} max={5000} suffix="sorgu/dk" />
              <InputField label="Otomatik Engel Süresi" field="block_duration_sec" min={60} max={86400} suffix="saniye" />
            </div>

            {/* DGA */}
            <div className="border-t border-glass-border pt-4">
              <ToggleField label="DGA Algılama" field="dga_detection_enabled" desc="Rastgele üretilmiş domain tespiti (Shannon entropi)" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                <InputField label="Entropi Eşiği" field="dga_entropy_threshold" min={2.0} max={5.0} step={0.1} />
              </div>
            </div>

            {/* Subnet flood */}
            <div className="border-t border-glass-border pt-4">
              <ToggleField label="Subnet Flood Tespiti" field="subnet_flood_enabled" desc="/24 alt ağından koordineli sorgu tespiti" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                <InputField label="Benzersiz IP Eşiği" field="subnet_flood_threshold" min={2} max={50} suffix="IP" />
                <InputField label="İzleme Penceresi" field="subnet_window_sec" min={60} max={3600} suffix="saniye" />
                <InputField label="Subnet Engel Süresi" field="subnet_block_duration_sec" min={60} max={86400} suffix="saniye" />
              </div>
            </div>

            {/* Scan pattern */}
            <div className="border-t border-glass-border pt-4">
              <ToggleField label="Tarama Pattern Tespiti" field="scan_pattern_enabled" desc="Aynı hedef+qtype'a farklı IP'lerden gelen sorguları tespit" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                <InputField label="Farklı IP Eşiği" field="scan_pattern_threshold" min={2} max={50} suffix="IP" />
                <InputField label="İzleme Penceresi" field="scan_pattern_window_sec" min={60} max={3600} suffix="saniye" />
              </div>
            </div>

            {/* Threat score */}
            <div className="border-t border-glass-border pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InputField label="Otomatik Engel Skor Eşiği" field="threat_score_auto_block" min={5} max={100} suffix="puan" />
                <InputField label="Skor Birikim Penceresi" field="threat_score_ttl" min={300} max={86400} suffix="saniye" />
              </div>
            </div>

            {/* Cooldowns */}
            <div className="border-t border-glass-border pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InputField label="Insight Cooldown" field="insight_cooldown_sec" min={60} max={7200} suffix="saniye" />
                <InputField label="Toplu Uyarı Cooldown" field="aggregated_cooldown_sec" min={60} max={7200} suffix="saniye" />
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => handleSave({
                  external_rate_threshold: form.external_rate_threshold,
                  local_rate_threshold: form.local_rate_threshold,
                  block_duration_sec: form.block_duration_sec,
                  dga_detection_enabled: form.dga_detection_enabled,
                  dga_entropy_threshold: form.dga_entropy_threshold,
                  insight_cooldown_sec: form.insight_cooldown_sec,
                  subnet_flood_enabled: form.subnet_flood_enabled,
                  subnet_flood_threshold: form.subnet_flood_threshold,
                  subnet_window_sec: form.subnet_window_sec,
                  subnet_block_duration_sec: form.subnet_block_duration_sec,
                  scan_pattern_enabled: form.scan_pattern_enabled,
                  scan_pattern_threshold: form.scan_pattern_threshold,
                  scan_pattern_window_sec: form.scan_pattern_window_sec,
                  threat_score_auto_block: form.threat_score_auto_block,
                  threat_score_ttl: form.threat_score_ttl,
                  aggregated_cooldown_sec: form.aggregated_cooldown_sec,
                })}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/20 transition-colors disabled:opacity-50"
              >
                <Save size={16} />
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </div>
        </GlassCard>
      )}

      {tab === "dns" && (
        <GlassCard>
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white">DNS Güvenlik Ayarları</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InputField label="Rate Limit (sorgu/sn)" field="dns_rate_limit_per_sec" min={1} max={100} suffix="/sn" />
            </div>

            {/* Blocked query types */}
            <div>
              <label className="block text-xs text-gray-400 mb-2">Engelli Sorgu Tipleri</label>
              <div className="flex flex-wrap gap-3">
                {QTYPE_OPTIONS.map((qt) => {
                  const checked = (form.dns_blocked_qtypes || []).includes(qt.value);
                  return (
                    <label key={qt.value} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          const current = [...(form.dns_blocked_qtypes || [])];
                          if (checked) {
                            updateForm("dns_blocked_qtypes", current.filter((v) => v !== qt.value));
                          } else {
                            updateForm("dns_blocked_qtypes", [...current, qt.value]);
                          }
                        }}
                        className="accent-neon-cyan"
                      />
                      {qt.label}
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Sinkhole */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InputField label="Sinkhole IPv4" field="sinkhole_ipv4" type="text" />
              <InputField label="Sinkhole IPv6" field="sinkhole_ipv6" type="text" />
            </div>

            {/* DNSSEC Dogrulama */}
            <div className="border-t border-glass-border pt-4">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={18} className="text-neon-cyan" />
                <h3 className="text-sm font-semibold text-white">DNSSEC Doğrulama</h3>
              </div>
              <ToggleField
                label="DNSSEC Doğrulama"
                field="dnssec_enabled"
                desc="Upstream DNS yanıtlarında AD (Authenticated Data) flag kontrolü"
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">DNSSEC Modu</label>
                  <select
                    value={(form.dnssec_mode as string) || "log_only"}
                    onChange={(e) => updateForm("dnssec_mode", e.target.value)}
                    className="w-full bg-black/30 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-neon-cyan focus:outline-none"
                  >
                    <option value="log_only">Sadece Logla (log_only)</option>
                    <option value="enforce">Zorla — Doğrulanamayan engelle (enforce)</option>
                  </select>
                  <p className="text-xs text-gray-600 mt-1">
                    enforce: DNSSEC doğrulaması başarısız olan domainler engellenir
                  </p>
                </div>
              </div>
            </div>

            {/* DNS Tunneling */}
            <div className="border-t border-glass-border pt-4">
              <div className="flex items-center gap-2 mb-3">
                <Search size={18} className="text-neon-magenta" />
                <h3 className="text-sm font-semibold text-white">DNS Tunneling Tespiti</h3>
              </div>
              <ToggleField
                label="DNS Tunneling Dedektörü"
                field="dns_tunneling_enabled"
                desc="DNS üzerinden veri kaçırma girişimlerini tespit eder (3 kural)"
              />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                <InputField
                  label="Maks Subdomain Uzunluğu"
                  field="dns_tunneling_max_subdomain_len"
                  min={20}
                  max={200}
                  suffix="karakter"
                />
                <InputField
                  label="Maks Label/dk"
                  field="dns_tunneling_max_labels_per_min"
                  min={10}
                  max={1000}
                  suffix="label/dk"
                />
                <InputField
                  label="TXT Sorgu Oranı Eşiği"
                  field="dns_tunneling_txt_ratio_threshold"
                  min={5}
                  max={100}
                  suffix="%"
                />
              </div>
              <div className="mt-2 p-3 rounded-lg bg-black/20 text-xs text-gray-400 space-y-1">
                <p><strong className="text-gray-300">Kural 1:</strong> Subdomain uzunluğu eşiği aşarsa → veri kaçırma şüphesi</p>
                <p><strong className="text-gray-300">Kural 2:</strong> Dakikada benzersiz label sayısı eşiği aşarsa → otomatik subdomain üretimi</p>
                <p><strong className="text-gray-300">Kural 3:</strong> TXT sorgu oranı eşiği aşarsa → DNS üzerinden veri kanalı</p>
              </div>
            </div>

            {/* DNS-over-HTTPS */}
            <div className="border-t border-glass-border pt-4">
              <div className="flex items-center gap-2 mb-3">
                <Lock size={18} className="text-neon-green" />
                <h3 className="text-sm font-semibold text-white">DNS-over-HTTPS (DoH)</h3>
              </div>
              <ToggleField
                label="DoH Endpoint"
                field="doh_enabled"
                desc="RFC 8484 uyumlu DoH endpoint: /api/v1/doh/dns-query (GET+POST)"
              />
              <div className="mt-2 p-3 rounded-lg bg-black/20 text-xs text-gray-400">
                <p>DoH etkinleştirildiğinde tarayıcılar ve uygulamalar şifreli DNS sorgusu gönderebilir.</p>
                <p className="mt-1 font-mono text-neon-cyan/60">POST /api/v1/doh/dns-query (Content-Type: application/dns-message)</p>
                <p className="font-mono text-neon-cyan/60">GET /api/v1/doh/dns-query?dns=&lt;base64url&gt;</p>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => handleSave({
                  dns_rate_limit_per_sec: form.dns_rate_limit_per_sec,
                  dns_blocked_qtypes: form.dns_blocked_qtypes,
                  sinkhole_ipv4: form.sinkhole_ipv4,
                  sinkhole_ipv6: form.sinkhole_ipv6,
                  dnssec_enabled: form.dnssec_enabled,
                  dnssec_mode: form.dnssec_mode,
                  dns_tunneling_enabled: form.dns_tunneling_enabled,
                  dns_tunneling_max_subdomain_len: form.dns_tunneling_max_subdomain_len,
                  dns_tunneling_max_labels_per_min: form.dns_tunneling_max_labels_per_min,
                  dns_tunneling_txt_ratio_threshold: form.dns_tunneling_txt_ratio_threshold,
                  doh_enabled: form.doh_enabled,
                })}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/20 transition-colors disabled:opacity-50"
              >
                <Save size={16} />
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </div>
        </GlassCard>
      )}

      {tab === "alerts" && (
        <GlassCard>
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white">DDoS Uyarı Eşikleri</h2>
            <p className="text-xs text-gray-400">
              Bu eşikler aşıldığında Telegram uyarısı gönderilir. Değerler 60 saniyelik periyottaki artış miktarını temsil eder.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <InputField label="SYN Flood Eşiği" field="ddos_alert_syn_flood" min={10} max={10000} suffix="paket" />
              <InputField label="UDP Flood Eşiği" field="ddos_alert_udp_flood" min={10} max={10000} suffix="paket" />
              <InputField label="ICMP Flood Eşiği" field="ddos_alert_icmp_flood" min={5} max={10000} suffix="paket" />
              <InputField label="Bağlantı Limiti Eşiği" field="ddos_alert_conn_limit" min={10} max={10000} suffix="reject" />
              <InputField label="Geçersiz Paket Eşiği" field="ddos_alert_invalid_packet" min={10} max={10000} suffix="paket" />
              <InputField label="Uyarı Cooldown" field="ddos_alert_cooldown_sec" min={60} max={86400} suffix="saniye" />
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => handleSave({
                  ddos_alert_syn_flood: form.ddos_alert_syn_flood,
                  ddos_alert_udp_flood: form.ddos_alert_udp_flood,
                  ddos_alert_icmp_flood: form.ddos_alert_icmp_flood,
                  ddos_alert_conn_limit: form.ddos_alert_conn_limit,
                  ddos_alert_invalid_packet: form.ddos_alert_invalid_packet,
                  ddos_alert_cooldown_sec: form.ddos_alert_cooldown_sec,
                })}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/20 transition-colors disabled:opacity-50"
              >
                <Save size={16} />
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </div>
        </GlassCard>
      )}

      {tab === "trusted" && (
        <GlassCard>
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white">Güvenilir IP Adresleri</h2>
            <p className="text-xs text-gray-400">
              Bu listedeki IP'ler otomatik engellemeye tabi tutulmaz. Gateway, Pi ve DNS sunucuları varsayılan olarak güvenilirdir.
            </p>

            {/* Add form */}
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                placeholder="IP adresi"
                value={newIp}
                onChange={(e) => setNewIp(e.target.value)}
                className="flex-1 bg-black/30 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-neon-cyan focus:outline-none"
              />
              <input
                type="text"
                placeholder="Açıklama (opsiyonel)"
                value={newIpDesc}
                onChange={(e) => setNewIpDesc(e.target.value)}
                className="flex-1 bg-black/30 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:border-neon-cyan focus:outline-none"
              />
              <button
                onClick={handleAddTrustedIp}
                className="flex items-center gap-1 px-4 py-2 rounded-lg bg-neon-green/10 text-neon-green border border-neon-green/30 hover:bg-neon-green/20 transition-colors text-sm"
              >
                <Plus size={16} />
                Ekle
              </button>
            </div>

            {/* IP table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-glass-border">
                    <th className="text-left py-2 px-3">IP Adresi</th>
                    <th className="text-left py-2 px-3">Açıklama</th>
                    <th className="text-left py-2 px-3">Eklenme Tarihi</th>
                    <th className="text-right py-2 px-3">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {trustedIps.map((ip) => (
                    <tr key={ip.id} className="border-b border-glass-border/50 hover:bg-glass-light/30">
                      <td className="py-2 px-3 text-neon-cyan font-mono">{ip.ip_address}</td>
                      <td className="py-2 px-3 text-gray-300">{ip.description || "-"}</td>
                      <td className="py-2 px-3 text-gray-500">
                        {ip.created_at ? new Date(ip.created_at).toLocaleDateString("tr-TR") : "-"}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => handleDeleteTrustedIp(ip.id)}
                          className="p-1 rounded text-gray-400 hover:text-neon-red hover:bg-neon-red/10 transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {trustedIps.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-gray-500">
                        Henüz güvenilir IP eklenmemiş
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </GlassCard>
      )}

      {tab === "stats" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard
              title="Engelli IP"
              value={stats?.blocked_ip_count ?? 0}
              icon={<ShieldAlert size={24} />}
              neonColor="red"
            />
            <StatCard
              title="Otomatik Engel"
              value={stats?.total_auto_blocks ?? 0}
              icon={<ShieldCheck size={24} />}
              neonColor="amber"
            />
            <StatCard
              title="Şüpheli Sorgu"
              value={stats?.total_suspicious ?? 0}
              icon={<Activity size={24} />}
              neonColor="amber"
            />
            <StatCard
              title="DGA Tespit"
              value={stats?.dga_detections ?? 0}
              icon={<Globe size={24} />}
              neonColor="magenta"
            />
            <StatCard
              title="Engelli Subnet"
              value={stats?.blocked_subnet_count ?? 0}
              icon={<Bell size={24} />}
              neonColor="red"
            />
          </div>

          <GlassCard>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Detaylı İstatistikler</h2>
                <button
                  onClick={loadStats}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-glass-light text-gray-300 hover:text-white transition-colors"
                >
                  <RefreshCw size={14} />
                  Yenile
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-black/20 rounded-lg p-4">
                  <p className="text-xs text-gray-400">Toplam Dış IP Engelleme</p>
                  <p className="text-2xl font-bold text-neon-cyan">{stats?.total_external_blocked ?? 0}</p>
                </div>
                <div className="bg-black/20 rounded-lg p-4">
                  <p className="text-xs text-gray-400">Son Tehdit Zamanı</p>
                  <p className="text-sm text-white">
                    {stats?.last_threat_time
                      ? new Date(stats.last_threat_time).toLocaleString("tr-TR")
                      : "Tehdit tespit edilmedi"}
                  </p>
                </div>
              </div>

              <p className="text-xs text-gray-500 mt-4">
                İstatistikler her 10 saniyede otomatik güncellenir
              </p>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
