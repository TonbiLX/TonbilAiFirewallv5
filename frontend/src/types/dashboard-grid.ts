// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard grid layout tip tanımları (react-grid-layout v2 API)

import { ReactNode } from "react";
import type { LayoutItem, ResponsiveLayouts } from "react-grid-layout";

export type { LayoutItem, ResponsiveLayouts };

export interface WidgetDefinition {
  id: string;
  title: string;
  icon: ReactNode;
  defaultVisible: boolean;
  neonColor?: "cyan" | "magenta" | "green" | "amber" | "red";
  defaultLayout: {
    lg: WidgetLayout;
    md: WidgetLayout;
    sm: WidgetLayout;
    xs: WidgetLayout;
  };
}

export interface WidgetLayout {
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

export interface DashboardPreferences {
  layouts: ResponsiveLayouts;
  visibleWidgets: string[];
  version: number;
}

export const GRID_CONFIG = {
  breakpoints: { lg: 1200, md: 996, sm: 768, xs: 0 },
  cols: { lg: 12, md: 12, sm: 6, xs: 4 },
  rowHeight: 40,
  margin: [12, 12] as [number, number],
  containerPadding: [0, 0] as [number, number],
};
