// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz bazinda özel DNS kurallari tabı: kural listesi, ekleme/düzenleme modali, silme

import { useState, useEffect } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  X,
  Smartphone,
  Info,
  ExternalLink,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import { LoadingSpinner } from "../common/LoadingSpinner";
import {
  fetchDeviceCustomRules,
  createDeviceCustomRule,
  updateDeviceCustomRule,
  deleteDeviceCustomRule,
} from "../../services/deviceCustomRuleApi";
import { fetchDevices } from "../../services/deviceApi";
import type { DeviceCustomRule, Device } from "../../types";

interface Props {
  onFeedback: (feedback: { type: "success" | "error"; message: string }) => void;
}

export function DeviceCustomRulesTab({ onFeedback }: Props) {
  const navigate = useNavigate();
  const [rules, setRules] = useState<DeviceCustomRule[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDeviceId, setFilterDeviceId] = useState<number | undefined>(undefined);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<DeviceCustomRule | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | "">("");
  const [domainInput, setDomainInput] = useState("");
  const [ruleType, setRuleType] = useState<"block" | "allow">("block");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadRules = async () => {
    try {
      const data = await fetchDeviceCustomRules(filterDeviceId);
      setRules(data);
    } catch {
      onFeedback({ type: "error", message: "Kurallar yuklenirken hata oluştu." });
    }
  };

  const loadDevices = async () => {
    try {
      const devRes = await fetchDevices();
      setDevices(devRes.data || []);
    } catch {
      // silent
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([loadRules(), loadDevices()]).finally(() =>
      setLoading(false)
    );
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadRules();
  }, [filterDeviceId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openCreateModal = () => {
    setEditingRule(null);
    setSelectedDeviceId("");
    setDomainInput("");
    setRuleType("block");
    setReason("");
    setModalOpen(true);
  };

  const openEditModal = (rule: DeviceCustomRule) => {
    setEditingRule(rule);
    setSelectedDeviceId(rule.device_id);
    setDomainInput(rule.domain);
    setRuleType(rule.rule_type);
    setReason(rule.reason || "");
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingRule(null);
  };

  const handleSubmit = async () => {
    // Düzenleme modunda
    if (editingRule) {
      const domain = domainInput.trim().toLowerCase();
      if (!domain) {
        onFeedback({ type: "error", message: "Domain bos olamaz." });
        return;
      }

      setSubmitting(true);
      try {
        await updateDeviceCustomRule(editingRule.id, {
          domain,
          rule_type: ruleType,
          reason: reason.trim() || undefined,
        });
        onFeedback({
          type: "success",
          message: `Kural başarıyla güncellendi.`,
        });
        closeModal();
        await loadRules();
      } catch (err: any) {
        const detail = err?.response?.data?.detail || "Kural güncellenirken hata oluştu.";
        onFeedback({ type: "error", message: detail });
      } finally {
        setSubmitting(false);
      }
      return;
    }

    // Yeni kural ekleme
    if (!selectedDeviceId) {
      onFeedback({ type: "error", message: "Lütfen bir cihaz seçin." });
      return;
    }

    const domain = domainInput.trim().toLowerCase();
    if (!domain) {
      onFeedback({ type: "error", message: "Lütfen bir domain girin." });
      return;
    }

    setSubmitting(true);
    try {
      await createDeviceCustomRule(Number(selectedDeviceId), {
        domain,
        rule_type: ruleType,
        reason: reason.trim() || undefined,
      });
      onFeedback({
        type: "success",
        message: `"${domain}" kuralı başarıyla eklendi.`,
      });
      closeModal();
      await loadRules();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Kural eklenirken hata oluştu.";
      onFeedback({ type: "error", message: detail });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (ruleId: number, domain: string) => {
    try {
      await deleteDeviceCustomRule(ruleId);
      onFeedback({ type: "success", message: `"${domain}" kuralı silindi.` });
      await loadRules();
    } catch {
      onFeedback({ type: "error", message: "Kural silinirken hata oluştu." });
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  const isEditing = !!editingRule;

  return (
    <div className="space-y-4">
      {/* Bilgi kutusu: Servis engelleme yonlendirmesi */}
      <div className="flex items-start gap-3 px-4 py-3 bg-neon-cyan/5 border border-neon-cyan/10 rounded-xl">
        <Info size={18} className="text-neon-cyan mt-0.5 shrink-0" />
        <div className="text-xs text-gray-300">
          <span className="text-white font-medium">Bu sayfa özel domain kurallari içindir.</span>{" "}
          Servis bazli engelleme (YouTube, Netflix, TikTok vb.) için{" "}
          <button
            onClick={() => navigate("/devices")}
            className="inline-flex items-center gap-1 text-neon-cyan hover:underline"
          >
            Cihaz Servisleri <ExternalLink size={11} />
          </button>{" "}
          sayfasıni kullanın.
        </div>
      </div>

      {/* Ust bar: filtre + ekle butonu */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={filterDeviceId ?? ""}
          onChange={(e) =>
            setFilterDeviceId(
              e.target.value ? Number(e.target.value) : undefined
            )
          }
          className="bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 min-w-[200px]"
        >
          <option value="">Tum Cihazlar</option>
          {devices.map((d) => (
            <option key={d.id} value={d.id}>
              {d.hostname || d.ip_address} ({d.ip_address})
            </option>
          ))}
        </select>

        <button
          onClick={openCreateModal}
          className="ml-auto flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm hover:bg-neon-cyan/20 transition-colors"
        >
          <Plus size={16} />
          Kural Ekle
        </button>
      </div>

      {/* Kural tablosu */}
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-glass-border">
                <th className="pb-3 pr-4">Cihaz</th>
                <th className="pb-3 pr-4">Domain</th>
                <th className="pb-3 pr-4">Tip</th>
                <th className="pb-3 pr-4">Sebep</th>
                <th className="pb-3 pr-4">Ekleyen</th>
                <th className="pb-3 pr-4">Tarih</th>
                <th className="pb-3 text-right">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr
                  key={rule.id}
                  className="border-b border-glass-border/50 hover:bg-glass-light transition-colors"
                >
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <Smartphone size={14} className="text-gray-500" />
                      <div>
                        <div className="text-xs text-white">
                          {rule.device_hostname || "Bilinmeyen"}
                        </div>
                        <div className="text-[10px] text-gray-500">
                          {rule.device_ip}
                        </div>
                      </div>
                    </div>
                  </td>
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
                  <td className="py-2.5 pr-4 text-xs text-gray-500">
                    {rule.created_at
                      ? new Date(rule.created_at).toLocaleDateString("tr-TR", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "--"}
                  </td>
                  <td className="py-2.5 text-right">
                    <div className="flex items-center gap-2 justify-end">
                      <button
                        onClick={() => openEditModal(rule)}
                        className="text-gray-500 hover:text-neon-cyan transition-colors text-xs flex items-center gap-1"
                        title="Kuralı düzenle"
                      >
                        <Pencil size={12} />
                        Düzenle
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id, rule.domain)}
                        className="text-gray-500 hover:text-neon-red transition-colors text-xs flex items-center gap-1"
                        title="Kuralı sil"
                      >
                        <Trash2 size={12} />
                        Sil
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rules.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    {filterDeviceId
                      ? "Bu cihaz için özel kural bulunmuyor."
                      : "Henüz cihaz özel kuralı eklenmemiş."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* KURAL EKLEME / DUZENLEME MODAL */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closeModal}
          />
          <div className="relative w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                {isEditing ? (
                  <Pencil size={20} className="text-neon-amber" />
                ) : (
                  <Smartphone size={20} className="text-neon-cyan" />
                )}
                {isEditing ? "Kural Düzenle" : "Cihaz Özel Kural Ekle"}
              </h3>
              <button
                onClick={closeModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form */}
            <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
              {/* Cihaz secimi - düzenleme modunda devre disi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Cihaz {!isEditing && <span className="text-neon-red">*</span>}
                </label>
                {isEditing ? (
                  <div className="flex items-center gap-2 px-4 py-2.5 bg-surface-800 border border-white/10 rounded-xl text-sm text-gray-400">
                    <Smartphone size={14} />
                    {editingRule?.device_hostname || "Bilinmeyen"} ({editingRule?.device_ip})
                  </div>
                ) : (
                  <select
                    value={selectedDeviceId}
                    onChange={(e) =>
                      setSelectedDeviceId(
                        e.target.value ? Number(e.target.value) : ""
                      )
                    }
                    className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                  >
                    <option value="">Cihaz seçin...</option>
                    {devices.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.hostname || "Bilinmeyen"} ({d.ip_address})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Domain / IP giriş */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Domain veya IP <span className="text-neon-red">*</span>
                </label>
                <input
                  type="text"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  placeholder="ornek.com veya 1.2.3.4"
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>

              {/* Kural tipi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Kural Tipi
                </label>
                <select
                  value={ruleType}
                  onChange={(e) =>
                    setRuleType(e.target.value as "block" | "allow")
                  }
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  <option value="block">Engelle</option>
                  <option value="allow">İzin Ver (Override)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  "İzin Ver" secenegi global engelleri bu cihaz için geçersiz kilar.
                </p>
              </div>

              {/* Sebep */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Sebep (opsiyonel)
                </label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="örn. Çocuk güvenliği"
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
            </div>

            {/* Butonlar */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closeModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 hover:text-white transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium border rounded-xl transition-all disabled:opacity-50 ${
                  isEditing
                    ? "bg-neon-amber/10 text-neon-amber border-neon-amber/20 hover:bg-neon-amber/20 hover:shadow-[0_0_20px_rgba(255,180,0,0.15)]"
                    : "bg-neon-cyan/10 text-neon-cyan border-neon-cyan/20 hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)]"
                }`}
              >
                {submitting ? (
                  <>
                    <div className={`w-4 h-4 border-2 border-transparent rounded-full animate-spin ${
                      isEditing ? "border-t-neon-amber" : "border-t-neon-cyan"
                    }`} />
                    Kaydediliyor...
                  </>
                ) : isEditing ? (
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
