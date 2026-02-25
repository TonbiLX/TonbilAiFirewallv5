// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz listesi bileseni

import { DeviceCard } from "./DeviceCard";
import { LoadingSpinner } from "../common/LoadingSpinner";
import type { Device } from "../../types";

interface DeviceListProps {
  devices: Device[];
  loading: boolean;
  onBlock?: (id: number) => void;
  onUnblock?: (id: number) => void;
}

export function DeviceList({
  devices,
  loading,
  onBlock,
  onUnblock,
}: DeviceListProps) {
  if (loading) return <LoadingSpinner />;

  if (devices.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        Kayıtlı cihaz bulunamadı.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {devices.map((device) => (
        <DeviceCard
          key={device.id}
          device={device}
          onBlock={onBlock}
          onUnblock={onUnblock}
        />
      ))}
    </div>
  );
}
