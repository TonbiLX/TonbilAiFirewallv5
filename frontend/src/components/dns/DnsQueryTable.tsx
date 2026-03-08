// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DNS sorgu log tablosu: engellenen/izin verilen gösterge ile
// Hizli aksiyon butonlari: domain engelle/izin ver, istemci engelle
// Yeni: source_type badge (INTERNAL/EXTERNAL/DOT), block_reason gösterimi

import { useState } from "react";
import { Ban, CheckCircle, ShieldBan, Globe, Wifi, Lock } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { DnsQueryLog } from "../../types";

interface DnsQueryTableProps {
  queries: DnsQueryLog[];
  onBlockDomain?: (domain: string) => Promise<void>;
  onAllowDomain?: (domain: string) => Promise<void>;
  onBlockClient?: (clientIp: string) => Promise<void>;
}

// Block reason Türkçe açıklamaları
const BLOCK_REASON_LABELS: Record<string, string> = {
  blocklist: "Engelleme listesi",
  device_blocked: "Cihaz engelli",
  device_custom_rule: "Özel kural",
  query_type_block: "Sorgu tipi yasak",
  reputation_block: "Düşük itibar",
  external_rejected: "Dış IP reddedildi",
};

function getBlockReasonLabel(reason: string | null): string {
  if (!reason) return "--";
  if (reason.startsWith("service:")) return `Servis: ${reason.slice(8)}`;
  if (reason.startsWith("profile:")) return `Profil filtresi`;
  return BLOCK_REASON_LABELS[reason] || reason;
}

function SourceBadge({ sourceType }: { sourceType: string | null }) {
  if (!sourceType || sourceType === "INTERNAL") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20">
        <Wifi size={10} />
        LAN
      </span>
    );
  }
  if (sourceType === "EXTERNAL") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-neon-red/10 text-neon-red border border-neon-red/20 animate-pulse">
        <Globe size={10} />
        DIŞ
      </span>
    );
  }
  if (sourceType === "DOT") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/20">
        <Lock size={10} />
        DoT
      </span>
    );
  }
  return (
    <span className="text-xs text-gray-500">{sourceType}</span>
  );
}

export function DnsQueryTable({
  queries,
  onBlockDomain,
  onAllowDomain,
  onBlockClient,
}: DnsQueryTableProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleAction = async (
    key: string,
    action: () => Promise<void>
  ) => {
    setActionLoading(key);
    try {
      await action();
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <GlassCard>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-glass-border">
              <th className="pb-3 pr-4">Zaman</th>
              <th className="pb-3 pr-4">Kaynak</th>
              <th className="pb-3 pr-4">İstemci IP</th>
              <th className="pb-3 pr-4">Domain</th>
              <th className="pb-3 pr-4">Tip</th>
              <th className="pb-3 pr-4">Durum</th>
              <th className="pb-3 pr-4">Sebep / Yanıt</th>
              <th className="pb-3 text-right">İşlem</th>
            </tr>
          </thead>
          <tbody>
            {queries.length === 0 && (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-500">
                  Kayıt bulunamadı.
                </td>
              </tr>
            )}
            {queries.map((q) => {
              const domainKey = `domain-${q.id}`;
              const clientKey = `client-${q.id}`;
              const isExternal = q.source_type === "EXTERNAL";

              return (
                <tr
                  key={q.id}
                  className={`border-b border-glass-border/50 hover:bg-glass-light transition-colors ${
                    isExternal ? "bg-neon-red/5" : ""
                  }`}
                >
                  <td className="py-2.5 pr-4 text-gray-400 text-xs font-mono">
                    {q.timestamp
                      ? new Date(q.timestamp).toLocaleTimeString("tr-TR")
                      : "--"}
                  </td>
                  <td className="py-2.5 pr-4">
                    <SourceBadge sourceType={q.source_type} />
                  </td>
                  <td className="py-2.5 pr-4 text-xs font-mono">
                    {q.client_ip || "--"}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs max-w-[180px] truncate">
                    {q.domain}
                  </td>
                  <td className="py-2.5 pr-4 text-gray-400 text-xs">
                    {q.query_type}
                  </td>
                  <td className="py-2.5 pr-4">
                    <NeonBadge
                      label={q.blocked ? "ENGEL" : "IZIN"}
                      variant={q.blocked ? "red" : "green"}
                    />
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-gray-400">
                    {q.blocked ? (
                      <span className="text-neon-amber">
                        {getBlockReasonLabel(q.block_reason)}
                      </span>
                    ) : (
                      <span className="font-mono">
                        {q.answer_ip || "--"}
                        {q.upstream_response_ms != null && (
                          <span className="ml-1 text-gray-600">
                            {q.upstream_response_ms}ms
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* Domain Engelle / İzin Ver — dış kaynaklı sorgularda da göster */}
                      {q.blocked ? (
                        onAllowDomain && (
                          <button
                            onClick={() =>
                              handleAction(domainKey, () =>
                                onAllowDomain(q.domain)
                              )
                            }
                            disabled={actionLoading === domainKey}
                            className="p-1.5 rounded-lg text-gray-500 hover:text-neon-green hover:bg-neon-green/10 transition-all"
                            title={`${q.domain} domainini izin ver`}
                          >
                            <CheckCircle size={14} />
                          </button>
                        )
                      ) : (
                        onBlockDomain && (
                          <button
                            onClick={() =>
                              handleAction(domainKey, () =>
                                onBlockDomain(q.domain)
                              )
                            }
                            disabled={actionLoading === domainKey}
                            className="p-1.5 rounded-lg text-gray-500 hover:text-neon-red hover:bg-neon-red/10 transition-all"
                            title={`${q.domain} domainini engelle`}
                          >
                            <Ban size={14} />
                          </button>
                        )
                      )}

                      {/* İstemci Engelle — sadece yerel istemciler için */}
                      {onBlockClient && q.client_ip && !isExternal && (
                        <button
                          onClick={() =>
                            handleAction(clientKey, () =>
                              onBlockClient(q.client_ip!)
                            )
                          }
                          disabled={actionLoading === clientKey}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-neon-amber hover:bg-neon-amber/10 transition-all"
                          title={`${q.client_ip} istemcisini engelle`}
                        >
                          <ShieldBan size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}
