// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard layout state yönetimi + localStorage persistence (react-grid-layout v2)

import { useState, useCallback, useEffect } from "react";
import type { LayoutItem, ResponsiveLayouts } from "react-grid-layout";
import { WIDGET_REGISTRY, DEFAULT_LAYOUTS } from "../config/widgetRegistry";
import type { DashboardPreferences } from "../types/dashboard-grid";

const STORAGE_KEY = "tonbilaios_dashboard_prefs";
const SCHEMA_VERSION = 1;

function loadPreferences(): DashboardPreferences | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DashboardPreferences;
    if (parsed.version !== SCHEMA_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

function savePreferences(prefs: DashboardPreferences): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function useDashboardLayout() {
  const [currentBreakpoint, setCurrentBreakpoint] = useState<string>("lg");

  const [layouts, setLayouts] = useState<ResponsiveLayouts>(() => {
    const saved = loadPreferences();
    return saved?.layouts ?? DEFAULT_LAYOUTS;
  });

  const [visibleWidgets, setVisibleWidgets] = useState<string[]>(() => {
    const saved = loadPreferences();
    return saved?.visibleWidgets ?? WIDGET_REGISTRY.filter((w) => w.defaultVisible).map((w) => w.id);
  });

  // Persist on change
  useEffect(() => {
    savePreferences({ layouts, visibleWidgets, version: SCHEMA_VERSION });
  }, [layouts, visibleWidgets]);

  const onLayoutChange = useCallback((_current: LayoutItem[], allLayouts: ResponsiveLayouts) => {
    setLayouts(allLayouts);
  }, []);

  const onBreakpointChange = useCallback((bp: string) => {
    setCurrentBreakpoint(bp);
  }, []);

  const toggleWidget = useCallback((widgetId: string) => {
    setVisibleWidgets((prev) =>
      prev.includes(widgetId) ? prev.filter((id) => id !== widgetId) : [...prev, widgetId]
    );
  }, []);

  const resetLayout = useCallback(() => {
    setLayouts(DEFAULT_LAYOUTS);
    setVisibleWidgets(WIDGET_REGISTRY.filter((w) => w.defaultVisible).map((w) => w.id));
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    layouts,
    visibleWidgets,
    currentBreakpoint,
    onLayoutChange,
    onBreakpointChange,
    toggleWidget,
    resetLayout,
  };
}
