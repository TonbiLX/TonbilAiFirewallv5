// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DPI kategori pasta grafiği: trafik dagilimi

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { GlassCard } from "../common/GlassCard";

interface CategoryData {
  category: string;
  count: number;
}

interface CategoryPieProps {
  data: CategoryData[];
}

const NEON_COLORS = [
  "#00F0FF", "#FF00E5", "#39FF14", "#FFB800",
  "#FF003C", "#7B68EE", "#00CED1", "#FF6347",
];

export function CategoryPie({ data }: CategoryPieProps) {
  return (
    <GlassCard className="h-72">
      <h3 className="text-lg font-semibold mb-4 neon-text">
        Trafik Kategorileri
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="category"
            cx="50%"
            cy="50%"
            outerRadius={70}
            strokeWidth={2}
            stroke="rgba(10, 10, 15, 0.8)"
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={NEON_COLORS[index % NEON_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(18, 18, 26, 0.95)",
              border: "1px solid rgba(0, 240, 255, 0.3)",
              borderRadius: "12px",
              color: "#fff",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "12px", color: "#999" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
