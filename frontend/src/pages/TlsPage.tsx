// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// TLS Şifreleme sayfası: AdGuard Home tarzi sertifika yapıştırma/yükleme,
// doğrulama göstergesi, DNS-over-TLS, Let's Encrypt

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Lock,
  Unlock,
  Globe,
  Shield,
  ShieldCheck,
  ShieldX,
  Mail,
  FileKey,
  CheckCircle,
  AlertTriangle,
  Upload,
  Smartphone,
  FileText,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchTlsConfig,
  updateTlsConfig,
  validateCertificate,
  uploadCertificateFiles,
  requestLetsEncrypt,
  toggleTlsEncryption,
} from "../services/tlsApi";
import type { TlsConfig, TlsValidateResponse } from "../services/tlsApi";

export function TlsPage() {
  const { connected } = useWebSocket();
  const [config, setConfig] = useState<TlsConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Domain
  const [domainInput, setDomainInput] = useState("");
  const [dotPortInput, setDotPortInput] = useState("853");

  // Sertifika yapıştırma
  const [certInput, setCertInput] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [validationResult, setValidationResult] =
    useState<TlsValidateResponse | null>(null);
  const [validating, setValidating] = useState(false);

  // Dosya yükleme
  const certFileRef = useRef<HTMLInputElement>(null);
  const keyFileRef = useRef<HTMLInputElement>(null);

  // Let's Encrypt
  const [letsEncryptEmail, setLetsEncryptEmail] = useState("");
  const [requestingCert, setRequestingCert] = useState(false);

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  const loadData = useCallback(async () => {
    try {
      const data = await fetchTlsConfig();
      setConfig(data);
      setDomainInput(data.domain || "");
      setDotPortInput(data.dot_port?.toString() || "853");
      setLetsEncryptEmail(data.lets_encrypt_email || "");
      if (data.certificate_chain) setCertInput(data.certificate_chain);
      if (data.private_key) setKeyInput(data.private_key);
      if (data.cert_valid) {
        setValidationResult({
          valid: true,
          subject: data.cert_subject,
          issuer: data.cert_issuer,
          not_before: data.cert_not_before,
          not_after: data.cert_not_after,
          domain_match: null,
          error: null,
        });
      }
    } catch {
      setFeedback({ type: "error", message: "TLS yapılandirmasi yüklenemedi" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // --- Sertifika doğrulama ---
  const handleValidateCert = async () => {
    if (!certInput.trim() || !keyInput.trim()) {
      setFeedback({
        type: "error",
        message: "Sertifika ve özel anahtar alanlari bos olamaz.",
      });
      return;
    }
    setValidating(true);
    try {
      const result = await validateCertificate({
        certificate_chain: certInput.trim(),
        private_key: keyInput.trim(),
        domain: domainInput.trim() || undefined,
      });
      setValidationResult(result);
      if (!result.valid) {
        setFeedback({
          type: "error",
          message: result.error || "Sertifika dogrulanamadi.",
        });
      }
    } catch {
      setFeedback({ type: "error", message: "Doğrulama istegi başarısız." });
    } finally {
      setValidating(false);
    }
  };

  // --- Sertifika kaydet ---
  const handleSaveCert = async () => {
    if (!validationResult?.valid) {
      setFeedback({
        type: "error",
        message: "Once sertifikayi dogrulayin.",
      });
      return;
    }
    setSaving(true);
    try {
      await updateTlsConfig({
        certificate_chain: certInput.trim(),
        private_key: keyInput.trim(),
        domain: domainInput.trim() || undefined,
      });
      await loadData();
      setFeedback({
        type: "success",
        message: "Sertifika başarıyla kaydedildi.",
      });
    } catch {
      setFeedback({ type: "error", message: "Sertifika kaydedilemedi." });
    } finally {
      setSaving(false);
    }
  };

  // --- Dosya yükleme ---
  const handleFileUpload = async () => {
    const certFile = certFileRef.current?.files?.[0];
    const keyFile = keyFileRef.current?.files?.[0];
    if (!certFile || !keyFile) {
      setFeedback({
        type: "error",
        message: "Sertifika ve anahtar dosyalarini seçin.",
      });
      return;
    }
    setSaving(true);
    try {
      await uploadCertificateFiles(certFile, keyFile);
      await loadData();
      setFeedback({
        type: "success",
        message: "Sertifika dosyalari başarıyla yuklendi.",
      });
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail;
      setFeedback({
        type: "error",
        message: detail || "Dosya yükleme başarısız.",
      });
    } finally {
      setSaving(false);
    }
  };

  // --- Toggle'lar ---
  const handleToggleEncryption = async () => {
    setSaving(true);
    try {
      const result = await toggleTlsEncryption();
      await loadData();
      setFeedback({ type: "success", message: result.message });
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail;
      setFeedback({
        type: "error",
        message: detail || "Durum değiştirilemedi.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleDoT = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await updateTlsConfig({ dot_enabled: !config.dot_enabled });
      await loadData();
      setFeedback({
        type: "success",
        message: config.dot_enabled
          ? "DoT devre disi birakildi."
          : "DoT etkinlestirildi.",
      });
    } catch {
      setFeedback({ type: "error", message: "Güncelleme başarısız." });
    } finally {
      setSaving(false);
    }
  };

  // --- Domain kaydet ---
  const handleSaveDomain = async () => {
    if (!domainInput.trim()) return;
    setSaving(true);
    try {
      await updateTlsConfig({
        domain: domainInput.trim(),
        dot_port: parseInt(dotPortInput) || 853,
      });
      await loadData();
      setFeedback({ type: "success", message: "Domain kaydedildi." });
    } catch {
      setFeedback({ type: "error", message: "Domain kaydedilemedi." });
    } finally {
      setSaving(false);
    }
  };

  // --- Let's Encrypt ---
  const handleRequestCert = async () => {
    if (!config?.domain) {
      setFeedback({
        type: "error",
        message: "Once domain adi belirleyin.",
      });
      return;
    }
    setRequestingCert(true);
    try {
      // Email'i once kaydet
      if (letsEncryptEmail.trim()) {
        await updateTlsConfig({
          lets_encrypt_email: letsEncryptEmail.trim(),
        });
      }
      const result = await requestLetsEncrypt();
      await loadData();
      setFeedback({
        type: result.status === "success" ? "success" : "success",
        message: result.message,
      });
    } catch (err: unknown) {
      const detail =
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail;
      setFeedback({
        type: "error",
        message: detail || "Sertifika talebi başarısız.",
      });
    } finally {
      setRequestingCert(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const inputClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors";

  const textareaClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors resize-y";

  const ToggleButton = ({
    enabled,
    onClick,
    disabled,
    color = "green",
  }: {
    enabled: boolean;
    onClick: () => void;
    disabled?: boolean;
    color?: "green" | "cyan" | "magenta";
  }) => {
    const colorMap = {
      green: {
        bg: "bg-neon-green/30",
        dot: "bg-neon-green shadow-[0_0_8px_rgba(57,255,20,0.5)]",
      },
      cyan: {
        bg: "bg-neon-cyan/30",
        dot: "bg-neon-cyan shadow-[0_0_8px_rgba(0,240,255,0.5)]",
      },
      magenta: {
        bg: "bg-neon-magenta/30",
        dot: "bg-neon-magenta shadow-[0_0_8px_rgba(255,0,229,0.5)]",
      },
    };
    const c = colorMap[color];
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className={`relative w-12 h-6 rounded-full transition-colors disabled:opacity-50 ${
          enabled ? c.bg : "bg-gray-700"
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
            enabled ? `translate-x-6 ${c.dot}` : "bg-gray-500"
          }`}
        />
      </button>
    );
  };

  const formatDate = (d: string | null) => {
    if (!d) return "-";
    return new Date(d).toLocaleDateString("tr-TR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const isCertExpiringSoon = () => {
    if (!config?.cert_not_after) return false;
    const expiry = new Date(config.cert_not_after);
    const daysLeft = (expiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24);
    return daysLeft < 30;
  };

  return (
    <div className="space-y-6">
      <TopBar title="TLS / DNS Şifreleme" connected={connected} />

      <div className="flex items-center gap-3 mb-2">
        <Lock size={28} className="text-neon-cyan" />
        <div>
          <h2 className="text-xl font-bold text-white">
            TLS Şifreleme Ayarları
          </h2>
          <p className="text-sm text-gray-400">
            DNS-over-TLS (DoT), sertifika yönetimi ve Android Özel DNS
          </p>
        </div>
      </div>

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

      {config && (
        <div className="space-y-6">
          {/* ===== ANA TOGGLE ===== */}
          <GlassCard neonColor={config.enabled ? "green" : undefined}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {config.enabled ? (
                  <ShieldCheck size={24} className="text-neon-green" />
                ) : (
                  <Unlock size={24} className="text-gray-500" />
                )}
                <div>
                  <h3 className="text-base font-semibold text-white">
                    DNS Şifreleme (DoT)
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {config.enabled
                      ? "DNS-over-TLS aktif. Port 853 üzerinden şifrelenmis DNS."
                      : "Şifreleme pasif. Etkinlestirmek için gecerli sertifika yükleyin."}
                  </p>
                </div>
              </div>
              <ToggleButton
                enabled={config.enabled}
                onClick={handleToggleEncryption}
                disabled={saving}
                color="green"
              />
            </div>
          </GlassCard>

          {/* ===== DOMAIN + PORT ===== */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Globe size={18} className="text-neon-cyan" />
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Domain ve Port Ayarları
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-400 mb-1">
                  Domain
                </label>
                <input
                  type="text"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  placeholder="guard.tonbilx.com"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  DoT Portu
                </label>
                <input
                  type="number"
                  value={dotPortInput}
                  onChange={(e) => setDotPortInput(e.target.value)}
                  placeholder="853"
                  min={1}
                  max={65535}
                  className={inputClass}
                />
              </div>
            </div>
            <button
              onClick={handleSaveDomain}
              disabled={saving || !domainInput.trim()}
              className="mt-3 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-lg text-sm transition-all disabled:opacity-50"
            >
              Kaydet
            </button>
          </GlassCard>

          {/* ===== SERTIFIKA DURUMU ===== */}
          {config.cert_valid && (
            <GlassCard
              neonColor={isCertExpiringSoon() ? "amber" : "green"}
            >
              <div className="flex items-center gap-2 mb-4">
                <ShieldCheck
                  size={18}
                  className={
                    isCertExpiringSoon()
                      ? "text-neon-amber"
                      : "text-neon-green"
                  }
                />
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                  Aktif Sertifika
                </h3>
                <NeonBadge
                  label={isCertExpiringSoon() ? "SONA YAKLASIYOR" : "GECERLI"}
                  variant={isCertExpiringSoon() ? "amber" : "green"}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-3 bg-surface-800 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Konu (Subject)</p>
                  <p className="text-sm font-mono text-white truncate">
                    {config.cert_subject || "-"}
                  </p>
                </div>
                <div className="p-3 bg-surface-800 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Veren (Issuer)</p>
                  <p className="text-sm font-mono text-white truncate">
                    {config.cert_issuer || "-"}
                  </p>
                </div>
                <div className="p-3 bg-surface-800 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Gecerlilik Başlangici</p>
                  <p className="text-sm text-white">
                    {formatDate(config.cert_not_before)}
                  </p>
                </div>
                <div className="p-3 bg-surface-800 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Gecerlilik Sonu</p>
                  <p
                    className={`text-sm font-medium ${
                      isCertExpiringSoon() ? "text-neon-amber" : "text-neon-green"
                    }`}
                  >
                    {formatDate(config.cert_not_after)}
                  </p>
                </div>
              </div>
            </GlassCard>
          )}

          {/* ===== SERTIFIKA YAPISTIRMA ===== */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <FileText size={18} className="text-neon-cyan" />
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Sertifika Yapistir (PEM)
              </h3>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Sertifika Zinciri */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Sertifika Zinciri (fullchain.pem)
                </label>
                <textarea
                  value={certInput}
                  onChange={(e) => {
                    setCertInput(e.target.value);
                    setValidationResult(null);
                  }}
                  placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                  rows={8}
                  className={textareaClass}
                />
              </div>

              {/* Özel Anahtar */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Özel Anahtar (privkey.pem)
                </label>
                <textarea
                  value={keyInput}
                  onChange={(e) => {
                    setKeyInput(e.target.value);
                    setValidationResult(null);
                  }}
                  placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
                  rows={8}
                  className={textareaClass}
                />
              </div>
            </div>

            {/* Doğrulama Sonuçu */}
            {validationResult && (
              <div
                className={`mt-4 p-3 rounded-lg border ${
                  validationResult.valid
                    ? "bg-neon-green/5 border-neon-green/20"
                    : "bg-neon-red/5 border-neon-red/20"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {validationResult.valid ? (
                    <ShieldCheck size={16} className="text-neon-green" />
                  ) : (
                    <ShieldX size={16} className="text-neon-red" />
                  )}
                  <span
                    className={`text-sm font-medium ${
                      validationResult.valid
                        ? "text-neon-green"
                        : "text-neon-red"
                    }`}
                  >
                    {validationResult.valid
                      ? "Sertifika Gecerli"
                      : "Sertifika Geçersiz"}
                  </span>
                  {validationResult.domain_match !== null && (
                    <NeonBadge
                      label={
                        validationResult.domain_match
                          ? "DOMAIN ESLESTI"
                          : "DOMAIN ESLESMEDI"
                      }
                      variant={
                        validationResult.domain_match ? "green" : "amber"
                      }
                    />
                  )}
                </div>
                {validationResult.valid && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500">Subject: </span>
                      <span className="text-white">
                        {validationResult.subject}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Issuer: </span>
                      <span className="text-white">
                        {validationResult.issuer}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Gecerli: </span>
                      <span className="text-white">
                        {formatDate(validationResult.not_before)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Sona Erer: </span>
                      <span className="text-white">
                        {formatDate(validationResult.not_after)}
                      </span>
                    </div>
                  </div>
                )}
                {validationResult.error && (
                  <p className="text-xs text-neon-red mt-1">
                    {validationResult.error}
                  </p>
                )}
              </div>
            )}

            {/* Butonlar */}
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleValidateCert}
                disabled={
                  validating || !certInput.trim() || !keyInput.trim()
                }
                className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-lg text-sm transition-all disabled:opacity-50"
              >
                {validating ? (
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                ) : (
                  <Shield size={14} />
                )}
                Dogrula
              </button>
              <button
                onClick={handleSaveCert}
                disabled={saving || !validationResult?.valid}
                className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 hover:bg-neon-green/20 border border-neon-green/30 text-neon-green rounded-lg text-sm transition-all disabled:opacity-50"
              >
                <CheckCircle size={14} />
                Kaydet ve Uygula
              </button>
            </div>
          </GlassCard>

          {/* ===== DOSYA YUKLEME ===== */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Upload size={18} className="text-neon-magenta" />
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Sertifika Dosyasi Yukle
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Sertifika (fullchain.pem)
                </label>
                <input
                  ref={certFileRef}
                  type="file"
                  accept=".pem,.crt,.cer"
                  className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border file:border-glass-border file:text-sm file:bg-surface-800 file:text-gray-300 hover:file:bg-surface-700"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Özel Anahtar (privkey.pem)
                </label>
                <input
                  ref={keyFileRef}
                  type="file"
                  accept=".pem,.key"
                  className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border file:border-glass-border file:text-sm file:bg-surface-800 file:text-gray-300 hover:file:bg-surface-700"
                />
              </div>
            </div>
            <button
              onClick={handleFileUpload}
              disabled={saving}
              className="mt-3 flex items-center gap-2 px-4 py-2 bg-neon-magenta/10 hover:bg-neon-magenta/20 border border-neon-magenta/30 text-neon-magenta rounded-lg text-sm transition-all disabled:opacity-50"
            >
              <Upload size={14} />
              Yukle ve Dogrula
            </button>
          </GlassCard>

          {/* ===== LET'S ENCRYPT ===== */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <FileKey size={18} className="text-neon-cyan" />
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Let's Encrypt ile Otomatik Sertifika
              </h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Domain adiniz bu sunucuya DNS ile yonlendirilmis olmalıdır. certbot
              veya openssl kullanilarak sertifika uretilir.
            </p>
            <div className="flex gap-3 items-end mb-4">
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  E-posta (bildirimler için)
                </label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="email"
                    value={letsEncryptEmail}
                    onChange={(e) => setLetsEncryptEmail(e.target.value)}
                    placeholder="admin@ornek.com"
                    className={`${inputClass} pl-10`}
                  />
                </div>
              </div>
            </div>
            <button
              onClick={handleRequestCert}
              disabled={requestingCert || !config.domain}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
            >
              {requestingCert ? (
                <>
                  <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                  Sertifika Oluşturuluyor...
                </>
              ) : (
                <>
                  <ShieldCheck size={16} />
                  Sertifika Oluştur
                </>
              )}
            </button>
            {!config.domain && (
              <p className="text-xs text-neon-amber mt-2">
                Once domain adi belirleyin.
              </p>
            )}
          </GlassCard>

          {/* ===== ANDROID OZEL DNS ===== */}
          <GlassCard>
            <div className="flex items-start gap-3">
              <Smartphone
                size={20}
                className="text-neon-cyan mt-0.5 flex-shrink-0"
              />
              <div>
                <h4 className="text-sm font-semibold text-white mb-2">
                  Android Özel DNS (Private DNS)
                </h4>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Android cihazlarda{" "}
                  <span className="text-gray-300 font-medium">
                    Ayarlar &gt; Ag &gt; Özel DNS
                  </span>{" "}
                  kismina aşağıdaki adresi girin:
                </p>
                {config.domain && config.enabled && config.cert_valid ? (
                  <div className="mt-3 p-3 bg-surface-800 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">
                      Özel DNS Adresi:
                    </p>
                    <p className="text-lg font-mono text-neon-cyan font-bold">
                      {config.domain}
                    </p>
                    <div className="flex items-center gap-1 mt-1">
                      <CheckCircle size={12} className="text-neon-green" />
                      <span className="text-xs text-neon-green">
                        DoT aktif, sertifika gecerli
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 p-2 bg-neon-amber/5 border border-neon-amber/20 rounded-lg">
                    <p className="text-xs text-neon-amber">
                      {!config.cert_valid
                        ? "Gecerli bir sertifika yükleyin."
                        : !config.enabled
                          ? "Şifrelemeyi etkinlestirin."
                          : "Domain adi belirleyin."}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
