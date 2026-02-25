// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard API çağrıları

import api from "./api";
import type { DashboardSummary } from "../types";

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get("/dashboard/summary");
  return data;
}
