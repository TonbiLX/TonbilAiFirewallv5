// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// TLS Şifreleme API çağrıları ve tip tanimlari
// Sertifika yapıştırma, yükleme, doğrulama, Let's Encrypt

import api from './api';

// --- Tipler ---

export interface TlsConfig {
  id: number;
  domain: string;
  cert_path: string | null;
  key_path: string | null;
  certificate_chain: string | null;
  private_key: string | null;
  cert_subject: string | null;
  cert_issuer: string | null;
  cert_not_before: string | null;
  cert_not_after: string | null;
  cert_valid: boolean;
  lets_encrypt_enabled: boolean;
  lets_encrypt_email: string | null;
  doh_enabled: boolean;
  dot_enabled: boolean;
  https_enabled: boolean;
  https_port: number;
  dot_port: number;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TlsConfigUpdate {
  domain?: string;
  certificate_chain?: string;
  private_key?: string;
  lets_encrypt_enabled?: boolean;
  lets_encrypt_email?: string;
  doh_enabled?: boolean;
  dot_enabled?: boolean;
  https_enabled?: boolean;
  https_port?: number;
  dot_port?: number;
  enabled?: boolean;
}

export interface TlsValidateRequest {
  certificate_chain: string;
  private_key: string;
  domain?: string;
}

export interface TlsValidateResponse {
  valid: boolean;
  subject: string | null;
  issuer: string | null;
  not_before: string | null;
  not_after: string | null;
  domain_match: boolean | null;
  error: string | null;
}

export interface LetsEncryptResponse {
  status: string;
  domain?: string;
  message: string;
}

export interface TlsToggleResponse {
  enabled: boolean;
  dot_enabled: boolean;
  message: string;
}

// --- API Fonksiyonlari ---

export async function fetchTlsConfig(): Promise<TlsConfig> {
  const { data } = await api.get('/tls/config');
  return data;
}

export async function updateTlsConfig(payload: TlsConfigUpdate): Promise<TlsConfig> {
  const { data } = await api.patch('/tls/config', payload);
  return data;
}

export async function validateCertificate(payload: TlsValidateRequest): Promise<TlsValidateResponse> {
  const { data } = await api.post('/tls/validate', payload);
  return data;
}

export async function uploadCertificateFiles(certFile: File, keyFile: File): Promise<unknown> {
  const formData = new FormData();
  formData.append('cert_file', certFile);
  formData.append('key_file', keyFile);
  const { data } = await api.post('/tls/upload-cert', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function requestLetsEncrypt(): Promise<LetsEncryptResponse> {
  const { data } = await api.post('/tls/letsencrypt');
  return data;
}

export async function toggleTlsEncryption(): Promise<TlsToggleResponse> {
  const { data } = await api.post('/tls/toggle');
  return data;
}
