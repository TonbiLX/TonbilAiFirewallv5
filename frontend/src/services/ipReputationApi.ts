import api from './api';

export const fetchReputationConfig = () => api.get('/ip-reputation/config');
export const updateReputationConfig = (data: any) => api.put('/ip-reputation/config', data);
export const fetchReputationSummary = () => api.get('/ip-reputation/summary');
export const fetchReputationIps = (minScore?: number) =>
  api.get('/ip-reputation/ips', { params: minScore ? { min_score: minScore } : {} });
export const clearReputationCache = () => api.delete('/ip-reputation/cache');
export const testAbuseipdbKey = () => api.post('/ip-reputation/test');
