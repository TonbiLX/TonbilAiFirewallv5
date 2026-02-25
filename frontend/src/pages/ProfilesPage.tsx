// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Profiller sayfası: çocuk/yetişkin/misafir profil yönetimi - Tam CRUD

import { useEffect, useState, useCallback } from "react";
import {
  Users,
  Plus,
  Pencil,
  Trash2,
  X,
  Clock,
  Shield,
  Gauge,
  CheckCircle,
  AlertTriangle,
  Monitor,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchProfiles,
  createProfile,
  updateProfile,
  deleteProfile,
} from "../services/profileApi";
import { fetchDevices } from "../services/deviceApi";
import { fetchContentCategories } from "../services/contentCategoryApi";
import type { ContentCategory } from "../services/contentCategoryApi";
import type { Profile, Device } from "../types";

// --- Profil tipleri için label/renk esleme ---
const typeVariant: Record<string, "amber" | "cyan" | "magenta"> = {
  child: "amber",
  adult: "cyan",
  guest: "magenta",
};

const typeLabel: Record<string, string> = {
  child: "Çocuk",
  adult: "Yetişkin",
  guest: "Misafir",
};

// Icerik filtre kategorileri artik API'den dinamik yukleniyor

// --- Form veri yapisi ---
interface ProfileFormData {
  name: string;
  profile_type: "child" | "adult" | "guest";
  allowed_hours_start: string;
  allowed_hours_end: string;
  content_filters: string[];
  bandwidth_limit_mbps: string;
}

const emptyForm: ProfileFormData = {
  name: "",
  profile_type: "child",
  allowed_hours_start: "08:00",
  allowed_hours_end: "22:00",
  content_filters: [],
  bandwidth_limit_mbps: "",
};

export function ProfilesPage() {
  const { connected } = useWebSocket();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [contentCategories, setContentCategories] = useState<ContentCategory[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal durumu
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<ProfileFormData>(emptyForm);
  const [formErrors, setFormErrors] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);

  // Silme onay
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // --- Veri yükleme ---
  const loadData = useCallback(async () => {
    try {
      const [profileRes, deviceRes, categories] = await Promise.all([
        fetchProfiles(),
        fetchDevices(),
        fetchContentCategories(),
      ]);
      setProfiles(profileRes.data);
      setDevices(deviceRes.data);
      setContentCategories(categories.filter((c: ContentCategory) => c.enabled));
    } catch (err) {
      console.error("Profil/cihaz verisi alinamadi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 12000);
    return () => clearInterval(interval);
  }, [loadData]);

  // --- Geri bildirim zamanlayici ---
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // --- Profil başına atanmis cihaz sayısı ---
  const getDeviceCount = (profileId: number): number => {
    return devices.filter((d) => d.profile_id === profileId).length;
  };

  // --- Form işlemleri ---
  const openCreateModal = () => {
    setEditingProfile(null);
    setForm(emptyForm);
    setFormErrors({});
    setModalOpen(true);
  };

  const openEditModal = (profile: Profile) => {
    setEditingProfile(profile);
    setForm({
      name: profile.name,
      profile_type: profile.profile_type,
      allowed_hours_start: profile.allowed_hours?.start || "08:00",
      allowed_hours_end: profile.allowed_hours?.end || "22:00",
      content_filters: profile.content_filters || [],
      bandwidth_limit_mbps: profile.bandwidth_limit_mbps?.toString() || "",
    });
    setFormErrors({});
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingProfile(null);
    setForm(emptyForm);
    setFormErrors({});
  };

  const toggleFilter = (filter: string) => {
    setForm((prev) => ({
      ...prev,
      content_filters: prev.content_filters.includes(filter)
        ? prev.content_filters.filter((f) => f !== filter)
        : [...prev.content_filters, filter],
    }));
  };

  const validateForm = (): boolean => {
    const errors: Record<string, boolean> = {};
    if (!form.name.trim()) errors.name = true;
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);

    const payload: any = {
      name: form.name.trim(),
      profile_type: form.profile_type,
      allowed_hours: {
        start: form.allowed_hours_start,
        end: form.allowed_hours_end,
      },
      content_filters:
        form.content_filters.length > 0 ? form.content_filters : null,
      bandwidth_limit_mbps: form.bandwidth_limit_mbps
        ? parseFloat(form.bandwidth_limit_mbps)
        : null,
    };

    try {
      if (editingProfile) {
        await updateProfile(editingProfile.id, payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" profili güncellendi.`,
        });
      } else {
        await createProfile(payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" profili oluşturuldu.`,
        });
      }
      closeModal();
      await loadData();
    } catch (err) {
      console.error("Profil kaydedilemedi:", err);
      setFeedback({
        type: "error",
        message: "Profil kaydedilirken hata oluştu.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  // --- Silme ---
  const handleDelete = async (id: number) => {
    try {
      await deleteProfile(id);
      setDeleteConfirmId(null);
      setFeedback({ type: "success", message: "Profil silindi." });
      await loadData();
    } catch (err) {
      console.error("Profil silinemedi:", err);
      setFeedback({
        type: "error",
        message: "Profil silinirken hata oluştu.",
      });
    }
  };

  // --- Loading ekrani ---
  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <TopBar title="Profiller" connected={connected} />

      {/* Ust bilgi satiri + Yeni Profil butonu */}
      <div className="flex items-center justify-between">
        <p className="text-gray-400 text-sm">
          {profiles.length} profil tanimli
        </p>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2.5 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl text-sm font-medium hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all"
        >
          <Plus size={18} />
          Yeni Profil
        </button>
      </div>

      {/* Geri bildirim mesaji */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle size={16} />
          ) : (
            <AlertTriangle size={16} />
          )}
          {feedback.message}
        </div>
      )}

      {/* Profil kartlari grid */}
      {profiles.length === 0 ? (
        <GlassCard>
          <p className="text-gray-500 text-center py-8">
            Henüz profil oluşturulmamis. "Yeni Profil" butonuyla başlayabilirsiniz.
          </p>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profiles.map((profile) => (
            <GlassCard
              key={profile.id}
              hoverable
              neonColor={typeVariant[profile.profile_type]}
            >
              {/* Kart ust kisim: isim + tip + butonlar */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Users size={24} className="text-neon-cyan" />
                  <div>
                    <h3 className="font-semibold text-lg">{profile.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <NeonBadge
                        label={typeLabel[profile.profile_type]}
                        variant={typeVariant[profile.profile_type]}
                      />
                      <span className="flex items-center gap-1 text-xs text-gray-500">
                        <Monitor size={12} />
                        {getDeviceCount(profile.id)} cihaz
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEditModal(profile)}
                    className="p-2 rounded-lg text-gray-400 hover:text-neon-cyan hover:bg-neon-cyan/10 transition-all"
                    title="Düzenle"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(profile.id)}
                    className="p-2 rounded-lg text-gray-400 hover:text-neon-red hover:bg-neon-red/10 transition-all"
                    title="Sil"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Profil detayları */}
              <div className="space-y-2 text-sm text-gray-400">
                {profile.allowed_hours && (
                  <div className="flex items-center gap-2">
                    <Clock size={14} className="text-neon-amber" />
                    <span>
                      {profile.allowed_hours.start} -{" "}
                      {profile.allowed_hours.end}
                    </span>
                  </div>
                )}
                {profile.content_filters &&
                  profile.content_filters.length > 0 && (
                    <div className="flex items-center gap-2">
                      <Shield size={14} className="text-neon-magenta" />
                      <div className="flex flex-wrap gap-1">
                        {profile.content_filters.map((f) => {
                          const cat = contentCategories.find((c) => c.key === f);
                          return (
                            <span
                              key={f}
                              className="text-xs bg-white/5 px-1.5 py-0.5 rounded"
                              style={cat?.color ? { borderLeft: `2px solid ${cat.color}` } : undefined}
                            >
                              {cat?.name || f}
                              {cat ? ` (${cat.domain_count.toLocaleString()})` : ""}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                {profile.bandwidth_limit_mbps && (
                  <div className="flex items-center gap-2">
                    <Gauge size={14} className="text-neon-green" />
                    <span>{profile.bandwidth_limit_mbps} Mbps limit</span>
                  </div>
                )}
              </div>

              {/* Silme onay */}
              {deleteConfirmId === profile.id && (
                <div className="mt-4 p-3 bg-neon-red/5 border border-neon-red/20 rounded-xl">
                  <p className="text-sm text-neon-red mb-3">
                    Bu profili silmek istediginizden emin misiniz?
                    {getDeviceCount(profile.id) > 0 && (
                      <span className="block text-xs mt-1 text-gray-400">
                        {getDeviceCount(profile.id)} cihaz bu profile atanmis.
                      </span>
                    )}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDelete(profile.id)}
                      className="px-3 py-1.5 bg-neon-red/10 text-neon-red border border-neon-red/20 rounded-lg text-xs hover:bg-neon-red/20 transition-colors"
                    >
                      Evet, Sil
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(null)}
                      className="px-3 py-1.5 bg-glass-light text-gray-400 border border-glass-border rounded-lg text-xs hover:text-white transition-colors"
                    >
                      Iptal
                    </button>
                  </div>
                </div>
              )}
            </GlassCard>
          ))}
        </div>
      )}

      {/* --- OLUSTURMA / DUZENLEME MODAL --- */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Arka plan overlay */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closeModal}
          />

          {/* Modal içerik */}
          <div className="relative w-full max-w-lg bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Modal baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold">
                {editingProfile ? "Profili Düzenle" : "Yeni Profil Oluştur"}
              </h3>
              <button
                onClick={closeModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form alanlari */}
            <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
              {/* Profil Adi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Profil Adi <span className="text-neon-red">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  placeholder="örn. Çocuk Profili"
                  className={`w-full bg-surface-800 border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                    formErrors.name
                      ? "border-neon-red/50 focus:border-neon-red"
                      : "border-white/10 focus:border-neon-cyan/50"
                  }`}
                />
                {formErrors.name && (
                  <p className="text-xs text-neon-red mt-1">
                    Profil adi zorunludur.
                  </p>
                )}
              </div>

              {/* Profil Tipi */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Profil Tipi
                </label>
                <select
                  value={form.profile_type}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      profile_type: e.target.value as
                        | "child"
                        | "adult"
                        | "guest",
                    }))
                  }
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                >
                  <option value="child">Çocuk</option>
                  <option value="adult">Yetişkin</option>
                  <option value="guest">Misafir</option>
                </select>
              </div>

              {/* İzin Verilen Saatler */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  İzin Verilen Saatler
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="time"
                    value={form.allowed_hours_start}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        allowed_hours_start: e.target.value,
                      }))
                    }
                    className="flex-1 bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                  />
                  <span className="text-gray-500 text-sm">-</span>
                  <input
                    type="time"
                    value={form.allowed_hours_end}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        allowed_hours_end: e.target.value,
                      }))
                    }
                    className="flex-1 bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-neon-cyan/50"
                  />
                </div>
              </div>

              {/* İçerik Filtreleri */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  İçerik Filtreleri
                </label>
                <div className="flex flex-wrap gap-2">
                  {contentCategories.length === 0 ? (
                    <p className="text-xs text-gray-500">
                      Henuz icerik kategorisi tanimlanmamis. Once Icerik Filtreleri
                      sayfasindan kategori ekleyin.
                    </p>
                  ) : (
                    contentCategories.map((category) => {
                      const isSelected = form.content_filters.includes(
                        category.key
                      );
                      return (
                        <button
                          key={category.key}
                          type="button"
                          onClick={() => toggleFilter(category.key)}
                          className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${
                            isSelected
                              ? "bg-neon-magenta/10 text-neon-magenta border-neon-magenta/30"
                              : "bg-surface-800 text-gray-400 border-white/10 hover:border-white/20 hover:text-white"
                          }`}
                        >
                          {isSelected && (
                            <span className="mr-1 inline-block">&#10003;</span>
                          )}
                          {category.name}
                          <span className="ml-1 text-gray-500">
                            ({category.domain_count.toLocaleString()})
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Bant Genisligi Limiti */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Bant Genisligi Limiti (Mbps)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={form.bandwidth_limit_mbps}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      bandwidth_limit_mbps: e.target.value,
                    }))
                  }
                  placeholder="Limitsiz birakmak için bos birakin"
                  className="w-full bg-surface-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
                />
              </div>
            </div>

            {/* Modal alt butonlar */}
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
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Kaydediliyor...
                  </>
                ) : editingProfile ? (
                  "Güncelle"
                ) : (
                  "Oluştur"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
