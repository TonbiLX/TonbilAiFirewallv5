// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Tekil cihaz karti: glassmorphic gorunum

import { Monitor, Wifi, WifiOff, Ban } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { Device } from "../../types";

interface DeviceCardProps {
  device: Device;
  onBlock?: (id: number) => void;
  onUnblock?: (id: number) => void;
}

export function DeviceCard({ device, onBlock, onUnblock }: DeviceCardProps) {
  return (
    <GlassCard hoverable className="flex items-center gap-4">
      <div className="flex-shrink-0">
        <Monitor
          size={32}
          className={device.is_online ? "text-neon-green" : "text-gray-600"}
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold truncate">
          {device.hostname || "Bilinmeyen Cihaz"}
        </p>
        <p className="text-xs text-gray-400">
          {device.ip_address} | {device.mac_address}
        </p>
        <p className="text-xs text-gray-500">{device.manufacturer}</p>
      </div>
      <div className="flex items-center gap-2">
        {device.is_online ? (
          <NeonBadge label="Çevrimiçi" variant="green" />
        ) : (
          <NeonBadge label="Çevrimdışı" variant="red" />
        )}
        {device.is_blocked ? (
          <button
            onClick={() => onUnblock?.(device.id)}
            className="p-2 rounded-lg bg-neon-red/10 text-neon-red hover:bg-neon-red/20 transition-colors"
            title="Engeli kaldir"
          >
            <Ban size={16} />
          </button>
        ) : (
          <button
            onClick={() => onBlock?.(device.id)}
            className="p-2 rounded-lg bg-glass-light text-gray-400 hover:text-neon-red hover:bg-neon-red/10 transition-colors"
            title="Engelle"
          >
            <Ban size={16} />
          </button>
        )}
      </div>
    </GlassCard>
  );
}
