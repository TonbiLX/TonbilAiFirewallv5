// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dış VPN İstemci API çağrıları ve tip tanimlari

import api from './api';

// --- Tipler ---

export interface VpnClientServer {
  id: number;
  name: string;
  country: string;
  country_code: string;
  endpoint: string;
  public_key: string;
  interface_address: string;
  allowed_ips: string;
  dns_servers: string;
  mtu: number;
  persistent_keepalive: number;
  is_active: boolean;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface VpnClientStats {
  total_servers: number;
  active_server: string | null;
  active_country: string | null;
  client_connected: boolean;
}

export interface VpnClientServerCreate {
  name: string;
  country: string;
  country_code: string;
  endpoint: string;
  public_key: string;
  private_key?: string;
  preshared_key?: string;
  interface_address?: string;
  allowed_ips?: string;
  dns_servers?: string;
  mtu?: number;
  persistent_keepalive?: number;
}

export interface VpnClientServerUpdate {
  name?: string;
  country?: string;
  country_code?: string;
  endpoint?: string;
  public_key?: string;
  private_key?: string;
  preshared_key?: string;
  interface_address?: string;
  allowed_ips?: string;
  dns_servers?: string;
  mtu?: number;
  persistent_keepalive?: number;
}

export interface VpnClientImportPayload {
  name: string;
  country?: string;
  country_code?: string;
  config_text: string;
}

export interface VpnClientStatus {
  connected: boolean;
  active_server: string | null;
  active_endpoint: string | null;
  active_country: string | null;
  active_country_code: string | null;
  transfer_rx: number;
  transfer_tx: number;
  session_total_rx: number;
  session_total_tx: number;
  speed_rx_bps: number;
  speed_tx_bps: number;
  last_handshake: string | null;
  uptime_seconds: number;
}

// --- API Fonksiyonlari ---

export async function fetchVpnClientServers(): Promise<VpnClientServer[]> {
  const { data } = await api.get('/vpn-client/servers');
  return data;
}

export async function createVpnClientServer(payload: VpnClientServerCreate): Promise<VpnClientServer> {
  const { data } = await api.post('/vpn-client/servers', payload);
  return data;
}

export async function importVpnClientConfig(payload: VpnClientImportPayload): Promise<VpnClientServer> {
  const { data } = await api.post('/vpn-client/servers/import', payload);
  return data;
}

export async function updateVpnClientServer(id: number, payload: VpnClientServerUpdate): Promise<VpnClientServer> {
  const { data } = await api.patch(`/vpn-client/servers/${id}`, payload);
  return data;
}

export async function deleteVpnClientServer(id: number): Promise<void> {
  await api.delete(`/vpn-client/servers/${id}`);
}

export async function activateVpnClientServer(id: number): Promise<any> {
  const { data } = await api.post(`/vpn-client/servers/${id}/activate`);
  return data;
}

export async function deactivateVpnClientServer(id: number): Promise<any> {
  const { data } = await api.post(`/vpn-client/servers/${id}/deactivate`);
  return data;
}

export async function fetchVpnClientStats(): Promise<VpnClientStats> {
  const { data } = await api.get('/vpn-client/stats');
  return data;
}

export async function fetchVpnClientStatus(): Promise<VpnClientStatus> {
  const { data } = await api.get('/vpn-client/status');
  return data;
}

export async function clearMockServers(): Promise<any> {
  const { data } = await api.post('/vpn-client/servers/clear-mock');
  return data;
}
