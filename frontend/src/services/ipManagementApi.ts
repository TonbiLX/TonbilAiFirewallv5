// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// IP Yönetimi API çağrıları

import api from './api';

// İstatistikler
export const fetchIpManagementStats = () => api.get('/ip-management/stats');

// Güvenilir IP
export const fetchTrustedIps = () => api.get('/ip-management/trusted');
export const addTrustedIp = (data: { ip_address: string; description?: string }) =>
  api.post('/ip-management/trusted', data);
export const deleteTrustedIp = (id: number) => api.delete(`/ip-management/trusted/${id}`);

// Engellenen IP
export const fetchBlockedIps = () => api.get('/ip-management/blocked');
export const addBlockedIp = (data: { ip_address: string; reason?: string; duration_minutes?: number | null }) =>
  api.post('/ip-management/blocked', data);
export const unblockIp = (ip_address: string) =>
  api.post('/ip-management/unblock', { ip_address });
export const updateBlockedIpDuration = (data: { ip_address: string; duration_minutes: number | null }) =>
  api.put('/ip-management/blocked/duration', data);
