// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Blocklist kaynak kartı: isim, açıklama, domain sayısı, toggle, güncelle, son güncelleme

import { useState } from "react";
import { Shield, Trash2, RotateCw } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { Blocklist, BlocklistRefreshResult } from "../../types";
import { refreshBlocklist } from "../../services/dnsApi";

interface BlocklistCardProps {
  blocklist: Blocklist;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
  onRefreshResult?: (result: BlocklistRefreshResult) => void;
}

export function BlocklistCard({ blocklist, onToggle, onDelete, onRefreshResult }: BlocklistCardProps) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await refreshBlocklist(blocklist.id);
      onRefreshResult?.(result);
    } catch (err) {
      console.error("Blocklist güncellenemedi:", err);
      onRefreshResult?.({
        blocklist_id: blocklist.id,
        name: blocklist.name,
        previous_domain_count: blocklist.domain_count,
        new_domain_count: blocklist.domain_count,
        added_count: 0,
        removed_count: 0,
        status: "error",
        error_message: "Güncelleme sırasında hata oluştu",
      });
    } finally {
      setRefreshing(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    return d.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <GlassCard hoverable>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <Shield
            size={20}
            className={`mt-0.5 flex-shrink-0 ${
              blocklist.enabled ? "text-neon-green" : "text-gray-600"
            }`}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-semibold truncate">{blocklist.name}</h4>
              <NeonBadge
                label={blocklist.enabled ? "AKTIF" : "PASIF"}
                variant={blocklist.enabled ? "green" : "red"}
              />
              <NeonBadge label={blocklist.format} variant="cyan" />
            </div>
            {blocklist.description && (
              <p className="text-xs text-gray-400 mb-2">{blocklist.description}</p>
            )}
            <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
              <span className="font-medium text-gray-300">
                {blocklist.domain_count.toLocaleString("tr-TR")} domain
              </span>
              {blocklist.last_updated && (
                <span>
                  Son güncelleme: {formatDate(blocklist.last_updated)}
                </span>
              )}
              <span>Her {blocklist.update_frequency_hours} saatte güncelle</span>
            </div>
            {blocklist.last_error && (
              <p className="text-xs text-neon-red mt-1">{blocklist.last_error}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 text-gray-400 hover:text-neon-cyan hover:bg-neon-cyan/10 rounded-lg transition-all disabled:opacity-50"
            title="Listeyi güncelle"
          >
            <RotateCw size={16} className={refreshing ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => onToggle(blocklist.id)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
              blocklist.enabled
                ? "bg-neon-green/10 text-neon-green border border-neon-green/20 hover:bg-neon-green/20"
                : "bg-gray-800 text-gray-400 border border-glass-border hover:bg-glass-light"
            }`}
          >
            {blocklist.enabled ? "Devre Dışı Birak" : "Etkinlestir"}
          </button>
          <button
            onClick={() => onDelete(blocklist.id)}
            className="p-1.5 text-gray-500 hover:text-neon-red transition-colors"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </GlassCard>
  );
}
