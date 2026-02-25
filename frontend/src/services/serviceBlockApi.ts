// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Servis engelleme API istemcisi

import api from "./api";
import type {
  BlockedService,
  DeviceBlockedService,
  ServiceGroup,
} from "../types";

export async function fetchServices(
  group?: string
): Promise<BlockedService[]> {
  const params = group ? { group } : {};
  const { data } = await api.get("/services/", { params });
  return data;
}

export async function fetchServiceGroups(): Promise<ServiceGroup[]> {
  const { data } = await api.get("/services/groups");
  return data;
}

export async function fetchDeviceServices(
  deviceId: number
): Promise<DeviceBlockedService[]> {
  const { data } = await api.get(`/services/devices/${deviceId}`);
  return data;
}

export async function toggleDeviceService(
  deviceId: number,
  serviceId: string,
  blocked: boolean
): Promise<void> {
  await api.put(`/services/devices/${deviceId}/toggle`, {
    service_id: serviceId,
    blocked,
  });
}

export async function bulkUpdateDeviceServices(
  deviceId: number,
  blockedServiceIds: string[]
): Promise<void> {
  await api.put(`/services/devices/${deviceId}/bulk`, {
    blocked_service_ids: blockedServiceIds,
  });
}
