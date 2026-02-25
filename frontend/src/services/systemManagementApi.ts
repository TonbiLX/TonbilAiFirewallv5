// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Sistem Yönetimi API çağrıları

import api from './api';

export const fetchSystemOverview = () => api.get('/system-management/overview');
export const fetchServicesStatus = () => api.get('/system-management/services');
export const restartService = (name: string) => api.post(`/system-management/services/${name}/restart`);
export const startService = (name: string) => api.post(`/system-management/services/${name}/start`);
export const stopService = (name: string) => api.post(`/system-management/services/${name}/stop`);
export const rebootSystem = () => api.post('/system-management/reboot');
export const shutdownSystem = () => api.post('/system-management/shutdown');
export const fetchBootInfo = () => api.get('/system-management/boot-info');
export const resetSafeMode = () => api.post('/system-management/reset-safe-mode');
export const fetchJournal = (lines?: number) => api.get('/system-management/journal', { params: { lines } });
