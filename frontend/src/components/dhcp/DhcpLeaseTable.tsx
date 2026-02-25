// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP kiralama tablosu: MAC, IP, hostname, kalan sure, statik badge

import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { DhcpLease } from "../../types";

interface DhcpLeaseTableProps {
  leases: DhcpLease[];
}

function formatRemaining(leaseEnd: string | null): string {
  if (!leaseEnd) return "Kalici";
  const remaining = new Date(leaseEnd).getTime() - Date.now();
  if (remaining <= 0) return "Süresi dolmus";
  const hours = Math.floor(remaining / 3600000);
  const mins = Math.floor((remaining % 3600000) / 60000);
  return `${hours}s ${mins}dk`;
}

export function DhcpLeaseTable({ leases }: DhcpLeaseTableProps) {
  return (
    <GlassCard>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-glass-border">
              <th className="pb-3 pr-4">MAC Adres</th>
              <th className="pb-3 pr-4">IP Adres</th>
              <th className="pb-3 pr-4">Hostname</th>
              <th className="pb-3 pr-4">Tip</th>
              <th className="pb-3 pr-4">Başlangic</th>
              <th className="pb-3 text-right">Kalan Sure</th>
            </tr>
          </thead>
          <tbody>
            {leases.map((lease) => (
              <tr
                key={lease.id}
                className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
              >
                <td className="py-2.5 pr-4 font-mono text-xs">
                  {lease.mac_address}
                </td>
                <td className="py-2.5 pr-4 font-mono text-xs text-neon-cyan">
                  {lease.ip_address}
                </td>
                <td className="py-2.5 pr-4">
                  {lease.hostname || "--"}
                </td>
                <td className="py-2.5 pr-4">
                  <NeonBadge
                    label={lease.is_static ? "STATIK" : "DINAMIK"}
                    variant={lease.is_static ? "magenta" : "cyan"}
                  />
                </td>
                <td className="py-2.5 pr-4 text-xs text-gray-400">
                  {lease.lease_start
                    ? new Date(lease.lease_start).toLocaleString("tr-TR")
                    : "--"}
                </td>
                <td className="py-2.5 text-right text-xs text-gray-400">
                  {formatRemaining(lease.lease_end)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}
