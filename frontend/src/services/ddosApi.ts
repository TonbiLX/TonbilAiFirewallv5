// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// DDoS Koruma API çağrıları

import api from './api';
import type { DdosConfig } from '../types';

export const fetchDdosConfig = () => api.get('/ddos/config');
export const updateDdosConfig = (data: Partial<DdosConfig>) => api.put('/ddos/config', data);
export const applyDdosRules = () => api.post('/ddos/apply');
export const toggleDdosProtection = (name: string) => api.post(`/ddos/toggle/${name}`);
export const fetchDdosStatus = () => api.get('/ddos/status');
export const fetchDdosCounters = () => api.get('/ddos/counters');
export const flushDdosAttackers = () => api.post('/ddos/flush-attackers');
export const fetchDdosAttackMap = () => api.get("\/ddos\/attack-map");
