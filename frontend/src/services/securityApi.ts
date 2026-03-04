// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Guvenlik Ayarlari API cagrilari

import api from './api';

export const fetchSecurityConfig = () => api.get('/security/config');
export const updateSecurityConfig = (data: Record<string, unknown>) => api.put('/security/config', data);
export const reloadSecurityConfig = () => api.post('/security/reload');
export const resetSecurityConfig = () => api.post('/security/reset');
export const fetchSecurityDefaults = () => api.get('/security/defaults');
export const fetchSecurityStats = () => api.get('/security/stats');
