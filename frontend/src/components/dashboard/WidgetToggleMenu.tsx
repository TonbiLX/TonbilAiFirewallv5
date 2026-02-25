// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Widget görünürlük toggle menüsü

import { useState, useRef, useEffect } from "react";
import { LayoutGrid, RotateCcw, ChevronDown } from "lucide-react";
import clsx from "clsx";
import { WIDGET_REGISTRY } from "../../config/widgetRegistry";
import type { WidgetDefinition } from "../../types/dashboard-grid";

interface WidgetToggleMenuProps {
  visibleWidgets: string[];
  onToggle: (widgetId: string) => void;
  onReset: () => void;
  widgetRegistry?: WidgetDefinition[];
}

export function WidgetToggleMenu({ visibleWidgets, onToggle, onReset, widgetRegistry }: WidgetToggleMenuProps) {
  const registry = widgetRegistry ?? WIDGET_REGISTRY;
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl glass-card border border-glass-border hover:border-neon-cyan/30 transition-all duration-200 text-sm text-gray-300"
      >
        <LayoutGrid size={16} className="text-neon-cyan" />
        <span className="hidden sm:inline">Widget</span>
        <ChevronDown
          size={14}
          className={clsx("transition-transform duration-200", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 glass-card border border-glass-border rounded-xl shadow-2xl z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-glass-border flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-300">Widget Görünürlüğü</span>
            <button
              onClick={() => {
                onReset();
                setOpen(false);
              }}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-neon-cyan transition-colors"
              title="Varsayılana Sıfırla"
            >
              <RotateCcw size={12} />
              Sıfırla
            </button>
          </div>
          <div className="p-2 max-h-80 overflow-y-auto scrollbar-thin">
            {registry.map((widget) => (
              <label
                key={widget.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/5 transition-all duration-150"
              >
                <input
                  type="checkbox"
                  checked={visibleWidgets.includes(widget.id)}
                  onChange={() => onToggle(widget.id)}
                  className="rounded border-gray-600 bg-transparent text-neon-cyan focus:ring-neon-cyan/30 focus:ring-offset-0"
                />
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  {widget.icon}
                  <span>{widget.title}</span>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
