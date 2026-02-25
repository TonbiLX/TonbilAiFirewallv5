// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Domain arama bileseni: engel durumu kontrolü

import { useState } from "react";
import { Search, ShieldCheck, ShieldX } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import { lookupDomain } from "../../services/dnsApi";
import type { DomainLookup } from "../../types";

export function DomainSearch() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<DomainLookup | null>(null);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const data = await lookupDomain(query.trim());
      setResult(data);
    } catch {
      setResult(null);
    } finally {
      setSearching(false);
    }
  };

  return (
    <GlassCard>
      <h4 className="text-sm font-semibold text-gray-300 mb-3">
        Domain Kontrol
      </h4>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="domain.com yazin..."
          className="flex-1 bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-lg text-sm hover:bg-neon-cyan/20 transition-colors disabled:opacity-50"
        >
          <Search size={16} />
        </button>
      </div>

      {result && (
        <div className="flex items-center gap-3 p-3 bg-surface-800 rounded-lg">
          {result.is_blocked ? (
            <ShieldX size={24} className="text-neon-red flex-shrink-0" />
          ) : (
            <ShieldCheck size={24} className="text-neon-green flex-shrink-0" />
          )}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono">{result.domain}</span>
              <NeonBadge
                label={result.is_blocked ? "ENGELLI" : "ACIK"}
                variant={result.is_blocked ? "red" : "green"}
              />
            </div>
            {result.custom_rule && (
              <p className="text-xs text-gray-400 mt-1">
                Özel kural: {result.custom_rule.type} - {result.custom_rule.reason}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Son sorgu sayısı: {result.recent_query_count}
            </p>
          </div>
        </div>
      )}
    </GlassCard>
  );
}
