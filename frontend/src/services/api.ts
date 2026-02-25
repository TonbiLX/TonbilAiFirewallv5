// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Axios temel istemci yapılandirmasi + JWT token interceptor
// Token yönetimi tokenStore üzerinden yapilir (localStorage/sessionStorage desteği)

import axios from "axios";
import { getToken, clearAuth } from "./tokenStore";

// Tarayıcıda calistiginda:
// - Dogrudan erişim (192.168.1.9:93): Vite proxy /api/* -> backend:8000
// - Reverse proxy (guard.tonbilx.com): ayni sekilde Vite proxy calisiyor
// Bu yuzden relative path kullaniyoruz, Vite proxy hallediyor.
const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,  // httpOnly cookie'lerin otomatik gönderilmesi için
});

// JWT token interceptor - her istege Authorization header ekle
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 yanit interceptor - oturumu sonlandir ve login sayfasına yonlendir
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuth();
      // Zaten login sayfasındaysak tekrar yonlendirme yapma
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
