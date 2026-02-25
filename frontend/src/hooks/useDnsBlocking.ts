// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DNS Engelleme birlesik veri hook'u

import { useEffect, useState, useCallback } from "react";
import { fetchDnsStats, fetchBlocklists, fetchDnsRules, fetchDnsQueries } from "../services/dnsApi";
import type { DnsStats, Blocklist, DnsRule, DnsQueryLog } from "../types";

export function useDnsBlocking() {
  const [stats, setStats] = useState<DnsStats | null>(null);
  const [blocklists, setBlocklists] = useState<Blocklist[]>([]);
  const [rules, setRules] = useState<DnsRule[]>([]);
  const [recentQueries, setRecentQueries] = useState<DnsQueryLog[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [s, bl, r, q] = await Promise.all([
        fetchDnsStats(),
        fetchBlocklists(),
        fetchDnsRules(),
        fetchDnsQueries({ limit: 50 }),
      ]);
      setStats(s);
      setBlocklists(bl);
      setRules(r);
      setRecentQueries(q);
    } catch (err) {
      console.error("DNS veri alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { stats, blocklists, rules, recentQueries, loading, refresh };
}
