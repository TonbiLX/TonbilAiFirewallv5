import api from './api';

// ── In-memory cache (TTL bazli) ──────────────────────────────────────────

const _cache = new Map<string, { data: any; ts: number }>();

function getCached<T>(key: string, ttlMs: number): T | null {
  const entry = _cache.get(key);
  if (entry && Date.now() - entry.ts < ttlMs) return entry.data as T;
  return null;
}

function setCache(key: string, data: any) {
  _cache.set(key, { data, ts: Date.now() });
}

/** Tum istemci tarafi cache'i temizle (cache sifirla butonu icin). */
export function invalidateAllCache() {
  _cache.clear();
}

/** Belirli bir cache key'ini temizle. */
export function invalidateCache(key: string) {
  _cache.delete(key);
}

// ── Config (cache'siz — sik degismez, zaten kucuk) ─────────────────────

export const fetchReputationConfig = () => api.get('/ip-reputation/config');
export const updateReputationConfig = (data: any) => api.put('/ip-reputation/config', data);

// ── Summary (60s cache) ─────────────────────────────────────────────────

export const fetchReputationSummary = async () => {
  const cached = getCached('rep-summary', 60_000);
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/summary');
  setCache('rep-summary', resp.data);
  return resp;
};

// ── IP Listesi (30s cache) ──────────────────────────────────────────────

export const fetchReputationIps = async (minScore?: number) => {
  const key = `rep-ips-${minScore ?? 0}`;
  const cached = getCached(key, 30_000);
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/ips', { params: minScore ? { min_score: minScore } : {} });
  setCache(key, resp.data);
  return resp;
};

// ── Cache temizleme (invalidate + API) ──────────────────────────────────

export const clearReputationCache = async () => {
  invalidateAllCache();
  return api.delete('/ip-reputation/cache');
};

// ── Test + API Usage (cache'siz — backend zaten Redis'ten okuyor) ───────

export const testAbuseipdbKey = () => api.post('/ip-reputation/test');
export const checkApiUsage = () => api.get('/ip-reputation/api-usage');

// ── Check-Block (Subnet Analizi) ────────────────────────────────────────

export const checkBlock = (network: string, autoBlock: boolean = true) =>
  api.post('/ip-reputation/check-block', { network, auto_block: autoBlock });
export const fetchCheckBlockResults = () => api.get('/ip-reputation/check-block/results');
export const fetchCheckBlockDetail = (network: string) =>
  api.get(`/ip-reputation/check-block/${encodeURIComponent(network)}`);
export const checkBlockApiUsage = () => api.get('/ip-reputation/check-block/api-usage');
export const clearCheckBlockCache = async () => {
  invalidateCache('rep-checkblock-results');
  return api.delete('/ip-reputation/check-block/cache');
};

// ── Blacklist (60s cache) ───────────────────────────────────────────────

export const checkBlacklistApiUsage = () => api.get('/ip-reputation/blacklist/api-usage');

export const fetchBlacklist = async () => {
  const cached = getCached('rep-blacklist', 60_000);
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/blacklist');
  setCache('rep-blacklist', resp.data);
  return resp;
};

export const triggerBlacklistFetch = async () => {
  invalidateCache('rep-blacklist');
  return api.post('/ip-reputation/blacklist/fetch');
};

export const fetchBlacklistConfig = () => api.get('/ip-reputation/blacklist/config');
export const updateBlacklistConfig = (data: { auto_block?: boolean; min_score?: number; limit?: number }) =>
  api.put('/ip-reputation/blacklist/config', data);
