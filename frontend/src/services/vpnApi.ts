// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// VPN (WireGuard) API çağrıları - sunucu yönetimi, peer CRUD, config indirme

import api from './api';

// --- Okuma ---
export const fetchVpnConfig = () => api.get('/vpn/config');
export const fetchVpnPeers = () => api.get('/vpn/peers');
export const fetchPeerConfig = (name: string) => api.get(`/vpn/peers/${name}/config`);
export const fetchVpnStats = () => api.get('/vpn/stats');

// --- Sunucu Kontrol ---
export const startVpnServer = () => api.post('/vpn/start');
export const stopVpnServer = () => api.post('/vpn/stop');

// --- Peer Yönetimi ---
export const addVpnPeer = (name: string) => api.post('/vpn/peers', null, { params: { name } });
export const removeVpnPeer = (name: string) => api.delete(`/vpn/peers/${name}`);

// --- Bakim ---
export const fixVpnSubnet = () => api.post('/vpn/fix-subnet');
