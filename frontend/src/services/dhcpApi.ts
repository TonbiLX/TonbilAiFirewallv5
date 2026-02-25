// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP Sunucu API çağrıları

import api from "./api";
import type { DhcpPool, DhcpLease, DhcpStats } from "../types";

export async function fetchPools(): Promise<DhcpPool[]> {
  const { data } = await api.get("/dhcp/pools");
  return data;
}

export async function createPool(payload: Partial<DhcpPool>): Promise<DhcpPool> {
  const { data } = await api.post("/dhcp/pools", payload);
  return data;
}

export async function updatePool(id: number, payload: Partial<DhcpPool>): Promise<DhcpPool> {
  const { data } = await api.patch(`/dhcp/pools/${id}`, payload);
  return data;
}

export async function deletePool(id: number): Promise<void> {
  await api.delete(`/dhcp/pools/${id}`);
}

export async function togglePool(id: number) {
  const { data } = await api.post(`/dhcp/pools/${id}/toggle`);
  return data;
}

export async function fetchLeases(params?: { static_only?: boolean }): Promise<DhcpLease[]> {
  const { data } = await api.get("/dhcp/leases", { params });
  return data;
}

export async function createStaticLease(payload: { mac_address: string; ip_address: string; hostname?: string }): Promise<DhcpLease> {
  const { data } = await api.post("/dhcp/leases/static", payload);
  return data;
}

export async function deleteStaticLease(mac: string): Promise<void> {
  await api.delete(`/dhcp/leases/static/${mac}`);
}

export async function deleteLease(mac: string): Promise<void> {
  await api.delete(`/dhcp/leases/${mac}`);
}

export async function fetchDhcpStats(): Promise<DhcpStats> {
  const { data } = await api.get("/dhcp/stats");
  return data;
}
