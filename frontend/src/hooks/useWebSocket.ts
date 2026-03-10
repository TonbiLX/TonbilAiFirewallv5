// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// WebSocket hook: otomatik yeniden bağlantı, exponential backoff, debounced disconnect göstergesi

import { useEffect, useRef, useState, useCallback } from "react";
import type { RealtimeUpdate } from "../types/websocket";

// Sayfa URL'inden WS adresi turet (reverse proxy uyumlu)
const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_BASE = `${wsProtocol}//${window.location.host}/api/v1/ws`;

// Exponential backoff sabitleri
const RECONNECT_BASE_MS = 2000;   // İlk yeniden bağlanma bekleme süresi
const RECONNECT_MAX_MS = 30000;   // Maksimum bekleme süresi (30 saniye)
const RECONNECT_JITTER_MS = 1000; // Rastgele jitter (thundering herd önlemek için)

// Bağlantı kopması göstergesini geciktirme süresi
// Bu süre içinde yeniden bağlanırsa kullanıcı "koptu" görmez
const DISCONNECT_DEBOUNCE_MS = 5000; // 5 saniye

export function useWebSocket() {
  const [data, setData] = useState<RealtimeUpdate | null>(null);
  // connected: gerçek WS durumu, displayConnected: kullanıcıya gösterilen (debounced)
  const [connected, setConnected] = useState(false);
  const [displayConnected, setDisplayConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  const disconnectDebounceRef = useRef<number>();
  const reconnectAttemptsRef = useRef<number>(0);
  const isUnmountedRef = useRef<boolean>(false);

  const scheduleReconnect = useCallback(() => {
    if (isUnmountedRef.current) return;

    const attempt = reconnectAttemptsRef.current;
    // Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
    const backoff = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, attempt),
      RECONNECT_MAX_MS
    );
    const jitter = Math.random() * RECONNECT_JITTER_MS;
    const delay = Math.round(backoff + jitter);

    reconnectAttemptsRef.current = attempt + 1;
    reconnectTimeoutRef.current = window.setTimeout(() => {
      if (!isUnmountedRef.current) {
        connect();
      }
    }, delay);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;

    // Önceki bağlantıyı temizle
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      if (
        wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }

    const ws = new WebSocket(WS_BASE);
    wsRef.current = ws;

    ws.onopen = () => {
      if (isUnmountedRef.current) return;
      // Bağlantı kuruldu: debounce timer'ı iptal et, hemen "bağlı" göster
      window.clearTimeout(disconnectDebounceRef.current);
      reconnectAttemptsRef.current = 0; // Başarılı bağlantıda sayacı sıfırla
      setConnected(true);
      setDisplayConnected(true);
    };

    ws.onclose = () => {
      if (isUnmountedRef.current) return;
      setConnected(false);

      // Debounce: 5 saniye içinde yeniden bağlanırsa kullanıcı fark etmez
      window.clearTimeout(disconnectDebounceRef.current);
      disconnectDebounceRef.current = window.setTimeout(() => {
        if (!isUnmountedRef.current) {
          setDisplayConnected(false);
        }
      }, DISCONNECT_DEBOUNCE_MS);

      scheduleReconnect();
    };

    ws.onmessage = (event) => {
      if (isUnmountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data);
        // Sadece realtime_update mesajlarini dashboard verisine yaz
        // ping ve security_event mesajlari data state'ini ezmesin
        if (parsed.type === "realtime_update") {
          setData(parsed);
        }
      } catch (e) {
        console.error("WebSocket parse hatasi:", e);
      }
    };

    ws.onerror = () => {
      // onerror her zaman onclose ile devam eder, yeniden bağlanma onclose'da
      ws.close();
    };
  }, [scheduleReconnect]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      window.clearTimeout(reconnectTimeoutRef.current);
      window.clearTimeout(disconnectDebounceRef.current);
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  // displayConnected: debounced bağlantı durumu (titreşimi önler)
  // connected: anlık gerçek WS durumu (gerektiğinde kullanılabilir)
  return { data, connected: displayConnected, rawConnected: connected };
}
