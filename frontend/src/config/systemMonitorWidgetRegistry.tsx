// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Sistem Monitörü widget kayıt defteri: 10 widget tanımı + varsayılan layout

import {
  Server, Clock, Cpu, Thermometer, HardDrive, MemoryStick,
  Fan, Network, Activity, BarChart3,
} from "lucide-react";
import type { ResponsiveLayouts } from "react-grid-layout";
import type { WidgetDefinition } from "../types/dashboard-grid";

export const SYSMON_WIDGET_REGISTRY: WidgetDefinition[] = [
  {
    id: "hw-info",
    title: "Donanım Bilgileri",
    icon: <Server size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 0, y: 0, w: 8, h: 4, minW: 4, minH: 3 },
      md: { x: 0, y: 0, w: 8, h: 4, minW: 4, minH: 3 },
      sm: { x: 0, y: 0, w: 6, h: 4, minW: 4, minH: 3 },
      xs: { x: 0, y: 0, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
  {
    id: "uptime",
    title: "Sistem Süresi",
    icon: <Clock size={14} />,
    defaultVisible: true,
    neonColor: "green",
    defaultLayout: {
      lg: { x: 8, y: 0, w: 4, h: 4, minW: 3, minH: 3 },
      md: { x: 8, y: 0, w: 4, h: 4, minW: 3, minH: 3 },
      sm: { x: 0, y: 4, w: 6, h: 4, minW: 3, minH: 3 },
      xs: { x: 0, y: 5, w: 4, h: 4, minW: 4, minH: 3 },
    },
  },
  {
    id: "stat-cards",
    title: "İstatistik Kartları",
    icon: <BarChart3 size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 4, w: 12, h: 3, minW: 6, minH: 2 },
      md: { x: 0, y: 4, w: 12, h: 3, minW: 6, minH: 2 },
      sm: { x: 0, y: 8, w: 6, h: 5, minW: 4, minH: 3 },
      xs: { x: 0, y: 9, w: 4, h: 8, minW: 4, minH: 4 },
    },
  },
  {
    id: "cpu-chart",
    title: "CPU Kullanım Grafiği",
    icon: <Activity size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 0, y: 7, w: 12, h: 5, minW: 4, minH: 4 },
      md: { x: 0, y: 7, w: 12, h: 5, minW: 4, minH: 4 },
      sm: { x: 0, y: 13, w: 6, h: 5, minW: 4, minH: 4 },
      xs: { x: 0, y: 17, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "temp-chart",
    title: "Sıcaklık Grafiği",
    icon: <Thermometer size={14} />,
    defaultVisible: true,
    neonColor: "amber",
    defaultLayout: {
      lg: { x: 0, y: 12, w: 6, h: 5, minW: 4, minH: 4 },
      md: { x: 0, y: 12, w: 6, h: 5, minW: 4, minH: 4 },
      sm: { x: 0, y: 18, w: 6, h: 5, minW: 4, minH: 4 },
      xs: { x: 0, y: 22, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "net-chart",
    title: "Ağ Veri Akışı",
    icon: <Network size={14} />,
    defaultVisible: true,
    neonColor: "cyan",
    defaultLayout: {
      lg: { x: 6, y: 12, w: 6, h: 5, minW: 4, minH: 4 },
      md: { x: 6, y: 12, w: 6, h: 5, minW: 4, minH: 4 },
      sm: { x: 0, y: 23, w: 6, h: 5, minW: 4, minH: 4 },
      xs: { x: 0, y: 27, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "memory-detail",
    title: "Bellek Detay",
    icon: <MemoryStick size={14} />,
    defaultVisible: true,
    neonColor: "magenta",
    defaultLayout: {
      lg: { x: 0, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      md: { x: 0, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      sm: { x: 0, y: 28, w: 3, h: 5, minW: 3, minH: 4 },
      xs: { x: 0, y: 32, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "disk-detail",
    title: "Disk Detay",
    icon: <HardDrive size={14} />,
    defaultVisible: true,
    neonColor: "amber",
    defaultLayout: {
      lg: { x: 4, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      md: { x: 4, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      sm: { x: 3, y: 28, w: 3, h: 5, minW: 3, minH: 4 },
      xs: { x: 0, y: 37, w: 4, h: 5, minW: 4, minH: 4 },
    },
  },
  {
    id: "fan-control",
    title: "Fan Kontrolü",
    icon: <Fan size={14} />,
    defaultVisible: true,
    neonColor: "green",
    defaultLayout: {
      lg: { x: 8, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      md: { x: 8, y: 17, w: 4, h: 5, minW: 3, minH: 4 },
      sm: { x: 0, y: 33, w: 6, h: 5, minW: 3, minH: 4 },
      xs: { x: 0, y: 42, w: 4, h: 6, minW: 4, minH: 4 },
    },
  },
  {
    id: "net-interfaces",
    title: "Ağ Arayüzleri",
    icon: <Network size={14} />,
    defaultVisible: true,
    defaultLayout: {
      lg: { x: 0, y: 22, w: 12, h: 4, minW: 4, minH: 3 },
      md: { x: 0, y: 22, w: 12, h: 4, minW: 4, minH: 3 },
      sm: { x: 0, y: 38, w: 6, h: 4, minW: 4, minH: 3 },
      xs: { x: 0, y: 48, w: 4, h: 5, minW: 4, minH: 3 },
    },
  },
];

export function buildSysmonDefaultLayouts(): ResponsiveLayouts {
  const layouts: Record<string, Array<{ i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number }>> = {
    lg: [], md: [], sm: [], xs: [],
  };
  const breakpoints = ["lg", "md", "sm", "xs"] as const;

  for (const bp of breakpoints) {
    layouts[bp] = SYSMON_WIDGET_REGISTRY.map((w) => ({
      i: w.id,
      ...w.defaultLayout[bp],
    }));
  }

  return layouts as ResponsiveLayouts;
}

export const SYSMON_DEFAULT_LAYOUTS = buildSysmonDefaultLayouts();
