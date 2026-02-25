// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Widget kayıt defteri: tüm dashboard widget tanımları (react-grid-layout v2)

import {
  Wifi, Activity, Search, ShieldBan, Shield, Globe, Ban, Users,
  Upload, BarChart3,
} from "lucide-react";
import type { ResponsiveLayouts } from "react-grid-layout";
import type { WidgetDefinition } from "../types/dashboard-grid";

export const WIDGET_REGISTRY: WidgetDefinition[] = [
  {
    id: "connection-status",
    title: "Bağlantı Durumu",
    icon: <Wifi size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 0, w: 12, h: 1, minW: 4, minH: 1 },
      md: { x: 0, y: 0, w: 12, h: 1, minW: 4, minH: 1 },
      sm: { x: 0, y: 0, w: 6, h: 1, minW: 4, minH: 1 },
      xs: { x: 0, y: 0, w: 4, h: 1, minW: 4, minH: 1 },
    },
  },
  {
    id: "stat-cards",
    title: "İstatistik Kartları",
    icon: <BarChart3 size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 1, w: 12, h: 2, minW: 4, minH: 2 },
      md: { x: 0, y: 1, w: 12, h: 2, minW: 4, minH: 2 },
      sm: { x: 0, y: 1, w: 6, h: 3, minW: 4, minH: 2 },
      xs: { x: 0, y: 1, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
  {
    id: "bandwidth-chart",
    title: "Bandwidth Grafiği",
    icon: <Activity size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 0, y: 3, w: 12, h: 4, minW: 4, minH: 3 },
      md: { x: 0, y: 3, w: 12, h: 4, minW: 4, minH: 3 },
      sm: { x: 0, y: 4, w: 6, h: 4, minW: 4, minH: 3 },
      xs: { x: 0, y: 6, w: 4, h: 4, minW: 4, minH: 3 },
    },
  },
  {
    id: "device-traffic",
    title: "Cihaz Trafiği",
    icon: <Activity size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 0, y: 7, w: 8, h: 6, minW: 4, minH: 4 },
      md: { x: 0, y: 7, w: 8, h: 6, minW: 4, minH: 4 },
      sm: { x: 0, y: 8, w: 6, h: 5, minW: 4, minH: 4 },
      xs: { x: 0, y: 10, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "dns-summary",
    title: "DNS Özet",
    icon: <Search size={14} />,
    defaultVisible: true,
    neonColor: "green",
    defaultLayout: {
      lg: { x: 8, y: 7, w: 4, h: 2, minW: 2, minH: 2 },
      md: { x: 8, y: 7, w: 4, h: 2, minW: 2, minH: 2 },
      sm: { x: 0, y: 13, w: 3, h: 3, minW: 2, minH: 2 },
      xs: { x: 0, y: 15, w: 4, h: 3, minW: 4, minH: 2 },
    },
  },
  {
    id: "device-status",
    title: "Cihaz Durumu",
    icon: <Wifi size={14} />,
    defaultVisible: true,
    neonColor: "amber",
    defaultLayout: {
      lg: { x: 8, y: 9, w: 4, h: 2, minW: 2, minH: 2 },
      md: { x: 8, y: 9, w: 4, h: 2, minW: 2, minH: 2 },
      sm: { x: 3, y: 13, w: 3, h: 3, minW: 2, minH: 2 },
      xs: { x: 0, y: 18, w: 4, h: 3, minW: 4, minH: 2 },
    },
  },
  {
    id: "vpn-status",
    title: "VPN Durumu",
    icon: <Shield size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 8, y: 11, w: 4, h: 2, minW: 2, minH: 2 },
      md: { x: 8, y: 11, w: 4, h: 2, minW: 2, minH: 2 },
      sm: { x: 0, y: 16, w: 6, h: 2, minW: 2, minH: 2 },
      xs: { x: 0, y: 21, w: 4, h: 3, minW: 4, minH: 2 },
    },
  },
  {
    id: "top-domains",
    title: "En Çok Sorgulanan",
    icon: <Globe size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      md: { x: 0, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      sm: { x: 0, y: 18, w: 3, h: 5, minW: 3, minH: 3 },
      xs: { x: 0, y: 24, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
  {
    id: "top-blocked",
    title: "En Çok Engellenen",
    icon: <Ban size={14} />,
    defaultVisible: true,
    neonColor: "magenta",
    defaultLayout: {
      lg: { x: 4, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      md: { x: 4, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      sm: { x: 3, y: 18, w: 3, h: 5, minW: 3, minH: 3 },
      xs: { x: 0, y: 29, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
  {
    id: "connected-devices",
    title: "Bağlı Cihazlar",
    icon: <Users size={14} />,
    defaultVisible: true,
    neonColor: "green",
    defaultLayout: {
      lg: { x: 8, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      md: { x: 8, y: 13, w: 4, h: 5, minW: 3, minH: 3 },
      sm: { x: 0, y: 23, w: 6, h: 5, minW: 3, minH: 3 },
      xs: { x: 0, y: 34, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
  {
    id: "top-clients",
    title: "En Aktif İstemciler",
    icon: <Upload size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 18, w: 12, h: 3, minW: 4, minH: 2 },
      md: { x: 0, y: 18, w: 12, h: 3, minW: 4, minH: 2 },
      sm: { x: 0, y: 28, w: 6, h: 3, minW: 4, minH: 2 },
      xs: { x: 0, y: 39, w: 4, h: 4, minW: 4, minH: 2 },
    },
  },
];

// Varsayılan layout'ları widget registry'den hesapla
export function buildDefaultLayouts(): ResponsiveLayouts {
  const layouts: Record<string, Array<{ i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number }>> = {
    lg: [], md: [], sm: [], xs: [],
  };
  const breakpoints = ["lg", "md", "sm", "xs"] as const;

  for (const bp of breakpoints) {
    layouts[bp] = WIDGET_REGISTRY.map((w) => ({
      i: w.id,
      ...w.defaultLayout[bp],
    }));
  }

  return layouts as ResponsiveLayouts;
}

export const DEFAULT_LAYOUTS = buildDefaultLayouts();
