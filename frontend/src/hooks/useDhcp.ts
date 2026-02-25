// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP birlesik veri hook'u

import { useEffect, useState, useCallback } from "react";
import { fetchPools, fetchLeases, fetchDhcpStats } from "../services/dhcpApi";
import type { DhcpPool, DhcpLease, DhcpStats } from "../types";

export function useDhcp() {
  const [pools, setPools] = useState<DhcpPool[]>([]);
  const [leases, setLeases] = useState<DhcpLease[]>([]);
  const [stats, setStats] = useState<DhcpStats | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [p, l, s] = await Promise.all([
        fetchPools(),
        fetchLeases(),
        fetchDhcpStats(),
      ]);
      setPools(p);
      setLeases(l);
      setStats(s);
    } catch (err) {
      console.error("DHCP veri alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { pools, leases, stats, loading, refresh };
}
