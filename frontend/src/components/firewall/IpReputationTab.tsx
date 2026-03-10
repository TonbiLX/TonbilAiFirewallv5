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
  Activity,
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
  checkApiUsage,
  checkBlacklistApiUsage,
  fetchBlacklist,
  triggerBlacklistFetch,
  fetchBlacklistConfig,
  updateBlacklistConfig,
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

interface BlacklistConfig {
  auto_block: boolean;
  min_score: number;
  limit: number;
  daily_fetches: number;
  daily_limit: number;
  last_fetch: string;
  total_count: number;
}

interface BlacklistIp {
  ip: string;
  abuse_score: number;
  country: string;
  last_reported_at: string;
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

  // Sorgulanan IP arama + sayfalama
  const [ipSearchTerm, setIpSearchTerm] = useState("");
  const [ipPageSize, setIpPageSize] = useState(50);
  const [ipCurrentPage, setIpCurrentPage] = useState(1);

  // API usage state
  const [apiUsage, setApiUsage] = useState<{ limit: number; used: number; remaining: number; usage_percent: number } | null>(null);
  const [checkingUsage, setCheckingUsage] = useState(false);

  // Blacklist state
  const [blacklistConfig, setBlacklistConfig] = useState<BlacklistConfig | null>(null);
  const [blacklistIps, setBlacklistIps] = useState<BlacklistIp[]>([]);
  const [blacklistFetching, setBlacklistFetching] = useState(false);
  const [blacklistApiChecking, setBlacklistApiChecking] = useState(false);
  const [blacklistSearch, setBlacklistSearch] = useState("");
  const [blacklistExpanded, setBlacklistExpanded] = useState(false);

  const showFeedback = (msg: string, ok: boolean) => {
    setFeedback({ msg, ok });
    setTimeout(() => setFeedback(null), 3000);
  };

  const loadBlacklistData = useCallback(async () => {
    try {
      const [configRes, listRes] = await Promise.all([
        fetchBlacklistConfig(),
        fetchBlacklist(),
      ]);
      setBlacklistConfig(configRes.data);
      setBlacklistIps(listRes.data.ips || []);
    } catch (err) {
      console.error("Blacklist veri yukleme hatasi:", err);
    }
  }, []);

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
    await loadBlacklistData();
  }, [loadBlacklistData]);

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

  const saveCountries = async (newList: string[]) => {
    try {
      await updateReputationConfig({ blocked_countries: newList });
      showFeedback("Ülke listesi güncellendi.", true);
    } catch {
      showFeedback("Ülke listesi kaydedilemedi.", false);
    }
  };

  const handleAddCountry = () => {
    const code = newCountry.trim().toUpperCase();
    if (!code || code.length !== 2 || !config) return;
    if (config.blocked_countries.includes(code)) {
      showFeedback("Bu ülke zaten listede.", false);
      return;
    }
    const newList = [...config.blocked_countries, code];
    setConfig({ ...config, blocked_countries: newList });
    setNewCountry("");
    saveCountries(newList);
  };

  const handleRemoveCountry = (code: string) => {
    if (!config) return;
    const newList = config.blocked_countries.filter((c) => c !== code);
    setConfig({ ...config, blocked_countries: newList });
    saveCountries(newList);
  };

  const handleCheckApiUsage = async () => {
    setCheckingUsage(true);
    try {
      const res = await checkApiUsage();
      if (res.data?.status === "ok" && res.data.data) {
        setApiUsage(res.data.data);
        // Summary'yi de güncelle (sync)
        const sumRes = await fetchReputationSummary();
        setSummary(sumRes.data);
        showFeedback("API kullanım bilgisi güncellendi.", true);
      } else {
        showFeedback(res.data?.message ?? "API kullanım bilgisi alınamadı.", false);
      }
    } catch {
      showFeedback("API kullanım kontrolü başarısız.", false);
    } finally {
      setCheckingUsage(false);
    }
  };

  const handleBlacklistFetch = async () => {
    setBlacklistFetching(true);
    try {
      const res = await triggerBlacklistFetch();
      const data = res.data;
      alert(data.message || "Blacklist fetch tamamlandi");
      await loadBlacklistData();
    } catch (err) {
      console.error("Blacklist fetch hatasi:", err);
    } finally {
      setBlacklistFetching(false);
    }
  };

  const handleBlacklistApiCheck = async () => {
    setBlacklistApiChecking(true);
    try {
      const res = await checkBlacklistApiUsage();
      const d = res.data?.data;
      if (d && blacklistConfig) {
        setBlacklistConfig({
          ...blacklistConfig,
          daily_fetches: d.used ?? blacklistConfig.daily_fetches,
          daily_limit: d.limit ?? blacklistConfig.daily_limit,
        });
      }
    } catch (err) {
      console.error("Blacklist API usage kontrol hatasi:", err);
    } finally {
      setBlacklistApiChecking(false);
    }
  };

  const handleBlacklistConfigUpdate = async (field: string, value: unknown) => {
    try {
      await updateBlacklistConfig({ [field]: value });
      await loadBlacklistData();
    } catch (err) {
      console.error("Blacklist config guncelleme hatasi:", err);
    }
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
      const newList = [...config.blocked_countries, code];
      setConfig({ ...config, blocked_countries: newList });
      saveCountries(newList);
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
    (!filterFlagged || ip.abuse_score >= 50) &&
    (!ipSearchTerm || ip.ip.includes(ipSearchTerm))
  );

  const sortedIps = [...filteredIps].sort((a, b) => {
    const aVal = a[sortBy] ?? "";
    const bVal = b[sortBy] ?? "";
    const cmp = typeof aVal === "number"
      ? (aVal as number) - (bVal as number)
      : String(aVal).localeCompare(String(bVal));
    return sortOrder === "asc" ? cmp : -cmp;
  });

  const totalFilteredIps = sortedIps.length;
  const totalIpPages = Math.ceil(totalFilteredIps / ipPageSize);
  const ipStartIndex = (ipCurrentPage - 1) * ipPageSize;
  const pagedIps = sortedIps.slice(ipStartIndex, ipStartIndex + ipPageSize);

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
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              {hasRealApiData || apiUsage ? "AbuseIPDB Kullanım" : "Günlük Kullanım"}
            </div>
            <button
              onClick={handleCheckApiUsage}
              disabled={checkingUsage || !config?.abuseipdb_key_set}
              className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium text-[#39FF14] border border-[#39FF14]/30 rounded hover:bg-[#39FF14]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="AbuseIPDB API'den güncel kullanım bilgisini çek"
            >
              <Activity className={`w-3 h-3 ${checkingUsage ? "animate-pulse" : ""}`} />
              {checkingUsage ? "Kontrol..." : "Kontrol Et"}
            </button>
          </div>
          <div className="text-2xl font-bold text-[#39FF14]">
            {apiUsage ? apiUsage.used : effectiveUsed}
            <span className="text-sm font-normal text-gray-400">/{apiUsage ? apiUsage.limit : effectiveLimit}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1 mt-1.5">
            <div
              className={`h-1 rounded-full transition-all ${
                (apiUsage ? apiUsage.usage_percent : dailyPct) >= 90
                  ? "bg-[#FF003C]"
                  : (apiUsage ? apiUsage.usage_percent : dailyPct) >= 70
                  ? "bg-[#FFB800]"
                  : "bg-[#39FF14]"
              }`}
              style={{ width: `${Math.min(apiUsage ? apiUsage.usage_percent : dailyPct, 100)}%` }}
            />
          </div>
          {apiUsage ? (
            <div className="text-xs text-[#00F0FF] mt-1.5 font-mono">
              {apiUsage.remaining} istek kalan ({apiUsage.usage_percent}%)
            </div>
          ) : hasRealApiData ? (
            <div className="text-xs text-[#00F0FF] mt-1.5 font-mono">
              {summary?.abuseipdb_remaining ?? "?"} istek kalan
            </div>
          ) : (
            <div className="text-xs text-gray-500 mt-1.5">Yerel sayaç — kontrol et ile güncelle</div>
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

      {/* ---- Bölüm 4: AbuseIPDB Kara Liste ---- */}
      <GlassCard className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[#FF00E5]" />
            <h3 className="text-sm font-semibold text-white">AbuseIPDB Kara Liste</h3>
            {blacklistConfig && (
              <span className="text-xs text-gray-500">
                ({blacklistConfig.total_count.toLocaleString()} IP)
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {blacklistConfig && (
              <span className="text-xs text-gray-500">
                Günlük: {blacklistConfig.daily_fetches}/{blacklistConfig.daily_limit}
              </span>
            )}
            <button
              onClick={handleBlacklistApiCheck}
              disabled={blacklistApiChecking || !config?.abuseipdb_key_set}
              className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium text-gray-400 border border-gray-600 hover:border-[#FF00E5]/40 hover:text-[#FF00E5] transition-colors disabled:opacity-40"
              title="AbuseIPDB Blacklist API limitini kontrol et"
            >
              <Activity className={`h-2.5 w-2.5 ${blacklistApiChecking ? 'animate-pulse' : ''}`} />
              {blacklistApiChecking ? '...' : 'Kontrol Et'}
            </button>
            <button
              onClick={handleBlacklistFetch}
              disabled={blacklistFetching}
              className="flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium text-[#FF00E5] border border-[#FF00E5]/30 hover:bg-[#FF00E5]/10 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${blacklistFetching ? 'animate-spin' : ''}`} />
              {blacklistFetching ? 'İndiriliyor...' : 'Şimdi Çek'}
            </button>
          </div>
        </div>

        {/* Config row */}
        {blacklistConfig && (
          <div className="flex flex-wrap items-center gap-4 mb-4 text-xs">
            <label className="flex items-center gap-1.5 text-gray-400">
              <span>Otomatik Engelle:</span>
              <button
                onClick={() => handleBlacklistConfigUpdate('auto_block', !blacklistConfig.auto_block)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  blacklistConfig.auto_block ? 'bg-[#FF00E5]/30 border border-[#FF00E5]/50' : 'bg-gray-700 border border-gray-600'
                }`}
              >
                <span className={`inline-block h-3.5 w-3.5 rounded-full transition-transform ${
                  blacklistConfig.auto_block ? 'translate-x-4 bg-[#FF00E5]' : 'translate-x-0.5 bg-gray-400'
                }`} />
              </button>
            </label>
            <label className="flex items-center gap-1 text-gray-400">
              Min Skor:
              <input
                type="number"
                value={blacklistConfig.min_score}
                onChange={(e) => handleBlacklistConfigUpdate('min_score', parseInt(e.target.value) || 100)}
                className="w-14 rounded border border-gray-600 bg-transparent px-1.5 py-0.5 text-xs text-white text-center focus:outline-none focus:border-[#FF00E5]/50"
                min={25}
                max={100}
              />
            </label>
            <label className="flex items-center gap-1 text-gray-400">
              Max IP:
              <input
                type="number"
                value={blacklistConfig.limit}
                onChange={(e) => handleBlacklistConfigUpdate('limit', parseInt(e.target.value) || 10000)}
                className="w-20 rounded border border-gray-600 bg-transparent px-1.5 py-0.5 text-xs text-white text-center focus:outline-none focus:border-[#FF00E5]/50"
                min={100}
                max={10000}
              />
            </label>
            {blacklistConfig.last_fetch && (
              <span className="text-gray-500 ml-auto">
                Son: {formatDate(blacklistConfig.last_fetch)}
              </span>
            )}
          </div>
        )}

        {/* Blacklist table (collapsible) */}
        {blacklistIps.length > 0 && (
          <>
            <div className="flex items-center gap-2 mb-2">
              <button
                onClick={() => setBlacklistExpanded(!blacklistExpanded)}
                className="text-xs text-[#FF00E5] hover:text-[#FF00E5]/80 transition-colors"
              >
                {blacklistExpanded ? '▼ Listeyi Gizle' : '▶ Listeyi Göster'} ({blacklistIps.length.toLocaleString()} IP)
              </button>
              {blacklistExpanded && (
                <div className="relative flex-1 max-w-xs">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-500" />
                  <input
                    type="text"
                    value={blacklistSearch}
                    onChange={(e) => setBlacklistSearch(e.target.value)}
                    placeholder="IP ara..."
                    className="w-full rounded border border-gray-700 bg-transparent pl-7 pr-2 py-1 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#FF00E5]/50"
                  />
                </div>
              )}
            </div>

            {blacklistExpanded && (
              <div className="max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="pb-2 pr-4 text-xs font-medium text-gray-400">IP Adresi</th>
                      <th className="pb-2 pr-4 text-xs font-medium text-gray-400">Skor</th>
                      <th className="pb-2 pr-4 text-xs font-medium text-gray-400">Ülke</th>
                      <th className="pb-2 text-xs font-medium text-gray-400">Son Rapor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {blacklistIps
                      .filter(item => !blacklistSearch || item.ip.includes(blacklistSearch) || item.country.toLowerCase().includes(blacklistSearch.toLowerCase()))
                      .slice(0, 100)
                      .map((item) => (
                        <tr key={item.ip} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-1.5 pr-4 text-xs font-mono text-[#FF00E5]">{item.ip}</td>
                          <td className="py-1.5 pr-4">
                            <ScoreBadge score={item.abuse_score} />
                          </td>
                          <td className="py-1.5 pr-4 text-xs text-gray-400">
                            {getFlag(item.country)} {item.country}
                          </td>
                          <td className="py-1.5 text-xs text-gray-500">
                            {item.last_reported_at ? formatDate(item.last_reported_at) : '--'}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
                {blacklistIps.filter(item => !blacklistSearch || item.ip.includes(blacklistSearch)).length > 100 && (
                  <p className="text-xs text-gray-600 text-center mt-2">
                    İlk 100 IP gösteriliyor ({blacklistIps.length.toLocaleString()} toplam)
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {blacklistIps.length === 0 && !blacklistFetching && (
          <p className="text-xs text-gray-600 text-center py-2">
            Henüz blacklist verisi yok. "Şimdi Çek" butonuyla ilk indirmeyi başlatabilirsiniz.
          </p>
        )}
      </GlassCard>

      {/* ---- Bölüm 5: Kontrol Edilen IP'ler ---- */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-neon-cyan/10 border border-neon-cyan/20">
              <Shield className="w-5 h-5 text-[#00F0FF]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Kontrol Edilen IP'ler</h3>
              <p className="text-xs text-gray-400">
                {ipSearchTerm ? `${totalFilteredIps} / ${ips.length}` : ips.length} kayıt
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* IP arama inputu */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
              <input
                type="text"
                value={ipSearchTerm}
                onChange={(e) => { setIpSearchTerm(e.target.value); setIpCurrentPage(1); }}
                placeholder="IP ara..."
                className="bg-black border border-glass-border rounded-lg px-3 py-2 pl-9 text-sm text-[#00F0FF] placeholder-gray-500 focus:outline-none focus:border-[#00F0FF]/50 w-64"
              />
            </div>

            {/* Sayfa basina dropdown */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">Sayfa:</span>
              <select
                value={ipPageSize}
                onChange={(e) => { setIpPageSize(Number(e.target.value)); setIpCurrentPage(1); }}
                style={{ backgroundColor: '#000' }}
                className="border border-glass-border rounded-lg px-2 py-2 text-sm text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]/50 appearance-none cursor-pointer w-20"
              >
                <option value={50} className="bg-black text-[#00F0FF]">50</option>
                <option value={100} className="bg-black text-[#00F0FF]">100</option>
                <option value={150} className="bg-black text-[#00F0FF]">150</option>
                <option value={200} className="bg-black text-[#00F0FF]">200</option>
              </select>
            </div>

            {/* Sadece işaretlenenler toggle */}
            <button
              onClick={() => { setFilterFlagged(!filterFlagged); setIpCurrentPage(1); }}
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

        {ips.length === 0 || totalFilteredIps === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Shield className="w-10 h-10 mb-3 opacity-30" />
            <p className="text-sm">
              {ipSearchTerm ? `"${ipSearchTerm}" ile eşleşen IP bulunamadı` : "Henüz kontrol edilen IP yok"}
            </p>
            {!ipSearchTerm && (
              <p className="text-xs mt-1 opacity-60">IP itibar kontrolü aktif olduğunda burada görünecek</p>
            )}
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
                {pagedIps.map((ip) => (
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

        {/* Sayfalama kontrolleri */}
        {totalIpPages > 1 && (
          <div className="flex items-center justify-between px-1 py-2 mt-4 text-sm">
            <button
              onClick={() => setIpCurrentPage(p => Math.max(1, p - 1))}
              disabled={ipCurrentPage <= 1}
              className="px-3 py-1.5 text-[#00F0FF] border border-[#00F0FF]/30 rounded-lg hover:bg-[#00F0FF]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-xs"
            >
              &lt; Onceki
            </button>
            <span className="text-xs text-gray-400">
              Sayfa {ipCurrentPage} / {totalIpPages}
              {ipSearchTerm
                ? ` (filtrelenmis: ${totalFilteredIps} / ${ips.length} IP)`
                : ` (toplam ${totalFilteredIps} IP)`}
            </span>
            <button
              onClick={() => setIpCurrentPage(p => Math.min(totalIpPages, p + 1))}
              disabled={ipCurrentPage >= totalIpPages}
              className="px-3 py-1.5 text-[#00F0FF] border border-[#00F0FF]/30 rounded-lg hover:bg-[#00F0FF]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-xs"
            >
              Sonraki &gt;
            </button>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
