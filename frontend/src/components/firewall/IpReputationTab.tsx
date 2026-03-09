// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// IP itibar yönetimi sekmesi: AbuseIPDB entegrasyonu, ülke engelleme, kontrol edilen IP listesi

import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Eye,
  EyeOff,
  Save,
  RefreshCw,
  Trash2,
  Plus,
  X,
  Globe,
  AlertTriangle,
  CheckCircle,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import { LoadingSpinner } from "../common/LoadingSpinner";
import {
  fetchReputationConfig,
  updateReputationConfig,
  fetchReputationSummary,
  fetchReputationIps,
  clearReputationCache,
  testAbuseipdbKey,
} from "../../services/ipReputationApi";

// ---- Tipler ----

interface ReputationConfig {
  enabled: boolean;
  abuseipdb_key: string;
  abuseipdb_key_set: boolean;
  blocked_countries: string[];
  check_interval: number;
  max_checks_per_cycle: number;
  daily_limit: number;
}

interface ReputationSummary {
  total_checked: number;
  flagged_critical: number;
  flagged_warning: number;
  daily_checks_used: number;
  daily_limit: number;
  abuseipdb_remaining?: number | null;
  abuseipdb_limit?: number | null;
}

interface ReputationIp {
  ip: string;
  abuse_score: number;
  total_reports: number;
  country: string;
  city: string;
  isp: string;
  org: string;
  checked_at: string;
}

// ---- Sabitler ----

const PRESET_COUNTRIES: { code: string; flag: string; name: string }[] = [
  { code: "CN", flag: "🇨🇳", name: "Çin" },
  { code: "RU", flag: "🇷🇺", name: "Rusya" },
  { code: "KP", flag: "🇰🇵", name: "Kuzey Kore" },
  { code: "IR", flag: "🇮🇷", name: "İran" },
  { code: "NG", flag: "🇳🇬", name: "Nijerya" },
  { code: "BR", flag: "🇧🇷", name: "Brezilya" },
  { code: "IN", flag: "🇮🇳", name: "Hindistan" },
  { code: "UA", flag: "🇺🇦", name: "Ukrayna" },
];

const COUNTRY_FLAG_MAP: Record<string, string> = {
  CN: "🇨🇳", RU: "🇷🇺", KP: "🇰🇵", IR: "🇮🇷",
  NG: "🇳🇬", BR: "🇧🇷", IN: "🇮🇳", UA: "🇺🇦",
  US: "🇺🇸", DE: "🇩🇪", FR: "🇫🇷", TR: "🇹🇷",
};

function getFlag(code: string | undefined | null): string {
  if (!code) return "🏳️";
  return COUNTRY_FLAG_MAP[code.toUpperCase()] ?? "🏳️";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function maskApiKey(key: string): string {
  if (key.length <= 8) return "****";
  return key.slice(0, 4) + "••••••••" + key.slice(-4);
}

// ---- Skor Badge ----

function ScoreBadge({ score }: { score: number }) {
  if (score == null || score === 0) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-700/50 text-gray-400 border border-gray-600/30">
        BİLİNMİYOR
      </span>
    );
  }
  if (score >= 80) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-neon-red/15 text-[#FF003C] border border-[#FF003C]/40 shadow-[0_0_8px_rgba(255,0,60,0.25)]">
        <AlertTriangle className="w-3 h-3" />
        KRİTİK {score}
      </span>
    );
  }
  if (score >= 50) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-neon-amber/10 text-[#FFB800] border border-[#FFB800]/40">
        <AlertTriangle className="w-3 h-3" />
        ŞÜPHELİ {score}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-neon-green/10 text-[#39FF14] border border-[#39FF14]/30">
      <CheckCircle className="w-3 h-3" />
      TEMİZ {score}
    </span>
  );
}

// ---- Ana Bileşen ----

export function IpReputationTab() {
  const [config, setConfig] = useState<ReputationConfig | null>(null);
  const [summary, setSummary] = useState<ReputationSummary | null>(null);
  const [ips, setIps] = useState<ReputationIp[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [filterFlagged, setFilterFlagged] = useState(false);
  const [sortBy, setSortBy] = useState<keyof ReputationIp>("checked_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [newCountry, setNewCountry] = useState("");
  const [feedback, setFeedback] = useState<{ msg: string; ok: boolean } | null>(null);

  const showFeedback = (msg: string, ok: boolean) => {
    setFeedback({ msg, ok });
    setTimeout(() => setFeedback(null), 3000);
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, sumRes, ipsRes] = await Promise.all([
        fetchReputationConfig(),
        fetchReputationSummary(),
        fetchReputationIps(),
      ]);
      setConfig(cfgRes.data);
      setSummary(sumRes.data);
      setIps(ipsRes.data?.ips ?? []);
    } catch {
      showFeedback("Veriler yüklenemedi.", false);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadIps = useCallback(async () => {
    try {
      const res = await fetchReputationIps(filterFlagged ? 50 : undefined);
      setIps(res.data?.ips ?? []);
    } catch {
      showFeedback("IP listesi yüklenemedi.", false);
    }
  }, [filterFlagged]);

  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => { loadIps(); }, [loadIps]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const payload: any = {
        enabled: config.enabled,
        blocked_countries: config.blocked_countries,
              };
      if (apiKeyInput.trim()) {
        payload.abuseipdb_key = apiKeyInput.trim();
      }
      await updateReputationConfig(payload);
      setApiKeyInput("");
      const res = await fetchReputationConfig();
      setConfig(res.data);
      showFeedback("Ayarlar kaydedildi.", true);
    } catch {
      showFeedback("Kaydetme başarısız.", false);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const res = await testAbuseipdbKey();
      if (res.data?.status === "ok") {
        showFeedback("API anahtarı geçerli.", true);
      } else {
        showFeedback(res.data?.message ?? "Test başarısız.", false);
      }
    } catch {
      showFeedback("API anahtarı geçersiz veya ulaşılamıyor.", false);
    } finally {
      setTesting(false);
    }
  };

  const handleClearCache = async () => {
    setClearing(true);
    try {
      await clearReputationCache();
      setIps([]);
      showFeedback("IP önbelleği temizlendi.", true);
    } catch {
      showFeedback("Önbellek temizlenemedi.", false);
    } finally {
      setClearing(false);
    }
  };

  const handleToggleEnabled = () => {
    if (!config) return;
    setConfig({ ...config, enabled: !config.enabled });
  };

  const handleAddCountry = () => {
    const code = newCountry.trim().toUpperCase();
    if (!code || code.length !== 2 || !config) return;
    if (config.blocked_countries.includes(code)) {
      showFeedback("Bu ülke zaten listede.", false);
      return;
    }
    setConfig({ ...config, blocked_countries: [...config.blocked_countries, code] });
    setNewCountry("");
  };

  const handleRemoveCountry = (code: string) => {
    if (!config) return;
    setConfig({
      ...config,
      blocked_countries: config.blocked_countries.filter((c) => c !== code),
    });
  };

  function handleSort(col: keyof ReputationIp) {
    if (sortBy === col) setSortOrder(o => o === "asc" ? "desc" : "asc");
    else { setSortBy(col); setSortOrder("asc"); }
  }

  const handlePresetCountry = (code: string) => {
    if (!config) return;
    if (config.blocked_countries.includes(code)) {
      handleRemoveCountry(code);
    } else {
      setConfig({ ...config, blocked_countries: [...config.blocked_countries, code] });
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <LoadingSpinner />
      <p className="text-gray-400 text-sm">IP İtibar verileri yükleniyor...</p>
    </div>
  );

  // Gercek AbuseIPDB limiti varsa onu kullan, yoksa yerel limite don
  const effectiveLimit = summary?.abuseipdb_limit ?? summary?.daily_limit ?? 900;
  // daily_checks_used backend tarafindan gercek API verisine gore hesaplanir (varsa)
  const effectiveUsed = summary?.daily_checks_used ?? 0;
  const dailyPct = effectiveLimit > 0
    ? Math.round((effectiveUsed / effectiveLimit) * 100)
    : 0;
  // Gercek AbuseIPDB verisi mevcut mu? (header'dan alindi mi?)
  const hasRealApiData = summary?.abuseipdb_limit != null && summary?.abuseipdb_remaining != null;

  const filteredIps = ips.filter(ip =>
    (!filterFlagged || ip.abuse_score >= 50)
  );

  const sortedIps = [...filteredIps].sort((a, b) => {
    const aVal = a[sortBy] ?? "";
    const bVal = b[sortBy] ?? "";
    const cmp = typeof aVal === "number"
      ? (aVal as number) - (bVal as number)
      : String(aVal).localeCompare(String(bVal));
    return sortOrder === "asc" ? cmp : -cmp;
  });

  return (
    <div className="space-y-6">

      {/* Geri bildirim mesajı */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
            feedback.ok
              ? "bg-neon-green/10 border-neon-green/30 text-[#39FF14]"
              : "bg-neon-red/10 border-neon-red/30 text-[#FF003C]"
          }`}
        >
          {feedback.ok ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {feedback.msg}
        </div>
      )}

      {/* ---- Bölüm 1: Özet İstatistikler ---- */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Toplam Kontrol */}
        <div className="glass-card p-4 border-l-2 border-[#00F0FF]">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Toplam Kontrol</div>
          <div className="text-2xl font-bold text-[#00F0FF]">{summary?.total_checked ?? 0}</div>
          <div className="text-xs text-gray-500 mt-1">Kontrol edilen IP</div>
        </div>

        {/* Kritik IP */}
        <div className="glass-card p-4 border-l-2 border-[#FF003C]">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Kritik IP</div>
          <div className="text-2xl font-bold text-[#FF003C]">{summary?.flagged_critical ?? 0}</div>
          <div className="text-xs text-gray-500 mt-1">Skor &ge; 80</div>
        </div>

        {/* Şüpheli IP */}
        <div className="glass-card p-4 border-l-2 border-[#FFB800]">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Şüpheli IP</div>
          <div className="text-2xl font-bold text-[#FFB800]">{summary?.flagged_warning ?? 0}</div>
          <div className="text-xs text-gray-500 mt-1">Skor 50–79</div>
        </div>

        {/* Günlük Kullanım */}
        <div className="glass-card p-4 border-l-2 border-[#39FF14]">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
            {hasRealApiData ? "AbuseIPDB Kullanım" : "Günlük Kullanım"}
          </div>
          <div className="text-2xl font-bold text-[#39FF14]">
            {effectiveUsed}
            <span className="text-sm font-normal text-gray-400">/{effectiveLimit}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1 mt-1.5">
            <div
              className={`h-1 rounded-full transition-all ${
                dailyPct >= 90 ? "bg-[#FF003C]" : dailyPct >= 70 ? "bg-[#FFB800]" : "bg-[#39FF14]"
              }`}
              style={{ width: `${Math.min(dailyPct, 100)}%` }}
            />
          </div>
          {hasRealApiData ? (
            <div className="text-xs text-[#00F0FF] mt-1.5 font-mono">
              {summary?.abuseipdb_remaining ?? "?"} istek kalan
            </div>
          ) : (
            <div className="text-xs text-gray-500 mt-1.5">Yerel sayaç</div>
          )}
        </div>
      </div>

      {/* ---- Bölüm 2: Ayarlar ---- */}
      <GlassCard>
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-neon-cyan/10 border border-neon-cyan/20">
            <Shield className="w-5 h-5 text-[#00F0FF]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">IP İtibar Ayarları</h3>
            <p className="text-xs text-gray-400">AbuseIPDB entegrasyonu ve kontrol parametreleri</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Worker Toggle */}
          <div>
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
              Servis Durumu
            </label>
            <button
              onClick={handleToggleEnabled}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border w-full text-left transition-all ${
                config?.enabled
                  ? "bg-neon-green/10 border-neon-green/30 hover:bg-neon-green/15"
                  : "bg-gray-800/50 border-gray-600/30 hover:bg-gray-700/50"
              }`}
            >
              <div
                className={`w-3 h-3 rounded-full flex-shrink-0 ${
                  config?.enabled
                    ? "bg-[#39FF14] shadow-[0_0_8px_#39FF14] animate-pulse"
                    : "bg-gray-500"
                }`}
              />
              <span className={`text-sm font-medium ${config?.enabled ? "text-[#39FF14]" : "text-gray-400"}`}>
                {config?.enabled ? "Aktif — IP itibar kontrolü çalışıyor" : "Pasif — IP itibar kontrolü devre dışı"}
              </span>
            </button>
          </div>

          {/* Kontrol bilgisi */}
          <div>
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
              Kontrol Aralığı
            </label>
            <p className="text-sm text-white">{config?.check_interval ?? 300}s — döngü başına max {config?.max_checks_per_cycle ?? 10} IP</p>
          </div>

          {/* AbuseIPDB API Anahtarı */}
          <div className="md:col-span-2">
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
              AbuseIPDB API Anahtarı
            </label>
            {config?.abuseipdb_key_set && !apiKeyInput && (
              <div className="flex items-center gap-2 mb-2 px-3 py-2 rounded-lg bg-neon-green/5 border border-neon-green/20 text-xs text-gray-300">
                <CheckCircle className="w-3.5 h-3.5 text-[#39FF14]" />
                Kayıtlı anahtar:
                <code className="text-[#00F0FF] font-mono">
                  {config.abuseipdb_key || "••••••••"}
                </code>
              </div>
            )}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={showApiKey ? "text" : "password"}
                  placeholder={config?.abuseipdb_key_set ? "Değiştirmek için yeni anahtar girin..." : "AbuseIPDB API anahtarınızı girin..."}
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  className="w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 pr-10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition-colors"
                >
                  {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <button
                onClick={handleTest}
                disabled={testing || (!apiKeyInput && !config?.abuseipdb_key_set)}
                className="px-4 py-2 bg-neon-amber/10 text-[#FFB800] border border-neon-amber/30 rounded-lg hover:bg-neon-amber/20 transition-colors text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                <Search className="w-4 h-4" />
                {testing ? "Test..." : "Test"}
              </button>
            </div>
          </div>
        </div>

        {/* Kaydet butonu */}
        <div className="flex justify-end mt-6 pt-4 border-t border-glass-border">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-neon-cyan/10 text-[#00F0FF] border border-neon-cyan/30 rounded-lg hover:bg-neon-cyan/20 transition-colors text-sm font-medium flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            {saving ? "Kaydediliyor..." : "Kaydet"}
          </button>
        </div>
      </GlassCard>

      {/* ---- Bölüm 3: Ülke Engelleme ---- */}
      <GlassCard>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-neon-magenta/10 border border-neon-magenta/20">
            <Globe className="w-5 h-5 text-[#FF00E5]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Ülke Sınırlandırma</h3>
            <p className="text-xs text-gray-400">Bu ülkelerden gelen bağlantılar otomatik olarak işaretlenir</p>
          </div>
        </div>

        {/* Mevcut engelli ülkeler */}
        <div className="flex flex-wrap gap-2 min-h-[40px] my-4">
          {config?.blocked_countries && config.blocked_countries.length > 0 ? (
            config.blocked_countries.map((code) => (
              <span
                key={code}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-neon-magenta/10 border border-neon-magenta/30 text-[#FF00E5]"
              >
                <span>{getFlag(code)}</span>
                <span>{code}</span>
                <button
                  onClick={() => handleRemoveCountry(code)}
                  className="ml-0.5 hover:text-white transition-colors"
                  title="Kaldır"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))
          ) : (
            <span className="text-sm text-gray-500 italic">Henüz ülke eklenmemiş</span>
          )}
        </div>

        {/* Hızlı preset butonlar */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Hızlı Ekle</p>
          <div className="flex flex-wrap gap-2">
            {PRESET_COUNTRIES.map((c) => {
              const active = config?.blocked_countries.includes(c.code);
              return (
                <button
                  key={c.code}
                  onClick={() => handlePresetCountry(c.code)}
                  title={c.name}
                  className={`px-2.5 py-1 rounded-lg text-xs border transition-all ${
                    active
                      ? "bg-neon-magenta/20 border-neon-magenta/50 text-[#FF00E5]"
                      : "bg-gray-800/50 border-gray-600/30 text-gray-400 hover:border-gray-500/50 hover:text-gray-200"
                  }`}
                >
                  {c.flag} {c.code}
                </button>
              );
            })}
          </div>
        </div>

        {/* Manuel ekleme */}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="2 harfli ülke kodu (örn. US)"
            maxLength={2}
            value={newCountry}
            onChange={(e) => setNewCountry(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleAddCountry()}
            className="flex-1 bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors uppercase"
          />
          <button
            onClick={handleAddCountry}
            disabled={newCountry.length !== 2}
            className="px-4 py-2 bg-neon-cyan/10 text-[#00F0FF] border border-neon-cyan/30 rounded-lg hover:bg-neon-cyan/20 transition-colors text-sm font-medium flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            Ekle
          </button>
        </div>
      </GlassCard>

      {/* ---- Bölüm 4: Kontrol Edilen IP'ler ---- */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-neon-cyan/10 border border-neon-cyan/20">
              <Shield className="w-5 h-5 text-[#00F0FF]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Kontrol Edilen IP'ler</h3>
              <p className="text-xs text-gray-400">{ips.length} kayıt</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Sadece işaretlenenler toggle */}
            <button
              onClick={() => setFilterFlagged(!filterFlagged)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-all ${
                filterFlagged
                  ? "bg-neon-amber/15 border-neon-amber/40 text-[#FFB800]"
                  : "bg-gray-800/50 border-gray-600/30 text-gray-400 hover:border-gray-500/50"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              {filterFlagged ? "Tümünü Göster" : "Sadece İşaretliler"}
            </button>

            {/* Yenile */}
            <button
              onClick={loadIps}
              className="px-3 py-1.5 bg-neon-cyan/10 text-[#00F0FF] border border-neon-cyan/30 rounded-lg hover:bg-neon-cyan/20 transition-colors text-xs font-medium flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Yenile
            </button>

            {/* Önbelleği temizle */}
            <button
              onClick={handleClearCache}
              disabled={clearing}
              className="px-3 py-1.5 bg-neon-red/10 text-[#FF003C] border border-neon-red/30 rounded-lg hover:bg-neon-red/20 transition-colors text-xs font-medium flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-3.5 h-3.5" />
              {clearing ? "Temizleniyor..." : "Önbelleği Temizle"}
            </button>
          </div>
        </div>

        {ips.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Shield className="w-10 h-10 mb-3 opacity-30" />
            <p className="text-sm">Henüz kontrol edilen IP yok</p>
            <p className="text-xs mt-1 opacity-60">IP itibar kontrolü aktif olduğunda burada görünecek</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-glass-border text-xs text-gray-400 uppercase tracking-wider">
                  <th
                    className="text-left py-2 pr-4 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("ip")}
                  >
                    <span className="flex items-center gap-1.5">
                      IP Adresi
                      {sortBy === "ip" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                  <th
                    className="text-left py-2 pr-4 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("abuse_score")}
                  >
                    <span className="flex items-center gap-1.5">
                      Skor
                      {sortBy === "abuse_score" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                  <th
                    className="text-left py-2 pr-4 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("country")}
                  >
                    <span className="flex items-center gap-1.5">
                      Ülke
                      {sortBy === "country" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                  <th
                    className="text-left py-2 pr-4 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("city")}
                  >
                    <span className="flex items-center gap-1.5">
                      Şehir
                      {sortBy === "city" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                  <th
                    className="text-left py-2 pr-4 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("isp")}
                  >
                    <span className="flex items-center gap-1.5">
                      ISP
                      {sortBy === "isp" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                  <th
                    className="text-left py-2 font-medium cursor-pointer select-none hover:text-white transition-colors"
                    onClick={() => handleSort("checked_at")}
                  >
                    <span className="flex items-center gap-1.5">
                      Kontrol Tarihi
                      {sortBy === "checked_at" ? (
                        sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-40" />
                      )}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-glass-border/50">
                {sortedIps.map((ip) => (
                  <tr
                    key={ip.ip}
                    className={`transition-colors ${
                      ip.abuse_score >= 80
                        ? "bg-neon-red/5 hover:bg-neon-red/8"
                        : ip.abuse_score >= 50
                        ? "bg-neon-amber/5 hover:bg-neon-amber/8"
                        : "hover:bg-white/3"
                    }`}
                  >
                    <td className="py-2.5 pr-4">
                      <code className="text-[#00F0FF] text-xs font-mono">{ip.ip}</code>
                    </td>
                    <td className="py-2.5 pr-4">
                      <ScoreBadge score={ip.abuse_score} />
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="flex items-center gap-1.5 text-gray-300">
                        <span>{getFlag(ip.country)}</span>
                        <span className="text-xs">{ip.country || "—"}</span>
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400 text-xs">{ip.city || "—"}</td>
                    <td className="py-2.5 pr-4 text-gray-400 text-xs max-w-[160px] truncate" title={ip.isp}>
                      {ip.isp || "—"}
                    </td>
                    <td className="py-2.5 text-gray-500 text-xs whitespace-nowrap">
                      {ip.checked_at ? formatDate(ip.checked_at) : "—"}
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
