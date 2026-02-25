// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard grid container: react-grid-layout ile sürükle-bırak + boyutlandırma

import { Responsive, WidthProvider } from "react-grid-layout/legacy";
import type { LayoutItem, ResponsiveLayouts } from "react-grid-layout";
import { ReactNode, useMemo } from "react";
import { WIDGET_REGISTRY } from "../../config/widgetRegistry";
import { GRID_CONFIG } from "../../types/dashboard-grid";
import type { WidgetDefinition } from "../../types/dashboard-grid";

const ResponsiveGridLayout = WidthProvider(Responsive);

interface DashboardGridProps {
  layouts: ResponsiveLayouts;
  visibleWidgets: string[];
  onLayoutChange: (current: LayoutItem[], all: ResponsiveLayouts) => void;
  onBreakpointChange: (bp: string) => void;
  widgetRenderers: Record<string, ReactNode>;
  widgetRegistry?: WidgetDefinition[];
}

export function DashboardGrid({
  layouts,
  visibleWidgets,
  onLayoutChange,
  onBreakpointChange,
  widgetRenderers,
  widgetRegistry,
}: DashboardGridProps) {
  const registry = widgetRegistry ?? WIDGET_REGISTRY;

  // Sadece visible widget'ların layout'larını filtrele (stabil referans)
  const filteredLayouts = useMemo(() => {
    const result: Record<string, LayoutItem[]> = {};
    for (const bp of Object.keys(layouts)) {
      result[bp] = (layouts[bp] || []).filter((item: LayoutItem) => visibleWidgets.includes(item.i));
    }
    return result as ResponsiveLayouts;
  }, [layouts, visibleWidgets]);

  return (
    <ResponsiveGridLayout
      className="dashboard-grid"
      layouts={filteredLayouts}
      breakpoints={GRID_CONFIG.breakpoints}
      cols={GRID_CONFIG.cols}
      rowHeight={GRID_CONFIG.rowHeight}
      margin={GRID_CONFIG.margin}
      containerPadding={GRID_CONFIG.containerPadding}
      onLayoutChange={onLayoutChange}
      onBreakpointChange={onBreakpointChange}
      isDraggable={true}
      isResizable={true}
      draggableHandle=".drag-handle"
      autoSize={true}
    >
      {registry.filter((w) => visibleWidgets.includes(w.id)).map((widget) => (
        <div key={widget.id}>{widgetRenderers[widget.id]}</div>
      ))}
    </ResponsiveGridLayout>
  );
}
