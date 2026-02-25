// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Gercek zamanli trafik çizgi grafiği: Netdata akan grafiklerinden ilham

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { GlassCard } from "../common/GlassCard";

interface TrafficDataPoint {
  time: string;
  download: number;
  upload: number;
}

interface TrafficChartProps {
  data: TrafficDataPoint[];
}

export function TrafficChart({ data }: TrafficChartProps) {
  return (
    <GlassCard className="h-80">
      <h3 className="text-lg font-semibold mb-4 neon-text">
        Canlı Trafik Akışı
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
          />
          <XAxis dataKey="time" stroke="#666" fontSize={12} />
          <YAxis stroke="#666" fontSize={12} unit=" Mbps" />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(18, 18, 26, 0.95)",
              border: "1px solid rgba(0, 240, 255, 0.3)",
              borderRadius: "12px",
              backdropFilter: "blur(16px)",
              color: "#fff",
            }}
          />
          <Line
            type="monotone"
            dataKey="download"
            stroke="#00F0FF"
            strokeWidth={2}
            dot={false}
            name="Indirme"
          />
          <Line
            type="monotone"
            dataKey="upload"
            stroke="#FF00E5"
            strokeWidth={2}
            dot={false}
            name="Yukleme"
          />
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
