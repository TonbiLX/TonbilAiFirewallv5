// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DNS istatistik grafikleri: PieChart (engel vs izin) + BarChart (top engelli domainler)

import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { GlassCard } from "../common/GlassCard";
import type { DnsStats } from "../../types";

interface DnsStatsChartProps {
  stats: DnsStats;
}

const PIE_COLORS = ["#FF003C", "#39FF14"];

export function DnsStatsChart({ stats }: DnsStatsChartProps) {
  const pieData = [
    { name: "Engellenen", value: stats.blocked_queries_24h },
    { name: "İzin Verilen", value: stats.total_queries_24h - stats.blocked_queries_24h },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Engel/Izin Pie */}
      <GlassCard>
        <h4 className="text-sm font-semibold text-gray-300 mb-3">
          Sorgu Dagilimi (24s)
        </h4>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {pieData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={PIE_COLORS[index]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "#1a1a2e",
                border: "1px solid rgba(0, 240, 255, 0.2)",
                borderRadius: "8px",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-neon-red" />
            Engellenen ({stats.blocked_queries_24h})
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-neon-green" />
            Izin ({stats.total_queries_24h - stats.blocked_queries_24h})
          </span>
        </div>
      </GlassCard>

      {/* Top Engellenen Domainler Bar */}
      <GlassCard>
        <h4 className="text-sm font-semibold text-gray-300 mb-3">
          En Çok Engellenen Domainler
        </h4>
        {stats.top_blocked_domains.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={stats.top_blocked_domains.slice(0, 7)}
              layout="vertical"
              margin={{ left: 10, right: 10 }}
            >
              <XAxis type="number" stroke="#666" fontSize={10} />
              <YAxis
                type="category"
                dataKey="domain"
                stroke="#666"
                fontSize={10}
                width={140}
                tick={{ fill: "#9ca3af" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid rgba(255, 0, 60, 0.2)",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="count" fill="#FF003C" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 text-sm text-center py-8">
            Henüz engellenen sorgu yok
          </p>
        )}
      </GlassCard>
    </div>
  );
}
