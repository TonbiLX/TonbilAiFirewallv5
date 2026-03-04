// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Giriş sayfası: Cyberpunk glassmorphism temali kimlik doğrulama
// İlk kurulum modu + normal giriş modu + "Beni Hatırla" desteği

import { useState, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { User, Lock, Eye, EyeOff, Loader2, UserPlus, LogIn } from "lucide-react";
import { FirewallLogo } from "../components/ui/FirewallLogo";
import { authApi, LoginResponse, AuthCheck } from "../services/authApi";
import { getToken, saveToken, saveUser, isRemembered } from "../services/tokenStore";

type PageMode = "loading" | "login" | "setup";

export function LoginPage() {
  const navigate = useNavigate();

  // Sayfa modu
  const [mode, setMode] = useState<PageMode>("loading");

  // Form alanlari
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [rememberMe, setRememberMe] = useState(isRemembered());

  // UI durumlari
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Sayfa yüklendiğinde: zaten giriş yapilmis mi? Kurulum gerekli mi?
  useEffect(() => {
    const token = getToken();
    if (token) {
      navigate("/", { replace: true });
      return;
    }
    checkAuthStatus();
  }, []);

  async function checkAuthStatus() {
    try {
      const res = await authApi.check();
      const data: AuthCheck = res.data;
      if (!data.setup_completed) {
        setMode("setup");
      } else {
        setMode("login");
      }
    } catch {
      // API erisilemezse yine de login goster
      setMode("login");
    }
  }

  function handleLoginSuccess(data: LoginResponse) {
    saveToken(data.access_token, rememberMe);
    saveUser(
      { username: data.username, display_name: data.display_name },
      rememberMe
    );
    navigate("/", { replace: true });
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Kullanıcı adi ve şifre gereklidir.");
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.login({
        username: username.trim(),
        password,
        remember_me: rememberMe,
      });
      handleLoginSuccess(res.data);
    } catch (err: any) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        setError("Geçersiz kullanıcı adı veya şifre.");
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.code === "ERR_NETWORK") {
        setError("Sunucuya bağlanılamıyor. Arka ucu kontrol edin.");
      } else {
        setError("Beklenmeyen bir hata oluştu. Tekrar deneyin.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSetup(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Kullanıcı adi ve şifre gereklidir.");
      return;
    }

    if (password.length < 6) {
      setError("Şifre en az 6 karakter olmalıdır.");
      return;
    }

    if (password !== passwordConfirm) {
      setError("Şifreler eşleşmiyor.");
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.setup({
        username: username.trim(),
        password,
        display_name: displayName.trim() || undefined,
      });
      handleLoginSuccess(res.data);
    } catch (err: any) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.code === "ERR_NETWORK") {
        setError("Sunucuya bağlanılamıyor. Arka ucu kontrol edin.");
      } else {
        setError("Kurulum sırasında bir hata oluştu. Tekrar deneyin.");
      }
    } finally {
      setLoading(false);
    }
  }

  // --- Yukleniyor ekrani ---
  if (mode === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={48} className="text-neon-cyan animate-spin" />
          <p className="text-gray-400 text-sm">Sistem kontrol ediliyor...</p>
        </div>
      </div>
    );
  }

  // --- Ana render ---
  return (
    <div className="login-page min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Cyberpunk arka plan */}
      <div className="absolute inset-0 bg-surface-900" />

      {/* Radyal gradyan efektleri */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon-cyan/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-neon-magenta/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-neon-cyan/3 rounded-full blur-3xl" />
      </div>

      {/* Izgara deseni - cyberpunk grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0, 240, 255, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.3) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Ust taraftaki yatay neon çizgi */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />

      {/* Alt taraftaki yatay neon çizgi */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-magenta/50 to-transparent" />

      {/* Giriş karti */}
      <div className="relative z-10 w-full max-w-md mx-4">
        {/* Logo ve baslik */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-glass backdrop-blur-glass border border-neon-cyan/30 mb-6 shadow-neon">
            <FirewallLogo size={64} />
          </div>
          <h1 className="text-3xl font-bold neon-text text-neon-cyan tracking-tight">
            TonbilAi<span className="text-neon-magenta">Firewall</span>
          </h1>
          <p className="text-gray-400 mt-2 text-sm tracking-widest uppercase">
            Yapay Zeka Destekli Güvenlik Duvarı
          </p>
        </div>

        {/* Form karti */}
        <div className="glass-card p-8">
          {/* Mod basligi */}
          {mode === "setup" && (
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-neon-amber/10 border border-neon-amber/30 mb-4">
                <UserPlus size={14} className="text-neon-amber" />
                <span className="text-neon-amber text-xs font-medium tracking-wide">
                  ILK KURULUM
                </span>
              </div>
              <h2 className="text-lg font-semibold text-white">
                Yönetici Hesabı Oluştur
              </h2>
              <p className="text-gray-500 text-sm mt-1">
                Sistemi kullanmak için bir yönetici hesabı oluşturun.
              </p>
            </div>
          )}

          {mode === "login" && (
            <div className="text-center mb-6">
              <h2 className="text-lg font-semibold text-white">
                Sisteme Giriş
              </h2>
              <p className="text-gray-500 text-sm mt-1">
                Devam etmek için kimlik bilgilerinizi girin.
              </p>
            </div>
          )}

          {/* Hata mesaji */}
          {error && (
            <div className="mb-5 px-4 py-3 rounded-xl bg-neon-red/10 border border-neon-red/30 flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-neon-red mt-1.5 flex-shrink-0 animate-pulse-neon" />
              <p className="text-neon-red text-sm">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={mode === "setup" ? handleSetup : handleLogin}>
            <div className="space-y-4">
              {/* Kullanıcı adi */}
              <div>
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-gray-400 mb-1.5"
                >
                  Kullanıcı Adi
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <User size={16} className="text-gray-500" />
                  </div>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    autoComplete="username"
                    autoFocus
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-800 border border-glass-border text-white placeholder-gray-600 text-sm focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/30 transition-colors"
                  />
                </div>
              </div>

              {/* Görünen ad (sadece setup modunda) */}
              {mode === "setup" && (
                <div>
                  <label
                    htmlFor="displayName"
                    className="block text-sm font-medium text-gray-400 mb-1.5"
                  >
                    Görünen Ad
                    <span className="text-gray-600 ml-1">(isteğe bağlı)</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <UserPlus size={16} className="text-gray-500" />
                    </div>
                    <input
                      id="displayName"
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Yönetici"
                      autoComplete="name"
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-800 border border-glass-border text-white placeholder-gray-600 text-sm focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/30 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Şifre */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-400 mb-1.5"
                >
                  Şifre
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Lock size={16} className="text-gray-500" />
                  </div>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={mode === "setup" ? "new-password" : "current-password"}
                    className="w-full pl-10 pr-11 py-2.5 rounded-xl bg-surface-800 border border-glass-border text-white placeholder-gray-600 text-sm focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/30 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-500 hover:text-gray-300 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Şifre tekrar (sadece setup modunda) */}
              {mode === "setup" && (
                <div>
                  <label
                    htmlFor="passwordConfirm"
                    className="block text-sm font-medium text-gray-400 mb-1.5"
                  >
                    Şifre Tekrar
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <Lock size={16} className="text-gray-500" />
                    </div>
                    <input
                      id="passwordConfirm"
                      type={showPasswordConfirm ? "text" : "password"}
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className="w-full pl-10 pr-11 py-2.5 rounded-xl bg-surface-800 border border-glass-border text-white placeholder-gray-600 text-sm focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/30 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-500 hover:text-gray-300 transition-colors"
                      tabIndex={-1}
                    >
                      {showPasswordConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Beni Hatırla checkbox (sadece login modunda) */}
            {mode === "login" && (
              <div className="flex items-center mt-4">
                <label className="relative flex items-center cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-4 h-4 rounded border border-glass-border bg-surface-800 peer-checked:bg-neon-cyan/20 peer-checked:border-neon-cyan/50 transition-all flex items-center justify-center">
                    {rememberMe && (
                      <svg className="w-3 h-3 text-neon-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <span className="ml-2 text-sm text-gray-400 group-hover:text-gray-300 transition-colors select-none">
                    Beni Hatırla
                  </span>
                </label>
              </div>
            )}

            {/* Giriş / Kurulum butonu */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 py-3 rounded-xl font-semibold text-sm tracking-wide transition-all duration-300 flex items-center justify-center gap-2 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/40 hover:bg-neon-cyan/20 hover:shadow-neon active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-neon-cyan/10 disabled:hover:shadow-none"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {mode === "setup" ? "Oluşturuluyor..." : "Giriş Yapılıyor..."}
                </>
              ) : (
                <>
                  {mode === "setup" ? (
                    <>
                      <UserPlus size={18} />
                      Hesap Oluştur ve Başla
                    </>
                  ) : (
                    <>
                      <LogIn size={18} />
                      Giriş Yap
                    </>
                  )}
                </>
              )}
            </button>
          </form>
        </div>

        {/* Alt bilgi */}
        <div className="text-center mt-6">
          <p className="text-gray-600 text-xs">
            TonbilAiFirewall V5.0 &middot; Yapay Zeka Destekli Güvenlik Duvarı
          </p>
        </div>
      </div>
    </div>
  );
}
