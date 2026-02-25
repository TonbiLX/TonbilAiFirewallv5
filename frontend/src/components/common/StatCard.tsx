// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Dashboard metrik karti: ikon, deger ve trend göstergesi

import { ReactNode } from "react";
import { GlassCard } from "./GlassCard";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: { value: number; positive: boolean };
  neonColor?: "cyan" | "magenta" | "green" | "amber" | "red";
}

export function StatCard({
  title,
  value,
  icon,
  trend,
  neonColor = "cyan",
}: StatCardProps) {
  return (
    <GlassCard hoverable neonColor={neonColor}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400 uppercase tracking-wider">
            {title}
          </p>
          <p className="text-3xl font-bold mt-1 neon-text">{value}</p>
          {trend && (
            <p
              className={`text-xs mt-1 ${
                trend.positive ? "text-neon-green" : "text-neon-red"
              }`}
            >
              {trend.positive ? "+" : ""}
              {trend.value}%
            </p>
          )}
        </div>
        <div className="text-neon-cyan opacity-70">{icon}</div>
      </div>
    </GlassCard>
  );
}
