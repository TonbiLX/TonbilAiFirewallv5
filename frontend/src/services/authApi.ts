// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Kimlik doğrulama API servisi: login, setup, auth check, şifre değiştirme

import api from "./api";

export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  display_name: string;
}

export interface SetupRequest {
  username: string;
  password: string;
  display_name?: string;
}

export interface AuthCheck {
  setup_completed: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ProfileUpdateRequest {
  display_name?: string;
}

export interface UserProfile {
  id: number;
  username: string;
  display_name: string | null;
  is_admin: boolean;
}

export const authApi = {
  /** Kullanıcı girişi */
  login: (data: LoginRequest) =>
    api.post<LoginResponse>("/auth/login", data),

  /** Sistem kurulum durumu kontrolü */
  check: () =>
    api.get<AuthCheck>("/auth/check"),

  /** İlk kurulum - yönetici hesabi oluşturma */
  setup: (data: SetupRequest) =>
    api.post<LoginResponse>("/auth/setup", data),

  /** Şifre değiştirme (oturum açık olmali) */
  changePassword: (data: ChangePasswordRequest) =>
    api.post("/auth/change-password", data),

  /** Kullanıcı bilgisi (oturum açık olmali) */
  getProfile: () =>
    api.get<UserProfile>("/auth/me"),

  /** Profil güncelleme (oturum açık olmali) */
  updateProfile: (data: ProfileUpdateRequest) =>
    api.put<UserProfile>("/auth/profile", data),

  /** Oturumu kapat (cookie + token temizle) */
  logout: () =>
    api.post("/auth/logout"),
};
