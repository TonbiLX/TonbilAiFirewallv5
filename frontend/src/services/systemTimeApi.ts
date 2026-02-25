// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Saat & Tarih API çağrıları

import api from './api';

export async function fetchTimeStatus() {
  const { data } = await api.get('/system-time/status');
  return data;
}

export async function fetchTimezones() {
  const { data } = await api.get('/system-time/timezones');
  return data.timezones as Record<string, string[]>;
}

export async function fetchNtpServers() {
  const { data } = await api.get('/system-time/ntp-servers');
  return data.servers as Array<{ id: string; name: string; address: string }>;
}

export async function setTimezone(timezone: string) {
  const { data } = await api.post('/system-time/set-timezone', { timezone });
  return data;
}

export async function setNtpServer(ntp_server: string) {
  const { data } = await api.post('/system-time/set-ntp-server', { ntp_server });
  return data;
}

export async function syncNow() {
  const { data } = await api.post('/system-time/sync-now');
  return data;
}
