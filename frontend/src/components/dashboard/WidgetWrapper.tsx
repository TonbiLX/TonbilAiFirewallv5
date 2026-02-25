// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Widget sarmalayıcı: drag handle + GlassCard + overflow yönetimi

import { ReactNode } from "react";
import { GripVertical } from "lucide-react";
import { GlassCard } from "../common/GlassCard";

interface WidgetWrapperProps {
  title: string;
  icon: ReactNode;
  neonColor?: "cyan" | "magenta" | "green" | "amber" | "red";
  children: ReactNode;
  /** Başlık çubuğunu gizle (connection-status gibi minimal widget'lar için) */
  hideHeader?: boolean;
}

export function WidgetWrapper({ title, icon, neonColor, children, hideHeader }: WidgetWrapperProps) {
  if (hideHeader) {
    return (
      <div className="h-full flex flex-col">
        <div className="drag-handle cursor-grab active:cursor-grabbing h-1 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
          <div className="w-8 h-0.5 rounded bg-gray-600" />
        </div>
        <div className="flex-1 min-h-0 overflow-hidden">{children}</div>
      </div>
    );
  }

  return (
    <GlassCard className="h-full !p-3 flex flex-col overflow-hidden" neonColor={neonColor}>
      <div className="drag-handle flex items-center justify-between cursor-grab active:cursor-grabbing mb-2 select-none">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          {icon} {title}
        </h3>
        <GripVertical size={14} className="text-gray-600 flex-shrink-0" />
      </div>
      <div className="flex-1 min-h-0 overflow-auto">{children}</div>
    </GlassCard>
  );
}
