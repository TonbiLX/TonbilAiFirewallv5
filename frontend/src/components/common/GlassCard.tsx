// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Tekrar kullanilabilir glassmorphism kart bileseni

import { ReactNode } from "react";
import clsx from "clsx";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hoverable?: boolean;
  neonColor?: "cyan" | "magenta" | "green" | "amber" | "red";
}

export function GlassCard({
  children,
  className,
  hoverable = false,
  neonColor,
}: GlassCardProps) {
  return (
    <div
      className={clsx(
        hoverable ? "glass-card-hover" : "glass-card",
        neonColor === "cyan" && "border-neon-cyan/30 shadow-neon",
        neonColor === "magenta" && "border-neon-magenta/30 shadow-neon-magenta",
        neonColor === "green" && "border-neon-green/30 shadow-neon-green",
        neonColor === "amber" && "border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.15)]",
        neonColor === "red" && "border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.15)]",
        "p-6",
        className
      )}
    >
      {children}
    </div>
  );
}
