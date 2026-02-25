// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Yapay Zeka Ayarları API çağrıları

import api from './api';

export const fetchAiConfig = () => api.get('/ai-settings/config');
export const updateAiConfig = (data: any) => api.put('/ai-settings/config', data);
export const testAiConnection = (prompt?: string) =>
  api.post('/ai-settings/test', prompt ? { prompt } : {});
export const fetchAiProviders = () => api.get('/ai-settings/providers');
export const fetchAiStats = () => api.get('/ai-settings/stats');
export const resetAiCounter = () => api.post('/ai-settings/reset-counter');
