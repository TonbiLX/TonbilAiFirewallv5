// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz özel DNS kurallari API istemcisi

import api from "./api";
import type { DeviceCustomRule } from "../types";

export async function fetchDeviceCustomRules(
  deviceId?: number
): Promise<DeviceCustomRule[]> {
  const params = deviceId ? { device_id: deviceId } : {};
  const { data } = await api.get("/device-rules/", { params });
  return data;
}

export async function createDeviceCustomRule(
  deviceId: number,
  payload: { domain: string; rule_type: string; reason?: string }
): Promise<DeviceCustomRule> {
  const { data } = await api.post(`/device-rules/devices/${deviceId}`, payload);
  return data;
}

export async function updateDeviceCustomRule(
  ruleId: number,
  payload: { domain?: string; rule_type?: string; reason?: string }
): Promise<DeviceCustomRule> {
  const { data } = await api.put(`/device-rules/${ruleId}`, payload);
  return data;
}

export async function deleteDeviceCustomRule(ruleId: number): Promise<void> {
  await api.delete(`/device-rules/${ruleId}`);
}
