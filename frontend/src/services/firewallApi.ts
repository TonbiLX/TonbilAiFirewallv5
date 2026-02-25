// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Firewall (Güvenlik Duvarı) API çağrıları

import api from './api';

export const fetchFirewallRules = (params?: any) => api.get('/firewall/rules', { params });
export const createFirewallRule = (data: any) => api.post('/firewall/rules', data);
export const updateFirewallRule = (id: number, data: any) => api.patch(`/firewall/rules/${id}`, data);
export const deleteFirewallRule = (id: number) => api.delete(`/firewall/rules/${id}`);
export const toggleFirewallRule = (id: number) => api.post(`/firewall/rules/${id}/toggle`);
export const scanPorts = (targetIp: string, portRange: string) => api.get('/firewall/scan', { params: { target_ip: targetIp, port_range: portRange } });
export const fetchFirewallStats = () => api.get('/firewall/stats');
export const fetchActiveConnections = (params?: any) => api.get('/firewall/connections', { params });
export const fetchConnectionCount = () => api.get('/firewall/connections/count');
