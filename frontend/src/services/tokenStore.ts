// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Merkezi token yönetimi: localStorage (beni hatırla) ve sessionStorage (oturum bazli) desteği.
// Tum token okuma/yazma işlemleri bu modül üzerinden yapilir.

const TOKEN_KEY = "tonbilai_token";
const USER_KEY = "tonbilai_user";
const REMEMBER_KEY = "tonbilai_remember";

/**
 * Token'i sakla. rememberMe true ise localStorage'a, false ise sessionStorage'a yazar.
 */
export function saveToken(token: string, rememberMe: boolean): void {
  if (rememberMe) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REMEMBER_KEY, "1");
    // sessionStorage'daki eski token'i temizle
    sessionStorage.removeItem(TOKEN_KEY);
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
    // localStorage'daki eski token'i temizle
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REMEMBER_KEY);
  }
}

/**
 * Kullanıcı bilgisini sakla (token ile ayni storage'a).
 */
export function saveUser(user: { username: string; display_name: string | null }, rememberMe: boolean): void {
  const userStr = JSON.stringify(user);
  if (rememberMe) {
    localStorage.setItem(USER_KEY, userStr);
    sessionStorage.removeItem(USER_KEY);
  } else {
    sessionStorage.setItem(USER_KEY, userStr);
    localStorage.removeItem(USER_KEY);
  }
}

/**
 * Token'i oku. Öncelik: sessionStorage (aktif oturum) > localStorage (beni hatırla).
 */
export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

/**
 * Kullanıcı bilgisini oku.
 */
export function getUser(): { username: string; display_name: string | null } | null {
  const raw = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * "Beni hatırla" secili miydi?
 */
export function isRemembered(): boolean {
  return localStorage.getItem(REMEMBER_KEY) === "1";
}

/**
 * Tum auth verilerini temizle (logout).
 */
export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(REMEMBER_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}
