// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Kimlik doğrulama korumasi: Token yoksa veya geçersizse login sayfasına yonlendirir.
// Tum korunmus route'lar bu bilesenle sarilir.

import { useState, useEffect, ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Loader2, ShieldAlert } from "lucide-react";
import { authApi } from "../../services/authApi";
import { getToken, clearAuth } from "../../services/tokenStore";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState<"checking" | "authenticated" | "unauthenticated">("checking");
  const [validated, setValidated] = useState(false);

  // Ilk yüklemede backend'den token dogrula
  useEffect(() => {
    if (!validated) {
      validateWithBackend();
    }
  }, []);

  // Sonraki route değişikliklerinde sadece token varligini kontrol et
  // (401 interceptor süresi dolmus token'lari yakalayacak)
  useEffect(() => {
    if (validated) {
      const token = getToken();
      if (!token) {
        setStatus("unauthenticated");
        navigate("/login", { replace: true });
      }
    }
  }, [location.pathname, validated]);

  async function validateWithBackend() {
    const token = getToken();

    // Token yoksa direkt login'e yonlendir
    if (!token) {
      setStatus("unauthenticated");
      navigate("/login", { replace: true });
      return;
    }

    // Token varsa backend'den dogrula
    try {
      await authApi.getProfile();
      setStatus("authenticated");
    } catch (err: any) {
      // 401 veya herhangi bir auth hatasi -> login'e yonlendir
      if (err.response?.status === 401 || err.response?.status === 403) {
        clearAuth();
        setStatus("unauthenticated");
        navigate("/login", { replace: true });
      } else if (err.code === "ERR_NETWORK") {
        // Network hatasi - token var ama backend'e ulasilamiyor
        // Bu durumda token'a guvenip sayfayi goster (offline/gecici kesinti)
        setStatus("authenticated");
      } else {
        // Beklenmeyen hata - güvenli tarafta kal, login'e yonlendir
        clearAuth();
        setStatus("unauthenticated");
        navigate("/login", { replace: true });
      }
    } finally {
      setValidated(true);
    }
  }

  // Doğrulama yapilirken loading goster
  if (status === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-900">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <ShieldAlert size={48} className="text-neon-cyan/30" />
            <Loader2 size={24} className="text-neon-cyan animate-spin absolute top-3 left-3" />
          </div>
          <p className="text-gray-400 text-sm tracking-wide">Oturum doğrulanıyor...</p>
        </div>
      </div>
    );
  }

  // Kimlik dogrulandi - çocuk bilesenleri render et
  if (status === "authenticated") {
    return <>{children}</>;
  }

  // Dogrulanamadi - bos dondur (navigate zaten calisiyor)
  return null;
}
