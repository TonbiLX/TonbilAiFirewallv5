// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Kullanıcı ayarları sayfası: Profil bilgileri + şifre değiştirme
// Uzaktan erişim için güvenli kullanıcı yönetimi

import { useState, useEffect, useCallback } from "react";
import {
  User,
  KeyRound,
  Save,
  Eye,
  EyeOff,
  Shield,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import { authApi } from "../services/authApi";
import type { UserProfile } from "../services/authApi";
import { getUser, saveUser, isRemembered } from "../services/tokenStore";

export function SettingsPage() {
  const { connected } = useWebSocket();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Profil formu
  const [displayName, setDisplayName] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);

  // Şifre formu
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);

  // Feedback
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadProfile = useCallback(async () => {
    try {
      const { data } = await authApi.getProfile();
      setProfile(data);
      setDisplayName(data.display_name || "");
    } catch (err) {
      console.error("Profil yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleProfileSave = async () => {
    if (!displayName.trim()) return;
    setProfileSaving(true);
    try {
      const { data } = await authApi.updateProfile({
        display_name: displayName.trim(),
      });
      setProfile(data);
      // Kullanıcı bilgisini güncelle
      const userInfo = getUser();
      if (userInfo) {
        userInfo.display_name = data.display_name;
        saveUser(userInfo, isRemembered());
      }
      showFeedback("success", "Profil güncellendi");
    } catch {
      showFeedback("error", "Profil güncellenemedi");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPassword) {
      showFeedback("error", "Tüm alanları doldurun");
      return;
    }
    if (newPassword.length < 6) {
      showFeedback("error", "Yeni şifre en az 6 karakter olmalı");
      return;
    }
    if (newPassword !== confirmPassword) {
      showFeedback("error", "Yeni şifreler eşleşmiyor");
      return;
    }

    setPasswordSaving(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      showFeedback("success", "Şifre başarıyla değiştirildi");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail;
      showFeedback("error", detail || "Şifre değiştirilemedi");
    } finally {
      setPasswordSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <TopBar title="Hesap Ayarları" connected={connected} />

      {/* Feedback */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border mb-6 ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          {feedback.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profil Bilgileri */}
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-neon-cyan/10 border border-neon-cyan/20 flex items-center justify-center">
                <User size={20} className="text-neon-cyan" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Profil Bilgileri
                </h3>
                <p className="text-xs text-gray-500">
                  Kullanıcı adı ve görünen ad
                </p>
              </div>
            </div>

            {/* Kullanıcı adi (salt okunur) */}
            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1.5">
                Kullanıcı Adi
              </label>
              <input
                type="text"
                value={profile?.username || ""}
                disabled
                className="w-full px-4 py-2.5 bg-surface-800/50 border border-glass-border rounded-xl text-sm text-gray-400 cursor-not-allowed"
              />
              <p className="text-[10px] text-gray-600 mt-1">
                Kullanıcı adı değiştirilemez
              </p>
            </div>

            {/* Görünen Ad */}
            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1.5">
                Görünen Ad
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Adinizi girin..."
                className="w-full px-4 py-2.5 bg-surface-800 border border-glass-border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
              />
            </div>

            {/* Rol */}
            <div className="mb-6">
              <label className="block text-xs text-gray-400 mb-1.5">Rol</label>
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-neon-amber" />
                <span className="text-sm text-neon-amber">
                  {profile?.is_admin ? "Yönetici" : "Kullanıcı"}
                </span>
              </div>
            </div>

            {/* Kaydet */}
            <button
              onClick={handleProfileSave}
              disabled={profileSaving || !displayName.trim()}
              className="flex items-center gap-2 px-5 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 transition-all disabled:opacity-50"
            >
              <Save size={14} />
              {profileSaving ? "Kaydediliyor..." : "Profili Kaydet"}
            </button>
          </div>
        </GlassCard>

        {/* Şifre Değiştirme */}
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-neon-amber/10 border border-neon-amber/20 flex items-center justify-center">
                <KeyRound size={20} className="text-neon-amber" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Şifre Değiştir
                </h3>
                <p className="text-xs text-gray-500">
                  Uzaktan erişim için güvenli şifre belirleyin
                </p>
              </div>
            </div>

            {/* Mevcut Şifre */}
            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1.5">
                Mevcut Şifre
              </label>
              <div className="relative">
                <input
                  type={showCurrentPw ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Mevcut şifrenizi girin"
                  className="w-full px-4 py-2.5 pr-10 bg-surface-800 border border-glass-border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-amber/50"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPw(!showCurrentPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  {showCurrentPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Yeni Şifre */}
            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1.5">
                Yeni Şifre
              </label>
              <div className="relative">
                <input
                  type={showNewPw ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="En az 6 karakter"
                  className="w-full px-4 py-2.5 pr-10 bg-surface-800 border border-glass-border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-amber/50"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPw(!showNewPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  {showNewPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {newPassword && newPassword.length < 6 && (
                <p className="text-[10px] text-neon-red mt-1">
                  Şifre en az 6 karakter olmalı
                </p>
              )}
            </div>

            {/* Şifre Tekrar */}
            <div className="mb-6">
              <label className="block text-xs text-gray-400 mb-1.5">
                Yeni Şifre (Tekrar)
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Yeni şifrenizi tekrar girin"
                className="w-full px-4 py-2.5 bg-surface-800 border border-glass-border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-amber/50"
              />
              {confirmPassword && newPassword !== confirmPassword && (
                <p className="text-[10px] text-neon-red mt-1">
                  Şifreler eşleşmiyor
                </p>
              )}
            </div>

            {/* Şifre Guvenligi Bilgisi */}
            <div className="mb-4 p-3 rounded-lg bg-surface-800/50 border border-glass-border">
              <p className="text-[10px] text-gray-500">
                Şifreler veritabanında SHA-256 ile hashlenerek saklanır.
                Duz metin olarak kaydedilmez.
              </p>
            </div>

            {/* Şifre Değiştir */}
            <button
              onClick={handlePasswordChange}
              disabled={
                passwordSaving ||
                !currentPassword ||
                !newPassword ||
                newPassword.length < 6 ||
                newPassword !== confirmPassword
              }
              className="flex items-center gap-2 px-5 py-2.5 bg-neon-amber/10 text-neon-amber border border-neon-amber/30 rounded-xl text-sm font-medium hover:bg-neon-amber/20 transition-all disabled:opacity-50"
            >
              <KeyRound size={14} />
              {passwordSaving ? "Değiştiriliyor..." : "Şifreyi Değiştir"}
            </button>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
