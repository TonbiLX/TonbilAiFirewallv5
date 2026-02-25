// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard veri getirme hook'u

import { useEffect, useState } from "react";
import { fetchDashboardSummary } from "../services/dashboardApi";
import type { DashboardSummary } from "../types";

export function useDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchDashboardSummary();
        setSummary(data);
      } catch (err) {
        console.error("Dashboard verisi alinamadi:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 10000); // Her 10 saniyede yenile
    return () => clearInterval(interval);
  }, []);

  return { summary, loading };
}
