// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Sistem Logları API çağrıları

import api from './api';

export interface SystemLogFilters {
  page?: number;
  per_page?: number;
  date_from?: string;
  date_to?: string;
  source_ip?: string;
  dest_ip?: string;
  domain_search?: string;
  action?: string;
  severity?: string;
  category?: string;
  search?: string;
}

export async function fetchSystemLogs(filters: SystemLogFilters = {}) {
  const { data } = await api.get('/system-logs/', { params: filters });
  return data;
}

export async function fetchSystemLogSummary() {
  const { data } = await api.get('/system-logs/summary');
  return data;
}
