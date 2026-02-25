// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// WebSocket hook: otomatik yeniden bağlantı ile canlı veri akışı

import { useEffect, useRef, useState, useCallback } from "react";
import type { RealtimeUpdate } from "../types/websocket";
import { getToken } from "../services/tokenStore";

// Sayfa URL'inden WS adresi turet (reverse proxy uyumlu)
const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_BASE = `${wsProtocol}//${window.location.host}/api/v1/ws`;

export function useWebSocket() {
  const [data, setData] = useState<RealtimeUpdate | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();

  const connect = useCallback(() => {
    // WebSocket auth: Cookie tabanli (httpOnly cookie otomatik gönderilir)
    // Token URL'de gönderilmez (log/referer sızması riski)
    const ws = new WebSocket(WS_BASE);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      // 3 saniye sonra otomatik yeniden baglan
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch (e) {
        console.error("WebSocket parse hatasi:", e);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, connected };
}
