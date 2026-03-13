// --- Ajan: INSAATCI (THE CONSTRUCTOR) + MUHAFIZ (THE GUARDIAN) ---
// DNS Engelleme sayfası: Pi-hole tarzi blocklist yönetimi, domain arama, istatistikler
// Yeni: Blocklist ekleme/düzenleme formu, tekli/toplu güncelleme, istatistik geri bildirimi

import { useState, useEffect } from "react";
import {
  ShieldBan,
  List,
  BookOpen,
  Search,
  Ban,
  Plus,
  Pencil,
  Trash2,
  X,
  Link,
  FileText,
  Clock,
  CheckCircle,
  AlertTriangle,
  RotateCw,
  Smartphone,
  Download,
  TrendingUp,
  TrendingDown,
  Globe,
  Filter,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { StatCard } from "../components/common/StatCard";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { BlocklistCard } from "../components/dns/BlocklistCard";
import { DnsQueryTable } from "../components/dns/DnsQueryTable";
import { DnsStatsChart } from "../components/dns/DnsStatsChart";
import { DomainSearch } from "../components/dns/DomainSearch";
import { DeviceCustomRulesTab } from "../components/dns/DeviceCustomRulesTab";
import { useWebSocket } from "../hooks/useWebSocket";
import { useDnsBlocking } from "../hooks/useDnsBlocking";
import {
  toggleBlocklist,
  deleteBlocklist,
  createBlocklist,
  updateBlocklist,
  createDnsRule,
  deleteDnsRule,
  refreshAllBlocklists,
  fetchDnsQueries,
  fetchExternalQueriesSummary,
} from "../services/dnsApi";
import { fetchDevices, blockDevice } from "../services/deviceApi";
import type { Blocklist, BlocklistRefreshResult, BulkRefreshResult } from "../types";

type Tab = "overview" | "blocklists" | "rules" | "device_rules" | "queries";
type QueryFilter = "all" | "blocked" | "allowed" | "external" | "dot" | "doh";

const tabs: { key: Tab; label: string; icon: typeof ShieldBan }[] = [
  { key: "overview", label: "Genel Bakış", icon: ShieldBan },
  { key: "blocklists", label: "Blok Listeleri", icon: List },
  { key: "rules", label: "Kurallar", icon: BookOpen },
  { key: "device_rules", label: "Özel Domain Kuralları", icon: Smartphone },
  { key: "queries", label: "Sorgu Loglari", icon: Search },
];

// --- Blocklist form yapisi ---
interface BlocklistFormData {
  name: string;
  url: string;
  description: string;
  format: "hosts" | "domain_list" | "adblock";
  update_frequency_hours: string;
}

const emptyBlocklistForm: BlocklistFormData = {
  name: "",
  url: "",
  description: "",
  format: "hosts",
  update_frequency_hours: "6",
};

// --- Sayi formatlama yardimcisi ---
function formatNumber(n: number): string {
  return n.toLocaleString("tr-TR");
}

export function DnsBlockingPage() {
  const { connected } = useWebSocket();
  const { stats, blocklists, rules, recentQueries, loading, refresh } =
    useDnsBlocking();
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [newDomain, setNewDomain] = useState("");
  const [newRuleType, setNewRuleType] = useState<"block" | "allow">("block");

  // Blocklist modal durumu
  const [blocklistModalOpen, setBlocklistModalOpen] = useState(false);
  const [editingBlocklist, setEditingBlocklist] = useState<Blocklist | null>(
    null
  );
  const [blocklistForm, setBlocklistForm] =
    useState<BlocklistFormData>(emptyBlocklistForm);
  const [blocklistFormErrors, setBlocklistFormErrors] = useState<
    Record<string, boolean>
  >({});
  const [submitting, setSubmitting] = useState(false);

  // Sorgu log filtresi
  const [queryFilter, setQueryFilter] = useState<QueryFilter>("all");
  const [filteredQueries, setFilteredQueries] = useState<typeof recentQueries>([]);
  const [filterLoading, setFilterLoading] = useState(false);

  // Dış sorgu özeti
  const [externalSummary, setExternalSummary] = useState<{
    total_external_queries: number;
    top_external_ips: Array<{ client_ip: string; count: number }>;
    top_external_domains: Array<{ domain: string; count: number }>;
  } | null>(null);

  // Anlik yenileme durumu
  const [refreshing, setRefreshing] = useState(false);

  // Toplu güncelleme durumu
  const [bulkRefreshing, setBulkRefreshing] = useState(false);

  const handleManualRefresh = async () => {
    setRefreshing(true);
    try {
      await refresh();
      await applyQueryFilter(queryFilter);
    } finally {
      setRefreshing(false);
    }
  };

  // Filtre uygulandığında sorguları yeniden çek
  const applyQueryFilter = async (filter: QueryFilter) => {
    setFilterLoading(true);
    try {
      let params: Parameters<typeof fetchDnsQueries>[0] = { limit: 100 };
      if (filter === "blocked") params = { ...params, blocked_only: true };
      else if (filter === "allowed") params = { ...params };
      else if (filter === "external") params = { ...params, source_type: "EXTERNAL" };
      else if (filter === "dot") params = { ...params, source_type: "DOT" };
      else if (filter === "doh") params = { ...params, source_type: "DOH" };

      const q = await fetchDnsQueries(params);

      // "allowed" filtresi için client tarafında filtrele
      const result = filter === "allowed" ? q.filter((x) => !x.blocked) : q;
      setFilteredQueries(result);
    } catch {
      setFilteredQueries([]);
    } finally {
      setFilterLoading(false);
    }
  };

  // queryFilter değiştiğinde uygula
  const handleFilterChange = async (f: QueryFilter) => {
    setQueryFilter(f);
    await applyQueryFilter(f);
    // Dışarıdan gelen seçilince özet verisini de çek
    if (f === "external" && !externalSummary) {
      try {
        const s = await fetchExternalQueriesSummary(24);
        setExternalSummary(s);
      } catch { /* ignore */ }
    }
  };

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error" | "info";
    message: string;
    details?: string;
  } | null>(null);

  // --- Geri bildirim zamanlayici ---
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 8000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // --- Sorgu logu sekmesine ilk geçişte filtreyi uygula ---
  useEffect(() => {
    if (activeTab === "queries") {
      applyQueryFilter(queryFilter);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  if (loading) return <LoadingSpinner />;

  // --- Mevcut işlemler ---
  const handleToggleBlocklist = async (id: number) => {
    try {
      await toggleBlocklist(id);
      refresh();
    } catch (err) {
      console.error("Blocklist toggle hatasi:", err);
      setFeedback({
        type: "error",
        message: "Blocklist durumu değiştirilemedi.",
      });
    }
  };

  const handleDeleteBlocklist = async (id: number) => {
    try {
      await deleteBlocklist(id);
      setFeedback({ type: "success", message: "Blocklist silindi." });
      refresh();
    } catch (err) {
      console.error("Blocklist silinemedi:", err);
      setFeedback({
        type: "error",
        message: "Blocklist silinirken hata oluştu.",
      });
    }
  };

  const handleAddRule = async () => {
    if (!newDomain.trim()) return;
    const domain = newDomain.trim();
    try {
      await createDnsRule({
        domain,
        rule_type: newRuleType,
      });
      setNewDomain("");
      setFeedback({
        type: "success",
        message: `"${domain}" için ${newRuleType === "block" ? "engelleme" : "izin"} kuralı eklendi.`,
      });
      refresh();
    } catch (err) {
      console.error("DNS kural eklenemedi:", err);
      setFeedback({
        type: "error",
        message: "DNS kuralı eklenirken hata oluştu.",
      });
    }
  };

  const handleDeleteRule = async (id: number) => {
    try {
      await deleteDnsRule(id);
      setFeedback({ type: "success", message: "DNS kuralı silindi." });
      refresh();
    } catch (err) {
      console.error("DNS kural silinemedi:", err);
      setFeedback({
        type: "error",
        message: "DNS kuralı silinirken hata oluştu.",
      });
    }
  };

  // --- Tekli blocklist güncelleme sonuçu ---
  const handleSingleRefreshResult = (result: BlocklistRefreshResult) => {
    if (result.status === "updated") {
      const delta = result.new_domain_count - result.previous_domain_count;
      const deltaStr = delta >= 0 ? `+${formatNumber(delta)}` : formatNumber(delta);
      setFeedback({
        type: "success",
        message: `"${result.name}" güncellendi: ${formatNumber(result.new_domain_count)} domain`,
        details: `Onceki: ${formatNumber(result.previous_domain_count)} | Fark: ${deltaStr}`,
      });
    } else if (result.status === "unchanged") {
      setFeedback({
        type: "info",
        message: `"${result.name}" zaten güncel. ${formatNumber(result.new_domain_count)} domain.`,
      });
    } else {
      setFeedback({
        type: "error",
        message: `"${result.name}" güncellenemedi: ${result.error_message || "Bilinmeyen hata"}`,
      });
    }
    refresh();
  };

  // --- Toplu güncelleme ---
  const handleBulkRefresh = async () => {
    setBulkRefreshing(true);
    try {
      const result: BulkRefreshResult = await refreshAllBlocklists();

      const delta = result.total_domains_after - result.total_domains_before;
      const deltaStr = delta >= 0 ? `+${formatNumber(delta)}` : formatNumber(delta);

      let details = result.results
        .map((r) => {
          if (r.status === "updated") {
            const d = r.new_domain_count - r.previous_domain_count;
            return `${r.name}: ${formatNumber(r.new_domain_count)} domain (${d >= 0 ? "+" : ""}${formatNumber(d)})`;
          } else if (r.status === "unchanged") {
            return `${r.name}: degismedi (${formatNumber(r.new_domain_count)})`;
          } else {
            return `${r.name}: HATA - ${r.error_message}`;
          }
        })
        .join(" | ");

      setFeedback({
        type: result.failed_count > 0 ? "error" : "success",
        message: `${result.total_blocklists} liste kontrol edildi: ${result.updated_count} güncellendi, ${result.unchanged_count} degismedi${result.failed_count > 0 ? `, ${result.failed_count} hata` : ""}. Toplam: ${formatNumber(result.total_domains_after)} domain (${deltaStr})`,
        details: details,
      });
      refresh();
    } catch (err) {
      console.error("Toplu güncelleme hatasi:", err);
      setFeedback({
        type: "error",
        message: "Toplu güncelleme sırasında hata oluştu.",
      });
    } finally {
      setBulkRefreshing(false);
    }
  };

  // --- Blocklist modal işlemleri ---
  const openCreateBlocklistModal = () => {
    setEditingBlocklist(null);
    setBlocklistForm(emptyBlocklistForm);
    setBlocklistFormErrors({});
    setBlocklistModalOpen(true);
  };

  const openEditBlocklistModal = (blocklist: Blocklist) => {
    setEditingBlocklist(blocklist);
    setBlocklistForm({
      name: blocklist.name,
      url: blocklist.url,
      description: blocklist.description || "",
      format: blocklist.format,
      update_frequency_hours: blocklist.update_frequency_hours.toString(),
    });
    setBlocklistFormErrors({});
    setBlocklistModalOpen(true);
  };

  const closeBlocklistModal = () => {
    setBlocklistModalOpen(false);
    setEditingBlocklist(null);
    setBlocklistForm(emptyBlocklistForm);
    setBlocklistFormErrors({});
  };

  const validateBlocklistForm = (): boolean => {
    const errors: Record<string, boolean> = {};
    if (!blocklistForm.name.trim()) errors.name = true;
    if (!blocklistForm.url.trim()) errors.url = true;
    if (
      !blocklistForm.update_frequency_hours ||
      parseInt(blocklistForm.update_frequency_hours) <= 0
    )
      errors.update_frequency_hours = true;
    setBlocklistFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleBlocklistSubmit = async () => {
    if (!validateBlocklistForm()) return;
    setSubmitting(true);

    const payload: Partial<Blocklist> = {
      name: blocklistForm.name.trim(),
      url: blocklistForm.url.trim(),
      description: blocklistForm.description.trim() || null,
      format: blocklistForm.format,
      update_frequency_hours: parseInt(blocklistForm.update_frequency_hours),
    };

    try {
      if (editingBlocklist) {
        const updated = await updateBlocklist(editingBlocklist.id, payload);
        const domainInfo = updated.domain_count > 0
          ? ` ${formatNumber(updated.domain_count)} domain yuklendi.`
          : "";
        setFeedback({
          type: "success",
          message: `"${payload.name}" blocklist güncellendi.${domainInfo}`,
        });
      } else {
        const created = await createBlocklist(payload);
        const domainInfo = created.domain_count > 0
          ? ` ${formatNumber(created.domain_count)} domain yuklendi.`
          : created.last_error
            ? ` Hata: ${created.last_error}`
            : "";
        setFeedback({
          type: created.domain_count > 0 ? "success" : "error",
          message: `"${payload.name}" blocklist eklendi.${domainInfo}`,
        });
      }
      closeBlocklistModal();
      refresh();
    } catch (err) {
      console.error("Blocklist kaydedilemedi:", err);
      setFeedback({
        type: "error",
        message: "Blocklist kaydedilirken hata oluştu.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <TopBar title="DNS Engelleme" connected={connected} />

      {/* Tab navigasyonu */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
              activeTab === tab.key
                ? "bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20"
                : "text-gray-400 bg-glass-light border border-glass-border hover:text-white"
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Geri bildirim mesaji */}
      {feedback && (
        <div
          className={`px-4 py-3 rounded-xl text-sm border ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : feedback.type === "info"
              ? "bg-neon-cyan/10 text-neon-cyan border-neon-cyan/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? (
              <CheckCircle size={16} className="flex-shrink-0" />
            ) : feedback.type === "info" ? (
              <CheckCircle size={16} className="flex-shrink-0" />
            ) : (
              <AlertTriangle size={16} className="flex-shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          {feedback.details && (
            <p className="mt-1.5 text-xs opacity-75 pl-6 break-all">
              {feedback.details}
            </p>
          )}
        </div>
      )}

      {/* GENEL BAKIS */}
      {activeTab === "overview" && stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Toplam Sorgu (24s)"
              value={stats.total_queries_24h.toLocaleString()}
              icon={<Search size={32} />}
              neonColor="cyan"
            />
            <StatCard
              title="Engellenen"
              value={`%${stats.block_percentage}`}
              icon={<Ban size={32} />}
              neonColor="amber"
            />
            <StatCard
              title="Aktif Liste"
              value={stats.active_blocklists}
              icon={<List size={32} />}
              neonColor="green"
            />
            <StatCard
              title="Engelli Domain"
              value={stats.total_blocklist_domains.toLocaleString()}
              icon={<ShieldBan size={32} />}
              neonColor="magenta"
            />
          </div>

          {/* Dışarıdan gelen sorgu uyarısı */}
          {stats.external_queries_24h > 0 && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-neon-red/10 border border-neon-red/30">
              <Globe size={20} className="text-neon-red flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-neon-red">
                  Dışarıdan Gelen DNS Sorguları Tespit Edildi
                </p>
                <p className="text-xs text-gray-300 mt-0.5">
                  Son 24 saatte dışarıdan (WAN) <strong className="text-neon-red">{formatNumber(stats.external_queries_24h)}</strong> DNS sorgusu
                  geldi ve reddedildi. DNS portunuz (53) internete açık olabilir.
                </p>
              </div>
              <button
                onClick={() => {
                  setActiveTab("queries");
                  handleFilterChange("external");
                }}
                className="flex-shrink-0 text-xs px-3 py-1.5 bg-neon-red/20 text-neon-red border border-neon-red/30 rounded-lg hover:bg-neon-red/30 transition-colors"
              >
                Logları Gör
              </button>
            </div>
          )}

          <DnsStatsChart stats={stats} />
          <DomainSearch />
        </div>
      )}

      {/* BLOK LISTELERI - Ekleme, düzenleme, tekli/toplu güncelleme */}
      {activeTab === "blocklists" && (
        <div className="space-y-4">
          {/* Ust kisim: bilgi + butonlar */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-gray-400 text-sm">
              {blocklists.length} blocklist tanimli (
              {blocklists.filter((b) => b.enabled).length} aktif) |{" "}
              <span className="text-gray-300 font-medium">
                {formatNumber(
                  blocklists
                    .filter((b) => b.enabled)
                    .reduce((sum, b) => sum + b.domain_count, 0)
                )}{" "}
                toplam domain
              </span>
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkRefresh}
                disabled={bulkRefreshing}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-amber/10 text-neon-amber border border-neon-amber/20 rounded-xl text-sm font-medium hover:bg-neon-amber/20 hover:shadow-[0_0_20px_rgba(255,176,0,0.15)] transition-all disabled:opacity-50"
              >
                <RotateCw size={16} className={bulkRefreshing ? "animate-spin" : ""} />
                {bulkRefreshing ? "Güncelleniyor..." : "Tümü Güncelle"}
              </button>
              <button
                onClick={openCreateBlocklistModal}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all"
              >
                <Plus size={18} />
                Yeni Liste Ekle
              </button>
            </div>
          </div>

          {/* Blocklist kartlari */}
          <div className="space-y-3">
            {blocklists.map((bl) => (
              <div key={bl.id} className="relative group">
                <BlocklistCard
                  blocklist={bl}
                  onToggle={handleToggleBlocklist}
                  onDelete={handleDeleteBlocklist}
                  onRefreshResult={handleSingleRefreshResult}
                />
                {/* Düzenleme butonu - kart üzerinde hover */}
                <button
                  onClick={() => openEditBlocklistModal(bl)}
                  className="absolute top-4 right-28 p-1.5 rounded-lg text-gray-500 opacity-0 group-hover:opacity-100 hover:text-neon-cyan hover:bg-neon-cyan/10 transition-all"
                  title="Blocklist düzenle"
                >
                  <Pencil size={14} />
                </button>
              </div>
            ))}
            {blocklists.length === 0 && (
              <GlassCard>
                <p className="text-gray-500 text-center py-8">
                  Henüz blocklist eklenmemiş. "Yeni Liste Ekle" ile başlayabilirsiniz.
                </p>
              </GlassCard>
            )}
          </div>
        </div>
      )}

      {/* KURALLAR */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          {/* Yeni kural ekleme */}
          <GlassCard>
            <h4 className="text-sm font-semibold text-gray-300 mb-3">
              Yeni DNS Kuralı Ekle
            </h4>
            <div className="flex gap-2 flex-wrap">
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddRule()}
                placeholder="domain.com"
                className="flex-1 min-w-[200px] bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
              />
              <select
                value={newRuleType}
                onChange={(e) =>
                  setNewRuleType(e.target.value as "block" | "allow")
                }
                className="bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              >
                <option value="block">Engelle</option>
                <option value="allow">İzin Ver</option>
              </select>
              <button
                onClick={handleAddRule}
                disabled={!newDomain.trim()}
                className="px-4 py-2 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-lg text-sm hover:bg-neon-cyan/20 transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <Plus size={16} />
                Ekle
              </button>
            </div>
          </GlassCard>

          {/* Kural listesi */}
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-glass-border">
                    <th className="pb-3 pr-4">Domain</th>
                    <th className="pb-3 pr-4">Tip</th>
                    <th className="pb-3 pr-4">Sebep</th>
                    <th className="pb-3 pr-4">Ekleyen</th>
                    <th className="pb-3 text-right">İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr
                      key={rule.id}
                      className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                    >
                      <td className="py-2.5 pr-4 font-mono text-xs">
                        {rule.domain}
                      </td>
                      <td className="py-2.5 pr-4">
                        <NeonBadge
                          label={rule.rule_type === "block" ? "ENGEL" : "IZIN"}
                          variant={rule.rule_type === "block" ? "red" : "green"}
                        />
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-gray-400">
                        {rule.reason || "--"}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-gray-500">
                        {rule.added_by}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => handleDeleteRule(rule.id)}
                          className="text-gray-500 hover:text-neon-red transition-colors text-xs flex items-center gap-1 ml-auto"
                        >
                          <Trash2 size={12} />
                          Sil
                        </button>
                      </td>
                    </tr>
                  ))}
                  {rules.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-8 text-center text-gray-500"
                      >
                        Henüz DNS kuralı eklenmemiş.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </div>
      )}

      {/* CIHAZ KURALLARI */}
      {activeTab === "device_rules" && (
        <DeviceCustomRulesTab onFeedback={setFeedback} />
      )}

      {/* SORGU LOGLARI */}
      {activeTab === "queries" && (
        <div className="space-y-4">
          {/* Üst satır: filtreler + yenile */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            {/* Filtre butonları */}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter size={14} className="text-gray-500" />
              {(
                [
                  { key: "all", label: "Tümü" },
                  { key: "blocked", label: "Engellenen" },
                  { key: "allowed", label: "İzin Verilen" },
                  { key: "external", label: "Dışarıdan Gelen", icon: Globe },
                  { key: "dot", label: "DNS-over-TLS" },
                  { key: "doh", label: "DNS-over-HTTPS" },
                ] as Array<{ key: QueryFilter; label: string; icon?: typeof Globe }>
              ).map((f) => (
                <button
                  key={f.key}
                  onClick={() => handleFilterChange(f.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    queryFilter === f.key
                      ? f.key === "external"
                        ? "bg-neon-red/20 text-neon-red border border-neon-red/40"
                        : f.key === "blocked"
                        ? "bg-neon-amber/20 text-neon-amber border border-neon-amber/40"
                        : "bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40"
                      : "bg-glass-light text-gray-400 border border-glass-border hover:text-white"
                  }`}
                >
                  {f.icon && <f.icon size={12} />}
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <p className="text-gray-500 text-xs">
                {filterLoading ? "Yükleniyor..." : `${filteredQueries.length} kayıt`}
              </p>
              <button
                onClick={handleManualRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                <RotateCw size={16} className={refreshing ? "animate-spin" : ""} />
                Yenile
              </button>
            </div>
          </div>

          {/* Dışarıdan gelen filtre seçiliyse özet kutu göster */}
          {queryFilter === "external" && externalSummary && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <GlassCard>
                <h4 className="text-xs font-semibold text-neon-red mb-2 flex items-center gap-1">
                  <Globe size={12} />
                  En Çok Sorgu Yapan Dış IP'ler (24s)
                </h4>
                <div className="space-y-1">
                  {externalSummary.top_external_ips.slice(0, 8).map((item) => (
                    <div key={item.client_ip} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-gray-300">{item.client_ip}</span>
                      <span className="text-neon-red font-medium">{formatNumber(item.count)}</span>
                    </div>
                  ))}
                  {externalSummary.top_external_ips.length === 0 && (
                    <p className="text-gray-500 text-xs">Veri yok</p>
                  )}
                </div>
              </GlassCard>
              <GlassCard>
                <h4 className="text-xs font-semibold text-neon-amber mb-2">
                  En Çok Sorgulanan Domainler (Dış)
                </h4>
                <div className="space-y-1">
                  {externalSummary.top_external_domains.slice(0, 8).map((item) => (
                    <div key={item.domain} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-gray-300 truncate max-w-[180px]">{item.domain}</span>
                      <span className="text-neon-amber font-medium">{formatNumber(item.count)}</span>
                    </div>
                  ))}
                  {externalSummary.top_external_domains.length === 0 && (
                    <p className="text-gray-500 text-xs">Veri yok</p>
                  )}
                </div>
              </GlassCard>
            </div>
          )}

          <DnsQueryTable
            queries={filteredQueries.length > 0 || queryFilter !== "all" ? filteredQueries : recentQueries}
            onBlockDomain={async (domain: string) => {
              await createDnsRule({ domain, rule_type: "block" });
              setFeedback({ type: "success", message: `"${domain}" engellendi.` });
              refresh();
              applyQueryFilter(queryFilter);
            }}
            onAllowDomain={async (domain: string) => {
              await createDnsRule({ domain, rule_type: "allow" });
              setFeedback({ type: "success", message: `"${domain}" için izin verildi.` });
              refresh();
              applyQueryFilter(queryFilter);
            }}
            onBlockClient={async (clientIp: string) => {
              try {
                const res = await fetchDevices();
                const device = res.data?.find(
                  (d: { ip_address: string | null }) => d.ip_address === clientIp
                );
                if (device) {
                  await blockDevice(device.id);
                  setFeedback({ type: "success", message: `${clientIp} istemcisi engellendi.` });
                } else {
                  setFeedback({ type: "error", message: `${clientIp} için cihaz bulunamadı.` });
                }
              } catch {
                setFeedback({ type: "error", message: "İstemci engellenirken hata oluştu." });
              }
            }}
          />
        </div>
      )}

      {/* --- BLOCKLIST OLUSTURMA / DUZENLEME MODAL --- */}
      {blocklistModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Arka plan overlay */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closeBlocklistModal}
          />

          {/* Modal içerik */}
          <div className="relative w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Modal baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <List size={20} className="text-neon-cyan" />
                {editingBlocklist
                  ? "Blocklist Düzenle"
                  : "Yeni Blocklist Ekle"}
              </h3>
              <button
                onClick={closeBlocklistModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form alanlari */}
            <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
              {/* Liste Adi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Liste Adi <span className="text-neon-red">*</span>
                </label>
                <div className="relative">
                  <FileText
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="text"
                    value={blocklistForm.name}
                    onChange={(e) =>
                      setBlocklistForm((prev) => ({
                        ...prev,
                        name: e.target.value,
                      }))
                    }
                    placeholder="örn. Steven Black Hosts"
                    className={`w-full pl-10 pr-4 bg-surface-800 border rounded-xl py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      blocklistFormErrors.name
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
                {blocklistFormErrors.name && (
                  <p className="text-xs text-neon-red mt-1">
                    Liste adi zorunludur.
                  </p>
                )}
              </div>

              {/* URL */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Liste URL'si <span className="text-neon-red">*</span>
                </label>
                <div className="relative">
                  <Link
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="url"
                    value={blocklistForm.url}
                    onChange={(e) =>
                      setBlocklistForm((prev) => ({
                        ...prev,
                        url: e.target.value,
                      }))
                    }
                    placeholder="https://raw.githubusercontent.com/.../hosts"
                    className={`w-full pl-10 pr-4 bg-surface-800 border rounded-xl py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                      blocklistFormErrors.url
                        ? "border-neon-red/50 focus:border-neon-red"
                        : "border-white/10 focus:border-neon-cyan/50"
                    }`}
                  />
                </div>
                {blocklistFormErrors.url && (
                  <p className="text-xs text-neon-red mt-1">
                    Liste URL'si zorunludur.
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1.5">
                  HTTP veya HTTPS üzerinden erişilebilir bir blocklist URL'si girin. Format otomatik algilanir.
                </p>
              </div>

              {/* Açıklama */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Açıklama
                </label>
                <textarea
                  value={blocklistForm.description}
                  onChange={(e) =>
                    setBlocklistForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Bu liste hakkında kısa bir açıklama..."
                  rows={2}
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 resize-none"
                />
              </div>

              {/* Format ve Güncelleme Sıklığı */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Format */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Format
                  </label>
                  <select
                    value={blocklistForm.format}
                    onChange={(e) =>
                      setBlocklistForm((prev) => ({
                        ...prev,
                        format: e.target.value as
                          | "hosts"
                          | "domain_list"
                          | "adblock",
                      }))
                    }
                    className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                  >
                    <option value="hosts">Hosts Dosyasi</option>
                    <option value="domain_list">Domain Listesi</option>
                    <option value="adblock">AdBlock Formati</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    {blocklistForm.format === "hosts" &&
                      "0.0.0.0 domain.com veya 127.0.0.1 domain.com"}
                    {blocklistForm.format === "domain_list" &&
                      "Satır başına bir domain veya IP"}
                    {blocklistForm.format === "adblock" &&
                      "||domain.com^ formati (modifierlar desteklenir)"}
                  </p>
                </div>

                {/* Güncelleme Sıklığı */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Güncelleme (saat)
                  </label>
                  <div className="relative">
                    <Clock
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                    />
                    <input
                      type="number"
                      min="1"
                      value={blocklistForm.update_frequency_hours}
                      onChange={(e) =>
                        setBlocklistForm((prev) => ({
                          ...prev,
                          update_frequency_hours: e.target.value,
                        }))
                      }
                      className={`w-full pl-10 pr-4 bg-surface-800 border rounded-xl py-2.5 text-sm text-white focus:outline-none transition-colors ${
                        blocklistFormErrors.update_frequency_hours
                          ? "border-neon-red/50 focus:border-neon-red"
                          : "border-white/10 focus:border-neon-cyan/50"
                      }`}
                    />
                  </div>
                  {blocklistFormErrors.update_frequency_hours && (
                    <p className="text-xs text-neon-red mt-1">
                      Gecerli bir sayi girin.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Modal alt butonlar */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closeBlocklistModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 hover:text-white transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handleBlocklistSubmit}
                disabled={submitting}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Kaydediliyor...
                  </>
                ) : editingBlocklist ? (
                  "Güncelle"
                ) : (
                  "Ekle"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
