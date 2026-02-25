// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Bant genişliği göstergesi: dairesel gauge stili

import { GlassCard } from "../common/GlassCard";

interface BandwidthGaugeProps {
  label: string;
  value: number;
  max: number;
  color: string;
}

export function BandwidthGauge({
  label,
  value,
  max,
  color,
}: BandwidthGaugeProps) {
  const percentage = Math.min((value / max) * 100, 100);
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <GlassCard className="flex flex-col items-center">
      <svg width="100" height="100" className="transform -rotate-90">
        <circle
          cx="50"
          cy="50"
          r="40"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="8"
          fill="none"
        />
        <circle
          cx="50"
          cy="50"
          r="40"
          stroke={color}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{
            transition: "stroke-dashoffset 0.5s ease",
            filter: `drop-shadow(0 0 6px ${color})`,
          }}
        />
      </svg>
      <p className="text-2xl font-bold mt-2" style={{ color }}>
        {value.toFixed(1)}
      </p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </GlassCard>
  );
}
