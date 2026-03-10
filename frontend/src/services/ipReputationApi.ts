import api from './api';

export const fetchReputationConfig = () => api.get('/ip-reputation/config');
export const updateReputationConfig = (data: any) => api.put('/ip-reputation/config', data);
export const fetchReputationSummary = () => api.get('/ip-reputation/summary');
export const fetchReputationIps = (minScore?: number) =>
  api.get('/ip-reputation/ips', { params: minScore ? { min_score: minScore } : {} });
export const clearReputationCache = () => api.delete('/ip-reputation/cache');
export const testAbuseipdbKey = () => api.post('/ip-reputation/test');
export const checkApiUsage = () => api.get('/ip-reputation/api-usage');

// AbuseIPDB Blacklist
export const checkBlacklistApiUsage = () => api.get('/ip-reputation/blacklist/api-usage');
export const fetchBlacklist = () => api.get('/ip-reputation/blacklist');
export const triggerBlacklistFetch = () => api.post('/ip-reputation/blacklist/fetch');
export const fetchBlacklistConfig = () => api.get('/ip-reputation/blacklist/config');
export const updateBlacklistConfig = (data: { auto_block?: boolean; min_score?: number; limit?: number }) =>
  api.put('/ip-reputation/blacklist/config', data);
