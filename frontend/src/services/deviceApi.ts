// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz API çağrıları + sıralama/filtre + bağlantı gecmisi

import api from './api';

export interface DeviceListParams {
  sort_by?: string;
  sort_order?: string;
  status?: string;
}

export const fetchDevices = (params?: DeviceListParams) =>
  api.get('/devices/', { params });
export const fetchLiveDevices = () => api.get('/devices/live');
export const fetchDevice = (id: number) => api.get(`/devices/${id}`);
export const createDevice = (data: any) => api.post('/devices/', data);
export const updateDevice = (id: number, data: any) => api.patch(`/devices/${id}`, data);
export const blockDevice = (id: number) => api.post(`/devices/${id}/block`);
export const unblockDevice = (id: number) => api.post(`/devices/${id}/unblock`);
export const fetchDeviceConnectionHistory = (id: number, limit = 20) =>
  api.get(`/devices/${id}/connection-history`, { params: { limit } });
export const setDeviceBandwidthLimit = (id: number, limit_mbps: number | null) =>
  api.patch(`/devices/${id}/bandwidth`, { limit_mbps });
export const scanDevices = () => api.post('/devices/scan');
