// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DNS Engelleme API çağrıları
// Yeni: Blocklist refresh (tekli ve toplu) endpoint'leri

import api from "./api";
import type {
  Blocklist,
  DnsRule,
  DnsQueryLog,
  DnsStats,
  DomainLookup,
  BlocklistRefreshResult,
  BulkRefreshResult,
} from "../types";

export async function fetchBlocklists(): Promise<Blocklist[]> {
  const { data } = await api.get("/dns/blocklists");
  return data;
}

export async function createBlocklist(payload: Partial<Blocklist>): Promise<Blocklist> {
  const { data } = await api.post("/dns/blocklists", payload);
  return data;
}

export async function updateBlocklist(id: number, payload: Partial<Blocklist>): Promise<Blocklist> {
  const { data } = await api.patch(`/dns/blocklists/${id}`, payload);
  return data;
}

export async function deleteBlocklist(id: number): Promise<void> {
  await api.delete(`/dns/blocklists/${id}`);
}

export async function toggleBlocklist(id: number) {
  const { data } = await api.post(`/dns/blocklists/${id}/toggle`);
  return data;
}

export async function refreshBlocklist(id: number): Promise<BlocklistRefreshResult> {
  const { data } = await api.post(`/dns/blocklists/${id}/refresh`);
  return data;
}

export async function refreshAllBlocklists(): Promise<BulkRefreshResult> {
  const { data } = await api.post("/dns/blocklists/refresh-all");
  return data;
}

export async function fetchDnsRules(params?: { rule_type?: string; profile_id?: number }): Promise<DnsRule[]> {
  const { data } = await api.get("/dns/rules", { params });
  return data;
}

export async function createDnsRule(payload: { domain: string; rule_type: string; reason?: string; profile_id?: number }): Promise<DnsRule> {
  const { data } = await api.post("/dns/rules", payload);
  return data;
}

export async function deleteDnsRule(id: number): Promise<void> {
  await api.delete(`/dns/rules/${id}`);
}

export async function fetchDnsQueries(params?: {
  limit?: number;
  blocked_only?: boolean;
  domain_search?: string;
  device_id?: number;
}): Promise<DnsQueryLog[]> {
  const { data } = await api.get("/dns/queries", { params });
  return data;
}

export async function fetchDnsStats(): Promise<DnsStats> {
  const { data } = await api.get("/dns/stats");
  return data;
}

export async function lookupDomain(domain: string): Promise<DomainLookup> {
  const { data } = await api.get(`/dns/lookup/${domain}`);
  return data;
}
