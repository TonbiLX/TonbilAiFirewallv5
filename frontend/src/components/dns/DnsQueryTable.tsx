// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// DNS sorgu log tablosu: engellenen/izin verilen gösterge ile
// Hizli aksiyon butonlari: domain engelle/izin ver, istemci engelle

import { useState } from "react";
import { Ban, CheckCircle, ShieldBan } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { DnsQueryLog } from "../../types";

interface DnsQueryTableProps {
  queries: DnsQueryLog[];
  onBlockDomain?: (domain: string) => Promise<void>;
  onAllowDomain?: (domain: string) => Promise<void>;
  onBlockClient?: (clientIp: string) => Promise<void>;
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
              <th className="pb-3 pr-4">İstemci IP</th>
              <th className="pb-3 pr-4">Domain</th>
              <th className="pb-3 pr-4">Tip</th>
              <th className="pb-3 pr-4">Durum</th>
              <th className="pb-3 pr-4">Yanit</th>
              <th className="pb-3 text-right">Aksiyonlar</th>
            </tr>
          </thead>
          <tbody>
            {queries.map((q) => {
              const domainKey = `domain-${q.id}`;
              const clientKey = `client-${q.id}`;

              return (
                <tr
                  key={q.id}
                  className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                >
                  <td className="py-2.5 pr-4 text-gray-400 text-xs font-mono">
                    {q.timestamp
                      ? new Date(q.timestamp).toLocaleTimeString("tr-TR")
                      : "--"}
                  </td>
                  <td className="py-2.5 pr-4 text-xs font-mono">
                    {q.client_ip || "--"}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs max-w-[200px] truncate">
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
                  <td className="py-2.5 pr-4 text-xs text-gray-400 font-mono">
                    {q.answer_ip || "--"}
                    {q.upstream_response_ms != null && (
                      <span className="ml-2 text-gray-600">
                        {q.upstream_response_ms}ms
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* Domain Engelle / İzin Ver */}
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

                      {/* İstemci Engelle */}
                      {onBlockClient && q.client_ip && (
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
