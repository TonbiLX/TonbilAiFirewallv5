// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Trafik ve bandwidth API çağrıları

import api from './api';

// Per-device trafik özeti
export const fetchPerDeviceTraffic = (period?: string) =>
  api.get('/traffic/per-device', { params: { period: period || '24h' } });

// Tek cihaz saatlik bandwidth gecmisi
export const fetchDeviceTrafficHistory = (deviceId: number, hours?: number) =>
  api.get(`/traffic/per-device/${deviceId}/history`, { params: { hours: hours || 24 } });

// Tek cihaz aktif bağlantılari
export const fetchDeviceActiveConnections = (deviceId: number) =>
  api.get(`/traffic/per-device/${deviceId}/connections`);

// Tek cihaz en cok eristigi hedefler
export const fetchDeviceTopDestinations = (deviceId: number, hours?: number) =>
  api.get(`/traffic/per-device/${deviceId}/top-destinations`, { params: { hours: hours || 24 } });

// Tek cihaz DNS sorgu gecmisi
export const fetchDeviceDnsQueries = (deviceId: number, limit?: number, blockedOnly?: boolean) =>
  api.get(`/traffic/per-device/${deviceId}/dns-queries`, {
    params: { limit: limit || 50, blocked_only: blockedOnly || false }
  });

// Anlik toplam bandwidth
export const fetchRealtimeBandwidth = () =>
  api.get('/traffic/realtime');

// Toplam trafik istatistikleri
export const fetchTotalTrafficStats = (period?: string) =>
  api.get('/traffic/total', { params: { period: period || '24h' } });

// Firewall aktif bağlantılari
export const fetchActiveConnections = (params?: { limit?: number; src_ip?: string; protocol?: string }) =>
  api.get('/firewall/connections', { params });

// Firewall bağlantı sayısı
export const fetchConnectionCount = () =>
  api.get('/firewall/connections/count');

// --- Connection Flow API ---

// Canli aktif flow'lar (Redis)
export const fetchLiveFlows = (params?: {
  device_id?: number;
  protocol?: string;
  dst_port?: number;
  dst_domain?: string;
  min_bytes?: number;
  sort?: string;
}) => api.get('/traffic/flows/live', { params });

// Buyuk transferler >1MB (Redis ZSET)
export const fetchLargeTransfers = () =>
  api.get('/traffic/flows/large-transfers');

// Gecmis flow kayitlari (MariaDB, pagination)
export const fetchFlowHistory = (params?: {
  device_id?: number;
  protocol?: string;
  dst_domain?: string;
  hours?: number;
  limit?: number;
  offset?: number;
}) => api.get('/traffic/flows/history', { params });

// Genel flow istatistikleri (Redis)
export const fetchFlowStats = () =>
  api.get('/traffic/flows/stats');

// Cihaz bazli flow ozeti (MariaDB)
export const fetchDeviceFlowSummary = (deviceId: number, hours?: number) =>
  api.get(`/traffic/flows/device/${deviceId}/summary`, { params: { hours } });
