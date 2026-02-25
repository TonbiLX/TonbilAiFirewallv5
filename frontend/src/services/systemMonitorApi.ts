// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Sistem Monitörü API çağrıları

import api from './api';
import type {
  SystemHardwareInfo,
  SystemMetricsResponse,
  FanConfig,
  FanConfigUpdate,
} from '../types';

export async function fetchHardwareInfo(): Promise<SystemHardwareInfo> {
  const { data } = await api.get('/system-monitor/info');
  return data;
}

export async function fetchMetrics(): Promise<SystemMetricsResponse> {
  const { data } = await api.get('/system-monitor/metrics');
  return data;
}

export async function fetchFanConfig(): Promise<FanConfig> {
  const { data } = await api.get('/system-monitor/fan');
  return data;
}

export async function updateFanConfig(config: FanConfigUpdate): Promise<FanConfig> {
  const { data } = await api.put('/system-monitor/fan', config);
  return data;
}
