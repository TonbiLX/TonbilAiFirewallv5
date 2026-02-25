// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Telegram Bot ayar sayfası: bot config, bildirim ayarları, test, rehber

import { useEffect, useState } from "react";
import {
  Send,
  Bot,
  Bell,
  BookOpen,
  Eye,
  EyeOff,
  CheckCircle,
  AlertTriangle,
  Save,
  Loader2,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchTelegramConfig,
  updateTelegramConfig,
  testTelegram,
} from "../services/telegramApi";
import type { TelegramConfig } from "../types";

export function TelegramPage() {
  const { connected } = useWebSocket();
  const [config, setConfig] = useState<TelegramConfig | null>(null);
  const [loading, setLoading] = useState(true);

  // Form alanlari
  const [botToken, setBotToken] = useState("");
  const [chatIds, setChatIds] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [notifyNewDevice, setNotifyNewDevice] = useState(true);
  const [notifyBlockedIp, setNotifyBlockedIp] = useState(true);
  const [notifyTrustedIpThreat, setNotifyTrustedIpThreat] = useState(true);
  const [notifyAiInsight, setNotifyAiInsight] = useState(true);
  const [showToken, setShowToken] = useState(false);
  const [tokenChanged, setTokenChanged] = useState(false);

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  // Veri yukle
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await fetchTelegramConfig();
      const data = res.data as TelegramConfig;
      setConfig(data);
      setBotToken(data.bot_token_masked || "");
      setChatIds(data.chat_ids || "");
      setEnabled(data.enabled);
      setNotifyNewDevice(data.notify_new_device);
      setNotifyBlockedIp(data.notify_blocked_ip);
      setNotifyTrustedIpThreat(data.notify_trusted_ip_threat);
      setNotifyAiInsight(data.notify_ai_insight);
      setTokenChanged(false);
    } catch (err) {
      console.error("Telegram config yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  };

  // Geri bildirim zamanlayici
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // Bot ayarlarıni kaydet
  const handleSaveBotSettings = async () => {
    setSaving(true);
    try {
      const payload: any = {
        chat_ids: chatIds,
        enabled,
      };
      // Token degistiyse ekle
      if (tokenChanged && botToken) {
        payload.bot_token = botToken;
      }
      await updateTelegramConfig(payload);
      setFeedback({ type: "success", message: "Bot ayarları kaydedildi." });
      await loadConfig();
    } catch (err) {
      setFeedback({ type: "error", message: "Ayarlar kaydedilemedi." });
    } finally {
      setSaving(false);
    }
  };

  // Bildirim ayarlarıni kaydet
  const handleSaveNotifications = async () => {
    setSaving(true);
    try {
      await updateTelegramConfig({
        notify_new_device: notifyNewDevice,
        notify_blocked_ip: notifyBlockedIp,
        notify_trusted_ip_threat: notifyTrustedIpThreat,
        notify_ai_insight: notifyAiInsight,
      });
      setFeedback({
        type: "success",
        message: "Bildirim ayarları kaydedildi.",
      });
      await loadConfig();
    } catch (err) {
      setFeedback({
        type: "error",
        message: "Bildirim ayarları kaydedilemedi.",
      });
    } finally {
      setSaving(false);
    }
  };

  // Test mesaji gönder
  const handleTest = async () => {
    setTesting(true);
    try {
      await testTelegram();
      setFeedback({ type: "success", message: "Test mesajı gönderildi!" });
    } catch (err: any) {
      const detail =
        err.response?.data?.detail || "Test mesajı gönderilemedi.";
      setFeedback({ type: "error", message: detail });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <TopBar title="Telegram Bot" connected={connected} />

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Kart 1: Bot Ayarları */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <Bot size={24} className="text-neon-cyan" />
            <h3 className="text-lg font-semibold">Bot Ayarları</h3>
          </div>

          <div className="space-y-4">
            {/* Bot Token */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">
                Bot Token
              </label>
              <div className="relative">
                <input
                  type={showToken ? "text" : "password"}
                  value={botToken}
                  onChange={(e) => {
                    setBotToken(e.target.value);
                    setTokenChanged(true);
                  }}
                  placeholder="7123456789:AAF..."
                  className="w-full pr-10 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
                <button
                  onClick={() => setShowToken(!showToken)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                >
                  {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Chat ID'ler */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">
                Chat ID'ler
              </label>
              <input
                type="text"
                value={chatIds}
                onChange={(e) => setChatIds(e.target.value)}
                placeholder="123456789, 987654321"
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
              />
              <p className="text-xs text-gray-500 mt-1">
                Birden fazla ID için virgül ile ayirin
              </p>
            </div>

            {/* Etkin/Devre disi toggle */}
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-gray-300">Bot Aktif</span>
              <button
                onClick={() => setEnabled(!enabled)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  enabled ? "bg-neon-cyan/30" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                    enabled
                      ? "translate-x-6 bg-neon-cyan"
                      : "translate-x-0 bg-gray-500"
                  }`}
                />
              </button>
            </div>

            <button
              onClick={handleSaveBotSettings}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30 rounded-xl hover:bg-neon-cyan/30 transition-all disabled:opacity-50"
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

        {/* Kart 2: Bildirim Ayarları */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <Bell size={24} className="text-neon-amber" />
            <h3 className="text-lg font-semibold">Bildirim Ayarları</h3>
          </div>

          <div className="space-y-4">
            {/* Yeni cihaz bildirimi */}
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <div>
                <p className="text-sm text-gray-300">
                  Yeni Cihaz Bildirimi
                </p>
                <p className="text-xs text-gray-500">
                  Ağa yeni bir cihaz bağlandığında bildirim gönder
                </p>
              </div>
              <button
                onClick={() => setNotifyNewDevice(!notifyNewDevice)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifyNewDevice ? "bg-neon-green/30" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                    notifyNewDevice
                      ? "translate-x-6 bg-neon-green"
                      : "translate-x-0 bg-gray-500"
                  }`}
                />
              </button>
            </div>

            {/* Tehdit engelleme bildirimi */}
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <div>
                <p className="text-sm text-gray-300">
                  Tehdit Engelleme Bildirimi
                </p>
                <p className="text-xs text-gray-500">
                  Bir IP engellendiğinde bildirim gönder
                </p>
              </div>
              <button
                onClick={() => setNotifyBlockedIp(!notifyBlockedIp)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifyBlockedIp ? "bg-neon-green/30" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                    notifyBlockedIp
                      ? "translate-x-6 bg-neon-green"
                      : "translate-x-0 bg-gray-500"
                  }`}
                />
              </button>
            </div>

            {/* Güvenilir IP tehdit uyarısı */}
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <div>
                <p className="text-sm text-gray-300">
                  Güvenilir IP Tehdit Uyarısı
                </p>
                <p className="text-xs text-gray-500">
                  Güvenilir IP'lerden tehdit algilandiginda bildirim gönder
                </p>
              </div>
              <button
                onClick={() => setNotifyTrustedIpThreat(!notifyTrustedIpThreat)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifyTrustedIpThreat ? "bg-neon-green/30" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                    notifyTrustedIpThreat
                      ? "translate-x-6 bg-neon-green"
                      : "translate-x-0 bg-gray-500"
                  }`}
                />
              </button>
            </div>

            {/* AI Uyari bildirimi */}
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <div>
                <p className="text-sm text-gray-300">
                  AI Uyari Bildirimi
                </p>
                <p className="text-xs text-gray-500">
                  AI tehdit analizinden gelen tüm uyarılar için bildirim gönder
                </p>
              </div>
              <button
                onClick={() => setNotifyAiInsight(!notifyAiInsight)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  notifyAiInsight ? "bg-neon-green/30" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                    notifyAiInsight
                      ? "translate-x-6 bg-neon-green"
                      : "translate-x-0 bg-gray-500"
                  }`}
                />
              </button>
            </div>

            <button
              onClick={handleSaveNotifications}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-neon-amber/20 text-neon-amber border border-neon-amber/30 rounded-xl hover:bg-neon-amber/30 transition-all disabled:opacity-50"
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

        {/* Kart 3: Test */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <Send size={24} className="text-neon-green" />
            <h3 className="text-lg font-semibold">Test Mesaji</h3>
          </div>

          <p className="text-sm text-gray-400 mb-4">
            Bot yapılandırmanızı test etmek için bir deneme mesajı gönderin.
          </p>

          <button
            onClick={handleTest}
            disabled={testing}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-neon-green/20 text-neon-green border border-neon-green/30 rounded-xl hover:bg-neon-green/30 transition-all disabled:opacity-50"
          >
            {testing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
            Test Mesajı Gönder
          </button>
        </GlassCard>

        {/* Kart 4: Nasil Yapilir Rehberi */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <BookOpen size={24} className="text-neon-magenta" />
            <h3 className="text-lg font-semibold">Nasil Yapilir?</h3>
          </div>

          <div className="space-y-6 text-sm">
            {/* Bot Token Alma */}
            <div>
              <h4 className="text-neon-cyan font-semibold mb-2">
                Bot Token Alma
              </h4>
              <ol className="list-decimal list-inside space-y-1.5 text-gray-400">
                <li>
                  Telegram'da{" "}
                  <code className="text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded">
                    @BotFather
                  </code>
                  'a mesaj at
                </li>
                <li>
                  <code className="text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded">
                    /newbot
                  </code>{" "}
                  komutunu yaz
                </li>
                <li>Bot için bir isim gir (örneğin: TonbilAiOS Router)</li>
                <li>
                  Bot için bir kullanıcı adı gir (örneğin:
                  tonbilai_router_bot)
                </li>
                <li>
                  BotFather sana bir API token verecek (örnek:{" "}
                  <code className="text-neon-amber bg-neon-amber/10 px-1.5 py-0.5 rounded">
                    7123456789:AAF...
                  </code>
                  )
                </li>
                <li>Bu token'i yukarıdaki "Bot Token" alanına yapıştır</li>
              </ol>
            </div>

            {/* Chat ID Alma */}
            <div>
              <h4 className="text-neon-cyan font-semibold mb-2">
                Chat ID Alma
              </h4>
              <ol className="list-decimal list-inside space-y-1.5 text-gray-400">
                <li>
                  Telegram'da{" "}
                  <code className="text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded">
                    @userinfobot
                  </code>
                  'a mesaj at (veya{" "}
                  <code className="text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded">
                    @raw_data_bot
                  </code>
                  )
                </li>
                <li>
                  Bot sana Chat ID'ni gosterecek (örnek:{" "}
                  <code className="text-neon-amber bg-neon-amber/10 px-1.5 py-0.5 rounded">
                    123456789
                  </code>
                  )
                </li>
                <li>Bu ID'yi yukarıdaki "Chat ID" alanına yapıştır</li>
                <li>
                  Birden fazla kişi için: her Chat ID'yi virgülle ayır
                  <br />
                  <span className="text-gray-500">
                    Ornek:{" "}
                    <code className="text-neon-amber bg-neon-amber/10 px-1.5 py-0.5 rounded">
                      123456789, 987654321
                    </code>
                  </span>
                </li>
              </ol>
            </div>

            {/* Grup Chat ID Alma */}
            <div>
              <h4 className="text-neon-cyan font-semibold mb-2">
                Grup Chat ID Alma
              </h4>
              <ol className="list-decimal list-inside space-y-1.5 text-gray-400">
                <li>Botu gruba ekle</li>
                <li>Grupta herhangi bir mesaj yaz</li>
                <li>
                  Tarayıcıda şu adresi aç:
                  <br />
                  <code className="text-neon-amber bg-neon-amber/10 px-1.5 py-0.5 rounded text-xs break-all">
                    {"https://api.telegram.org/bot<TOKEN>/getUpdates"}
                  </code>
                </li>
                <li>
                  <code className="text-neon-amber bg-neon-amber/10 px-1.5 py-0.5 rounded">
                    {"\"chat\":{\"id\":-XXXXXXXXX}"}
                  </code>{" "}
                  degerini bul
                  <br />
                  <span className="text-gray-500">
                    (gruplar eksi ile başlar)
                  </span>
                </li>
                <li>Bu değeri Chat ID alanına ekle</li>
              </ol>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
