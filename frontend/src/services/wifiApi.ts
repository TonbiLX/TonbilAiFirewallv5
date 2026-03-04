// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// WiFi AP API cagrilari — durum, konfigürasyon, kontrol, istemciler

import api from './api';

// --- Okuma ---
export const fetchWifiStatus = () => api.get('/wifi/status');
export const fetchWifiConfig = () => api.get('/wifi/config');
export const fetchWifiClients = () => api.get('/wifi/clients');
export const fetchWifiChannels = () => api.get('/wifi/channels');

// --- Kontrol ---
export const enableWifi = () => api.post('/wifi/enable');
export const disableWifi = () => api.post('/wifi/disable');

// --- Konfigürasyon ---
export const updateWifiConfig = (data: Record<string, unknown>) => api.put('/wifi/config', data);
export const updateGuestConfig = (data: Record<string, unknown>) => api.put('/wifi/guest', data);
export const updateSchedule = (data: Record<string, unknown>) => api.put('/wifi/schedule', data);
export const updateMacFilter = (data: Record<string, unknown>) => api.put('/wifi/mac-filter', data);
