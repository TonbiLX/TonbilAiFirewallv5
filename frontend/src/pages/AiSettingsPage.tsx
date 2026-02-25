// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Yapay Zeka Ayarları sayfası: Saglayici, Model, Log Analizi, İstatistikler (4 tab)

import { useEffect, useState } from "react";
import {
  Server,
  Settings2,
  BarChart3,
  FileSearch,
  Eye,
  EyeOff,
  CheckCircle,
  AlertTriangle,
  Save,
  Loader2,
  Zap,
  RefreshCw,
  Brain,
  Cpu,
  Clock,
  Activity,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { StatCard } from "../components/common/StatCard";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchAiConfig,
  updateAiConfig,
  testAiConnection,
  fetchAiProviders,
  fetchAiStats,
  resetAiCounter,
} from "../services/aiSettingsApi";
import type { AiConfig, AiProviderInfo, AiTestResponse, AiStats } from "../types";

type TabId = "provider" | "model" | "log-analysis" | "stats";

const tabs: { id: TabId; label: string; icon: typeof Server }[] = [
  { id: "provider", label: "Saglayici", icon: Server },
  { id: "model", label: "Model Ayarları", icon: Settings2 },
  { id: "log-analysis", label: "Log Analizi", icon: FileSearch },
  { id: "stats", label: "İstatistikler", icon: BarChart3 },
];

export function AiSettingsPage() {
  const { connected } = useWebSocket();
  const [activeTab, setActiveTab] = useState<TabId>("provider");
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [providers, setProviders] = useState<AiProviderInfo[]>([]);
  const [stats, setStats] = useState<AiStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Form state (Saglayici tab)
  const [provider, setProvider] = useState("none");
  const [apiKey, setApiKey] = useState("");
  const [apiKeyChanged, setApiKeyChanged] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [enabled, setEnabled] = useState(false);

  // Form state (Model tab)
  const [model, setModel] = useState("");
  const [chatMode, setChatMode] = useState<"tfidf" | "llm" | "hybrid">("tfidf");
  const [temperature, setTemperature] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [dailyLimit, setDailyLimit] = useState(200);
  const [customPrompt, setCustomPrompt] = useState("");

  // Form state (Log Analizi tab)
  const [logAnalysisEnabled, setLogAnalysisEnabled] = useState(false);
  const [logInterval, setLogInterval] = useState(60);
  const [logMaxLogs, setLogMaxLogs] = useState(100);

  // UI state
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AiTestResponse | null>(null);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  const loadAll = async () => {
    try {
      // Her API çağrısıni ayri yap - biri başarısız olursa digerlerini etkilemesin
      const [configRes, providersRes, statsRes] = await Promise.allSettled([
        fetchAiConfig(),
        fetchAiProviders(),
        fetchAiStats(),
      ]);

      if (providersRes.status === "fulfilled") {
        setProviders(providersRes.value.data as AiProviderInfo[]);
      } else {
        console.error("Providers yüklenemedi:", providersRes.reason);
      }

      if (statsRes.status === "fulfilled") {
        setStats(statsRes.value.data as AiStats);
      } else {
        console.error("Stats yüklenemedi:", statsRes.reason);
      }

      if (configRes.status === "fulfilled") {
        const c = configRes.value.data as AiConfig;
        setConfig(c);
        // Form'u doldur
        setProvider(c.provider);
        setApiKey(c.api_key_masked || "");
        setApiKeyChanged(false);
        setBaseUrl(c.base_url || "");
        setEnabled(c.enabled);
        setModel(c.model || "");
        setChatMode(c.chat_mode);
        setTemperature(c.temperature);
        setMaxTokens(c.max_tokens);
        setDailyLimit(c.daily_request_limit);
        setCustomPrompt(c.custom_system_prompt || "");
        setLogAnalysisEnabled(c.log_analysis_enabled);
        setLogInterval(c.log_analysis_interval_minutes);
        setLogMaxLogs(c.log_analysis_max_logs);
      } else {
        console.error("Config yüklenemedi:", configRes.reason);
      }
    } catch (err) {
      console.error("AI config yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectedProvider = providers.find((p) => p.id === provider);

  // Kaydet
  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: any = {
        provider,
        base_url: baseUrl || null,
        model: model || null,
        chat_mode: chatMode,
        temperature,
        max_tokens: maxTokens,
        daily_request_limit: dailyLimit,
        custom_system_prompt: customPrompt || null,
        enabled,
        log_analysis_enabled: logAnalysisEnabled,
        log_analysis_interval_minutes: logInterval,
        log_analysis_max_logs: logMaxLogs,
      };
      if (apiKeyChanged && apiKey) {
        payload.api_key = apiKey;
      }
      await updateAiConfig(payload);
      setFeedback({ type: "success", message: "Ayarlar kaydedildi." });
      await loadAll();
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err.response?.data?.detail || "Ayarlar kaydedilemedi.",
      });
    } finally {
      setSaving(false);
    }
  };

  // Bağlantı testi
  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testAiConnection();
      setTestResult(res.data as AiTestResponse);
    } catch (err: any) {
      setTestResult({
        success: false,
        response: null,
        latency_ms: 0,
        model_used: null,
        error: err.response?.data?.detail || "Bağlantı testi başarısız.",
      });
    } finally {
      setTesting(false);
    }
  };

  // Sayac sıfırla
  const handleResetCounter = async () => {
    try {
      await resetAiCounter();
      setFeedback({ type: "success", message: "Günlük sayaç sıfırlandı." });
      const res = await fetchAiStats();
      setStats(res.data as AiStats);
    } catch {
      setFeedback({ type: "error", message: "Sayaç sıfırlanamadı." });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-neon-cyan animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6 p-4 md:p-6">
      <TopBar
        title="Yapay Zeka Ayarları"
        connected={connected}
      />

      {/* Geri bildirim */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border border-neon-red/20"
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

      {/* Tab navigasyonu */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 shadow-neon"
                : "text-gray-400 hover:text-white hover:bg-glass-light border border-transparent"
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Saglayici */}
      {activeTab === "provider" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <Server className="w-5 h-5 text-neon-cyan" />
              <h2 className="text-lg font-semibold text-white">AI Saglayici</h2>
            </div>

            <div className="space-y-4">
              {/* Provider secimi */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Saglayici
                </label>
                <select
                  value={provider}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setModel("");
                    setApiKey("");
                    setApiKeyChanged(false);
                    const p = providers.find((pr) => pr.id === e.target.value);
                    if (p?.default_base_url) setBaseUrl(p.default_base_url);
                    else setBaseUrl("");
                  }}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                >
                  <option value="none">Kapalı (Sadece TF-IDF)</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                {selectedProvider && (
                  <p className="text-xs text-gray-500 mt-1">
                    {selectedProvider.description}
                  </p>
                )}
              </div>

              {/* API Key */}
              {provider !== "none" &&
                selectedProvider?.requires_api_key !== false && (
                  <div>
                    <label className="block text-sm text-gray-400 mb-1.5">
                      API Anahtari
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => {
                          setApiKey(e.target.value);
                          setApiKeyChanged(true);
                        }}
                        placeholder="sk-..."
                        className="w-full px-3 py-2.5 pr-10 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50"
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                      >
                        {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>
                )}

              {/* Base URL (Ollama/Custom) */}
              {(provider === "ollama" || provider === "custom") && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">
                    Base URL
                  </label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                  />
                </div>
              )}

              {/* Etkinlestir toggle */}
              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-gray-300">
                  Yapay Zeka Etkin
                </span>
                <button
                  onClick={() => setEnabled(!enabled)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    enabled ? "bg-neon-cyan/30" : "bg-glass-light"
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-5 h-5 rounded-full transition-all ${
                      enabled
                        ? "left-[26px] bg-neon-cyan shadow-neon"
                        : "left-0.5 bg-gray-500"
                    }`}
                  />
                </button>
              </div>

              {/* Butonlar */}
              <div className="flex gap-3 pt-3">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
                >
                  {saving ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Save size={16} />
                  )}
                  Kaydet
                </button>
                <button
                  onClick={handleTest}
                  disabled={testing || provider === "none"}
                  className="flex items-center gap-2 px-4 py-2.5 bg-neon-green/10 text-neon-green border border-neon-green/30 rounded-xl text-sm font-medium hover:bg-neon-green/20 transition-all disabled:opacity-50"
                >
                  {testing ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Zap size={16} />
                  )}
                  Bağlantı Testi
                </button>
              </div>
            </div>
          </GlassCard>

          {/* Test Sonuçu + Son Test Bilgisi */}
          <div className="space-y-4 md:space-y-6">
            {/* Test sonuçu */}
            {testResult && (
              <GlassCard>
                <div className="flex items-center gap-3 mb-4">
                  {testResult.success ? (
                    <CheckCircle className="w-5 h-5 text-neon-green" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-neon-red" />
                  )}
                  <h3 className="text-lg font-semibold text-white">
                    Test Sonuçu
                  </h3>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Durum</span>
                    <span
                      className={
                        testResult.success ? "text-neon-green" : "text-neon-red"
                      }
                    >
                      {testResult.success ? "Başarılı" : "Başarısız"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Gecikme</span>
                    <span className="text-white">{testResult.latency_ms}ms</span>
                  </div>
                  {testResult.model_used && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Model</span>
                      <span className="text-white">{testResult.model_used}</span>
                    </div>
                  )}
                  {testResult.response && (
                    <div className="mt-3 p-3 bg-surface-700 rounded-lg">
                      <p className="text-xs text-gray-400 mb-1">Yanit:</p>
                      <p className="text-sm text-gray-200">
                        {testResult.response}
                      </p>
                    </div>
                  )}
                  {testResult.error && (
                    <div className="mt-3 p-3 bg-neon-red/5 border border-neon-red/20 rounded-lg">
                      <p className="text-sm text-neon-red">{testResult.error}</p>
                    </div>
                  )}
                </div>
              </GlassCard>
            )}

            {/* Son test bilgisi */}
            {config?.last_test_result && (
              <GlassCard>
                <div className="flex items-center gap-3 mb-3">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <h3 className="text-sm font-medium text-gray-300">
                    Son Test
                  </h3>
                </div>
                <p className="text-sm text-gray-400">{config.last_test_result}</p>
                {config.last_test_at && (
                  <p className="text-xs text-gray-600 mt-1">
                    {new Date(config.last_test_at).toLocaleString("tr-TR")}
                  </p>
                )}
              </GlassCard>
            )}

            {/* Bilgi karti */}
            <GlassCard>
              <div className="flex items-center gap-3 mb-3">
                <Brain className="w-4 h-4 text-neon-magenta" />
                <h3 className="text-sm font-medium text-gray-300">
                  Nasıl Çalışır?
                </h3>
              </div>
              <div className="text-xs text-gray-500 space-y-2">
                <p>
                  Yapay zeka etkinleştirildiğinde, AI Asistan (Chat) ve Telegram
                  Bot mesajlari secilen LLM saglayicisi üzerinden islenir.
                </p>
                <p>
                  <strong className="text-gray-400">TF-IDF:</strong> Yerel NLP motoru
                  (hizli, çevrimdışı, sifir maliyet)
                </p>
                <p>
                  <strong className="text-gray-400">LLM:</strong> Harici AI üzerinden
                  (akıllı, bağlamsal, API maliyeti)
                </p>
                <p>
                  <strong className="text-gray-400">Hibrit:</strong> Once LLM dener,
                  başarısız olursa TF-IDF'e doner
                </p>
              </div>
            </GlassCard>
          </div>
        </div>
      )}

      {/* Tab 2: Model Ayarları */}
      {activeTab === "model" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <Settings2 className="w-5 h-5 text-neon-cyan" />
              <h2 className="text-lg font-semibold text-white">
                Model Yapılandırma
              </h2>
            </div>

            <div className="space-y-4">
              {/* Model secimi */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                >
                  <option value="">Varsayilan</option>
                  {selectedProvider?.models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                      {m.context
                        ? ` (${Math.round(m.context / 1000)}K)`
                        : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sohbet Modu */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Sohbet Modu
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(
                    [
                      {
                        id: "tfidf" as const,
                        label: "TF-IDF",
                        desc: "Sadece yerel",
                      },
                      { id: "llm" as const, label: "LLM", desc: "Sadece AI" },
                      {
                        id: "hybrid" as const,
                        label: "Hibrit",
                        desc: "AI + Fallback",
                      },
                    ] as const
                  ).map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => setChatMode(mode.id)}
                      className={`p-3 rounded-xl border text-center transition-all ${
                        chatMode === mode.id
                          ? "bg-neon-cyan/10 border-neon-cyan/30 text-neon-cyan"
                          : "bg-surface-700 border-glass-border text-gray-400 hover:text-white hover:border-glass-border/50"
                      }`}
                    >
                      <div className="text-sm font-medium">{mode.label}</div>
                      <div className="text-xs mt-0.5 opacity-70">
                        {mode.desc}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Sıcaklık */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Sıcaklık:{" "}
                  <span className="text-neon-cyan">{temperature}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-neon-cyan"
                />
                <div className="flex justify-between text-xs text-gray-600">
                  <span>Tutarlı (0)</span>
                  <span>Yaratıcı (1)</span>
                </div>
              </div>

              {/* Maks Token */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Maks Token
                </label>
                <input
                  type="number"
                  value={maxTokens}
                  onChange={(e) =>
                    setMaxTokens(Math.max(64, parseInt(e.target.value) || 1024))
                  }
                  min={64}
                  max={8192}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                />
              </div>

              {/* Gunluk Limit */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Günlük İstek Limiti
                </label>
                <input
                  type="number"
                  value={dailyLimit}
                  onChange={(e) =>
                    setDailyLimit(Math.max(1, parseInt(e.target.value) || 200))
                  }
                  min={1}
                  max={10000}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                />
              </div>

              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Save size={16} />
                )}
                Kaydet
              </button>
            </div>
          </GlassCard>

          {/* Özel Sistem Promptu */}
          <GlassCard>
            <div className="flex items-center gap-3 mb-4">
              <Brain className="w-5 h-5 text-neon-magenta" />
              <h2 className="text-lg font-semibold text-white">
                Özel Sistem Promptu
              </h2>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Varsayılan sistem promptuna ek talimatlar ekleyin. LLM'in
              davranışını özelleştirmek için kullanabilirsiniz.
            </p>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Örneğin: Kullanıcıya her zaman resmi hitap et. Güvenlik uyarılarını kritik olarak işaretle..."
              rows={10}
              className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 resize-y"
            />
            <div className="flex justify-between items-center mt-3">
              <span className="text-xs text-gray-600">
                {customPrompt.length} karakter
              </span>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Save size={16} />
                )}
                Kaydet
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Tab 3: Log Analizi */}
      {activeTab === "log-analysis" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <FileSearch className="w-5 h-5 text-neon-cyan" />
              <h2 className="text-lg font-semibold text-white">
                LLM Log Analizi
              </h2>
            </div>

            <div className="space-y-4">
              {/* Etkinlestir toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-gray-300">
                    Log Analizi Etkin
                  </span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    DNS loglarını periyodik olarak LLM ile analiz et
                  </p>
                </div>
                <button
                  onClick={() => setLogAnalysisEnabled(!logAnalysisEnabled)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    logAnalysisEnabled ? "bg-neon-cyan/30" : "bg-glass-light"
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-5 h-5 rounded-full transition-all ${
                      logAnalysisEnabled
                        ? "left-[26px] bg-neon-cyan shadow-neon"
                        : "left-0.5 bg-gray-500"
                    }`}
                  />
                </button>
              </div>

              {/* Analiz aralığı */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Analiz Aralığı
                </label>
                <select
                  value={logInterval}
                  onChange={(e) => setLogInterval(parseInt(e.target.value))}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                >
                  <option value={15}>15 dakika</option>
                  <option value={30}>30 dakika</option>
                  <option value={60}>1 saat</option>
                  <option value={120}>2 saat</option>
                  <option value={360}>6 saat</option>
                </select>
              </div>

              {/* Maks log sayısı */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  Maks Log Sayısı
                </label>
                <input
                  type="number"
                  value={logMaxLogs}
                  onChange={(e) =>
                    setLogMaxLogs(
                      Math.max(10, parseInt(e.target.value) || 100)
                    )
                  }
                  min={10}
                  max={500}
                  className="w-full px-3 py-2.5 bg-[#1a1a2e] border border-glass-border rounded-xl text-white text-sm focus:outline-none focus:border-neon-cyan/50 [&>option]:bg-[#1a1a2e] [&>option]:text-white"
                />
                <p className="text-xs text-gray-600 mt-1">
                  Her analizde incelenecek son log sayısı (10-500)
                </p>
              </div>

              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Save size={16} />
                )}
                Kaydet
              </button>
            </div>
          </GlassCard>

          {/* Bilgi karti */}
          <GlassCard>
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-semibold text-white">
                Log Analizi Hakkında
              </h2>
            </div>
            <div className="text-sm text-gray-400 space-y-3">
              <p>
                LLM log analizi etkinleştirildiğinde, sistem periyodik olarak son
                DNS sorgu loglarını yapay zekaya gönderir ve analiz ettirir.
              </p>
              <div className="p-3 bg-surface-700 rounded-lg space-y-2">
                <p className="text-xs">
                  <strong className="text-neon-cyan">Neler Analiz Edilir:</strong>
                </p>
                <ul className="text-xs text-gray-500 list-disc list-inside space-y-1">
                  <li>Şüpheli DNS sorgu kalıpları (DGA, tünel)</li>
                  <li>Bilinen zararli domain bağlantılari</li>
                  <li>Gizlilik riski taşıyan trafik desenleri</li>
                  <li>Cihaz bazinda anormal davranislar</li>
                  <li>Optimizasyon firsatlari</li>
                </ul>
              </div>
              <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                <p className="text-xs text-amber-400">
                  <strong>Maliyet Uyarısı:</strong> Her analiz bir API çağrısı
                  tüketir. Kısa aralıklar daha fazla maliyet oluşturur. Gunluk
                  istek limitini ayarlamayı unutmayın.
                </p>
              </div>
              <p className="text-xs text-gray-500">
                Analiz bulguları otomatik olarak AI Insights sayfasında "[LLM
                Analiz]" önekiyle görünür. Telegram bildirimi etkinse ayrica
                bildirim gönderilir.
              </p>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Tab 4: İstatistikler */}
      {activeTab === "stats" && (
        <div className="space-y-4 md:space-y-6">
          {/* Stat kartlari */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Günlük İstek"
              value={`${stats?.daily_request_count || 0} / ${stats?.daily_request_limit || 200}`}
              icon={<Activity size={20} />}
              neonColor="cyan"
            />
            <StatCard
              title="Kalan"
              value={`${stats?.remaining_today || 0}`}
              icon={<Zap size={20} />}
              neonColor="green"
            />
            <StatCard
              title="Saglayici"
              value={
                stats?.provider === "none"
                  ? "Kapali"
                  : providers.find((p) => p.id === stats?.provider)?.name ||
                    stats?.provider ||
                    "-"
              }
              icon={<Server size={20} />}
              neonColor="magenta"
            />
            <StatCard
              title="Sohbet Modu"
              value={
                stats?.chat_mode === "tfidf"
                  ? "TF-IDF"
                  : stats?.chat_mode === "llm"
                  ? "LLM"
                  : stats?.chat_mode === "hybrid"
                  ? "Hibrit"
                  : "-"
              }
              icon={<Cpu size={20} />}
              neonColor="amber"
            />
          </div>

          {/* Detay karti */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            <GlassCard>
              <div className="flex items-center gap-3 mb-4">
                <BarChart3 className="w-5 h-5 text-neon-cyan" />
                <h2 className="text-lg font-semibold text-white">
                  Kullanım Detaylari
                </h2>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between py-2 border-b border-glass-border">
                  <span className="text-gray-400">Durum</span>
                  <span
                    className={
                      stats?.enabled ? "text-neon-green" : "text-gray-500"
                    }
                  >
                    {stats?.enabled ? "Etkin" : "Devre Dışı"}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-glass-border">
                  <span className="text-gray-400">Saglayici</span>
                  <span className="text-white">
                    {providers.find((p) => p.id === stats?.provider)?.name ||
                      stats?.provider ||
                      "-"}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-glass-border">
                  <span className="text-gray-400">Model</span>
                  <span className="text-white">{stats?.model || "Varsayilan"}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-glass-border">
                  <span className="text-gray-400">Sohbet Modu</span>
                  <span className="text-white">
                    {stats?.chat_mode === "tfidf"
                      ? "TF-IDF (Yerel)"
                      : stats?.chat_mode === "llm"
                      ? "LLM (Harici AI)"
                      : stats?.chat_mode === "hybrid"
                      ? "Hibrit (AI + Fallback)"
                      : "-"}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-glass-border">
                  <span className="text-gray-400">Günlük Kullanım</span>
                  <span className="text-white">
                    {stats?.daily_request_count || 0} /{" "}
                    {stats?.daily_request_limit || 200}
                  </span>
                </div>
                {stats?.last_test_at && (
                  <div className="flex justify-between py-2">
                    <span className="text-gray-400">Son Test</span>
                    <span className="text-white">
                      {new Date(stats.last_test_at).toLocaleString("tr-TR")}
                    </span>
                  </div>
                )}
              </div>
            </GlassCard>

            <GlassCard>
              <div className="flex items-center gap-3 mb-4">
                <RefreshCw className="w-5 h-5 text-neon-magenta" />
                <h2 className="text-lg font-semibold text-white">
                  İşlemler
                </h2>
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-surface-700 rounded-xl">
                  <p className="text-sm text-gray-300 mb-3">
                    Gunluk istek sayacıni sıfırlamak için aşağıdaki butonu
                    kullanın. Sayaç her gün otomatik olarak sıfırlanır.
                  </p>
                  <button
                    onClick={handleResetCounter}
                    className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-xl text-sm font-medium hover:bg-amber-500/20 transition-all"
                  >
                    <RefreshCw size={16} />
                    Sayacı Sıfırla
                  </button>
                </div>

                {/* Kullanım ilerleme cubugu */}
                {stats && (
                  <div className="p-4 bg-surface-700 rounded-xl">
                    <div className="flex justify-between text-xs text-gray-400 mb-2">
                      <span>Günlük Kullanım</span>
                      <span>
                        {stats.daily_request_count} / {stats.daily_request_limit}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-glass-light rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          (stats.daily_request_count /
                            stats.daily_request_limit) *
                            100 >
                          80
                            ? "bg-neon-red"
                            : (stats.daily_request_count /
                                stats.daily_request_limit) *
                                100 >
                              50
                            ? "bg-amber-400"
                            : "bg-neon-cyan"
                        }`}
                        style={{
                          width: `${Math.min(
                            100,
                            (stats.daily_request_count /
                              stats.daily_request_limit) *
                              100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </div>
  );
}
