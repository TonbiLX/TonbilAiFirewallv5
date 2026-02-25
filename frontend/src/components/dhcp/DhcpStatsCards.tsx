// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP istatistik kartlari

import { Network, Server, Lock, Globe } from "lucide-react";
import { StatCard } from "../common/StatCard";
import type { DhcpStats } from "../../types";

interface DhcpStatsCardsProps {
  stats: DhcpStats;
}

export function DhcpStatsCards({ stats }: DhcpStatsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Toplam IP"
        value={stats.total_ips}
        icon={<Globe size={32} />}
        neonColor="cyan"
      />
      <StatCard
        title="Dagitilan IP"
        value={stats.assigned_ips}
        icon={<Server size={32} />}
        neonColor="green"
      />
      <StatCard
        title="Bos IP"
        value={stats.available_ips}
        icon={<Network size={32} />}
        neonColor="amber"
      />
      <StatCard
        title="Statik Atama"
        value={stats.static_leases}
        icon={<Lock size={32} />}
        neonColor="magenta"
      />
    </div>
  );
}
