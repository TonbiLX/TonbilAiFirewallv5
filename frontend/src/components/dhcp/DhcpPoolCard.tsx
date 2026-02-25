// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DHCP havuz karti: subnet, aralık, kullanım oranı, lease süresi

import { Network, Trash2 } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { DhcpPool } from "../../types";

interface DhcpPoolCardProps {
  pool: DhcpPool;
  leaseCount: number;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
}

export function DhcpPoolCard({ pool, leaseCount, onToggle, onDelete }: DhcpPoolCardProps) {
  const startLast = parseInt(pool.range_start.split(".").pop() || "0");
  const endLast = parseInt(pool.range_end.split(".").pop() || "0");
  const totalIps = endLast - startLast + 1;
  const usagePercent = Math.min(100, Math.round((leaseCount / Math.max(totalIps, 1)) * 100));

  const leaseHours = Math.round(pool.lease_time_seconds / 3600);

  return (
    <GlassCard hoverable>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Network
            size={20}
            className={pool.enabled ? "text-neon-cyan" : "text-gray-600"}
          />
          <h4 className="text-sm font-semibold">{pool.name}</h4>
          <NeonBadge
            label={pool.enabled ? "AKTIF" : "PASIF"}
            variant={pool.enabled ? "green" : "red"}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggle(pool.id)}
            className={`px-3 py-1 text-xs rounded-lg transition-all ${
              pool.enabled
                ? "bg-neon-green/10 text-neon-green border border-neon-green/20"
                : "bg-gray-800 text-gray-400 border border-glass-border"
            }`}
          >
            {pool.enabled ? "Durdur" : "Başlat"}
          </button>
          <button
            onClick={() => onDelete(pool.id)}
            className="p-1.5 text-gray-500 hover:text-neon-red transition-colors"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="space-y-2 text-xs text-gray-400">
        <div className="flex justify-between">
          <span>Subnet: {pool.subnet}/{pool.netmask}</span>
          <span>Gateway: {pool.gateway}</span>
        </div>
        <div className="flex justify-between">
          <span>Aralık: {pool.range_start} - {pool.range_end}</span>
          <span>Lease: {leaseHours}s</span>
        </div>
      </div>

      {/* Kullanım progress bar */}
      <div className="mt-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">
            {leaseCount}/{totalIps} IP kullanılıyor
          </span>
          <span className={usagePercent > 80 ? "text-neon-red" : "text-neon-green"}>
            %{usagePercent}
          </span>
        </div>
        <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              usagePercent > 80
                ? "bg-neon-red"
                : usagePercent > 50
                ? "bg-neon-amber"
                : "bg-neon-green"
            }`}
            style={{ width: `${usagePercent}%` }}
          />
        </div>
      </div>
    </GlassCard>
  );
}
