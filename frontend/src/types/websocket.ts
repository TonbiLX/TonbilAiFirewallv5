// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// WebSocket mesaj tip tanimlari - DNS istatistikleri + Bandwidth

export interface DeviceBandwidthWs {
  upload_bps: number;
  download_bps: number;
  upload_total: number;
  download_total: number;
}

export interface RealtimeUpdate {
  type: "realtime_update";
  device_count: number;
  devices: Array<{
    id: number;
    mac: string;
    ip: string;
    hostname: string;
    manufacturer: string;
    is_online: boolean;
  }>;
  dns: {
    total_queries_24h: number;
    blocked_queries_24h: number;
    block_percentage: number;
    queries_per_min: number;
  };
  bandwidth: {
    total_upload_bps: number;
    total_download_bps: number;
    devices: Record<string, DeviceBandwidthWs>;
  };
  vpn?: {
    enabled: boolean;
    connected_peers: number;
    total_peers: number;
  };
  vpn_client?: {
    connected: boolean;
    transfer_rx: number;
    transfer_tx: number;
  };
}

export type WebSocketMessage = RealtimeUpdate;
