// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// İçerik Filtre Kategorileri sayfası: profillere atanarak engelleme yapılandirmasi
// Kategori CRUD, ikon eslestirme, renk kodlu kartlar

import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Plus,
  Pencil,
  Trash2,
  X,
  CheckCircle,
  AlertTriangle,
  Info,
  // Ikon eslestirme için kullanilacak ikonlar
  Ban,
  Gamepad2,
  Wine,
  Skull,
  ShieldAlert,
  Heart,
  DollarSign,
  Tv,
  Bomb,
  Globe,
  Users,
  Cigarette,
  Swords,
  MessageCircle,
  ShoppingCart,
  Dices,
  Cannabis,
  Flame,
  Laptop,
  Eye,
  type LucideIcon,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { NeonBadge } from "../components/common/NeonBadge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchContentCategories,
  createContentCategory,
  updateContentCategory,
  deleteContentCategory,
} from "../services/contentCategoryApi";
import api from "../services/api";
import type {
  ContentCategory,
  ContentCategoryCreate,
  ContentCategoryUpdate,
} from "../services/contentCategoryApi";

// --- Ikon string -> Lucide ikon eslestirmesi ---
const iconMap: Record<string, LucideIcon> = {
  ban: Ban,
  shield: Shield,
  "shield-alert": ShieldAlert,
  gamepad: Gamepad2,
  gamepad2: Gamepad2,
  wine: Wine,
  skull: Skull,
  heart: Heart,
  dollar: DollarSign,
  "dollar-sign": DollarSign,
  tv: Tv,
  bomb: Bomb,
  globe: Globe,
  users: Users,
  cigarette: Cigarette,
  swords: Swords,
  "message-circle": MessageCircle,
  chat: MessageCircle,
  shopping: ShoppingCart,
  "shopping-cart": ShoppingCart,
  dices: Dices,
  dice: Dices,
  gambling: Dices,
  cannabis: Cannabis,
  flame: Flame,
  fire: Flame,
  laptop: Laptop,
  eye: Eye,
  adult: Eye,
  malware: Skull,
  violence: Swords,
  drugs: Cannabis,
  alcohol: Wine,
  social: Users,
};

function getIconComponent(iconName: string): LucideIcon {
  const normalizedName = iconName.toLowerCase().trim();
  return iconMap[normalizedName] || Shield;
}

// --- Blocklist tipi (DNS sayfasindan) ---
interface Blocklist {
  id: number;
  name: string;
  domain_count: number;
  enabled: boolean;
}

// --- Kategori form yapisi ---
interface CategoryFormData {
  key: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  example_domains: string;
  custom_domains: string;
  blocklist_ids: number[];
  enabled: boolean;
}

const emptyCategoryForm: CategoryFormData = {
  key: "",
  name: "",
  description: "",
  icon: "shield",
  color: "#00f0ff",
  example_domains: "",
  custom_domains: "",
  blocklist_ids: [],
  enabled: true,
};

// --- Hazir renk paleti ---
const presetColors = [
  "#00f0ff", // cyan
  "#ff00e5", // magenta
  "#39ff14", // green
  "#ffb800", // amber
  "#ff003c", // red
  "#8b5cf6", // purple
  "#3b82f6", // blue
  "#f97316", // orange
  "#ec4899", // pink
  "#14b8a6", // teal
];

// --- Hazir ikon listesi ---
const presetIcons = [
  "shield",
  "shield-alert",
  "ban",
  "skull",
  "eye",
  "gamepad",
  "wine",
  "cannabis",
  "dices",
  "swords",
  "flame",
  "bomb",
  "heart",
  "dollar-sign",
  "globe",
  "users",
  "tv",
  "shopping-cart",
  "message-circle",
  "laptop",
];

export function ContentCategoriesPage() {
  const { connected } = useWebSocket();
  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Geri bildirim
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Modal durumu
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] =
    useState<ContentCategory | null>(null);
  const [form, setForm] = useState<CategoryFormData>(emptyCategoryForm);
  const [submitting, setSubmitting] = useState(false);

  // Blocklist listesi (modal icin)
  const [availableBlocklists, setAvailableBlocklists] = useState<Blocklist[]>([]);

  // --- Geri bildirim zamanlayici ---
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // --- Veri yükleme ---
  const loadData = useCallback(async () => {
    try {
      const data = await fetchContentCategories();
      setCategories(data);
      setError(null);
    } catch (err) {
      setError("İçerik kategorileri yüklenemedi");
      console.error("Kategori yükleme hatasi:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // --- Kategori toggle ---
  const handleToggleCategory = async (category: ContentCategory) => {
    try {
      await updateContentCategory(category.id, {
        enabled: !category.enabled,
      });
      setFeedback({
        type: "success",
        message: `"${category.name}" ${
          category.enabled ? "devre disi birakildi" : "etkinlestirildi"
        }.`,
      });
      await loadData();
    } catch (err: unknown) {
      console.error("Kategori toggle hatasi:", err);
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setFeedback({
        type: "error",
        message: axiosErr?.response?.data?.detail || "Kategori durumu değiştirilemedi.",
      });
    }
  };

  // --- Kategori silme ---
  const handleDeleteCategory = async (id: number, name: string) => {
    try {
      await deleteContentCategory(id);
      setFeedback({ type: "success", message: `"${name}" kategorisi silindi.` });
      await loadData();
    } catch (err: unknown) {
      console.error("Kategori silme hatasi:", err);
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setFeedback({
        type: "error",
        message: axiosErr?.response?.data?.detail || "Kategori silinirken hata oluştu.",
      });
    }
  };

  // --- Blocklist listesini yukle ---
  const loadBlocklists = async () => {
    try {
      const { data } = await api.get("/dns/blocklists");
      setAvailableBlocklists(data);
    } catch (err) {
      console.error("Blocklist listesi yuklenemedi:", err);
    }
  };

  // --- Modal islemleri ---
  const openCreateModal = async () => {
    setEditingCategory(null);
    setForm(emptyCategoryForm);
    await loadBlocklists();
    setModalOpen(true);
  };

  const openEditModal = async (category: ContentCategory) => {
    setEditingCategory(category);
    setForm({
      key: category.key,
      name: category.name,
      description: category.description,
      icon: category.icon,
      color: category.color,
      example_domains: category.example_domains?.join(", ") || "",
      custom_domains: category.custom_domains || "",
      blocklist_ids: category.blocklist_ids || [],
      enabled: category.enabled,
    });
    await loadBlocklists();
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingCategory(null);
    setForm(emptyCategoryForm);
  };

  const handleSubmit = async () => {
    if (!form.key.trim() || !form.name.trim()) return;
    setSubmitting(true);

    const exampleDomains = form.example_domains
      .split(",")
      .map((d) => d.trim())
      .filter((d) => d.length > 0);

    try {
      if (editingCategory) {
        const payload: ContentCategoryUpdate = {
          name: form.name.trim(),
          description: form.description.trim(),
          icon: form.icon.trim(),
          color: form.color.trim(),
          example_domains: exampleDomains,
          custom_domains: form.custom_domains.trim() || undefined,
          blocklist_ids: form.blocklist_ids,
          enabled: form.enabled,
        };
        await updateContentCategory(editingCategory.id, payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" kategorisi güncellendi.`,
        });
      } else {
        const payload: ContentCategoryCreate = {
          key: form.key.trim(),
          name: form.name.trim(),
          description: form.description.trim(),
          icon: form.icon.trim(),
          color: form.color.trim(),
          example_domains: exampleDomains,
          custom_domains: form.custom_domains.trim() || undefined,
          blocklist_ids: form.blocklist_ids,
        };
        await createContentCategory(payload);
        setFeedback({
          type: "success",
          message: `"${payload.name}" kategorisi eklendi.`,
        });
      }
      closeModal();
      await loadData();
    } catch (err: unknown) {
      console.error("Kategori kaydetme hatasi:", err);
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail;
      setFeedback({
        type: "error",
        message: detail || "Kategori kaydedilirken hata oluştu.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const inputClass =
    "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 transition-colors";
  const labelClass =
    "block text-xs text-gray-400 mb-1 uppercase tracking-wider";

  return (
    <div className="space-y-6">
      <TopBar title="İçerik Filtre Kategorileri" connected={connected} />

      {/* Baslik */}
      <div className="flex items-center gap-3 mb-2">
        <Shield size={28} className="text-neon-cyan" />
        <div>
          <h2 className="text-xl font-bold text-white">
            İçerik Filtre Kategorileri
          </h2>
          <p className="text-sm text-gray-400">
            Profillerde kullanilan engelleme kategorilerini yonetin
          </p>
        </div>
      </div>

      {/* Hata mesaji */}
      {error && (
        <div className="bg-neon-red/10 border border-neon-red/30 rounded-xl p-4 text-neon-red text-sm">
          {error}
        </div>
      )}

      {/* Geri bildirim */}
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

      {/* Açıklama Kutusu */}
      <GlassCard>
        <div className="flex items-start gap-3">
          <Info size={20} className="text-neon-cyan mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-400 leading-relaxed">
            Bu kategoriler, profillere atanarak hangi tur sitelerin
            engellenmesini saglar. Örneğin bir çocuk profiline 'Kumar' ve
            'Yetişkin İçerik' kategorileri atandiginda, bu kategorilerdeki tum
            siteler o profile sahip cihazlarda engellenir.
          </p>
        </div>
      </GlassCard>

      {/* Ust Bar: Toplam + Ekle Butonu */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          {categories.length} kategori tanimli (
          {categories.filter((c) => c.enabled).length} aktif)
        </p>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 hover:bg-neon-cyan/20 border border-neon-cyan/30 text-neon-cyan rounded-xl text-sm transition-all"
        >
          <Plus size={16} />
          Kategori Ekle
        </button>
      </div>

      {/* Kategori Grid */}
      {categories.length === 0 ? (
        <GlassCard>
          <p className="text-gray-500 text-center py-8">
            Henüz içerik kategorisi eklenmemiş. "Kategori Ekle" ile
            başlayabilirsiniz.
          </p>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {categories.map((category) => {
            const IconComp = getIconComponent(category.icon);
            return (
              <div
                key={category.id}
                className={`relative glass-card p-5 transition-all hover:shadow-lg ${
                  !category.enabled ? "opacity-60" : ""
                }`}
                style={{ borderLeft: `4px solid ${category.color}` }}
              >
                {/* Ust kisim: Ikon + Ad + Toggle */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{
                        backgroundColor: `${category.color}15`,
                        border: `1px solid ${category.color}30`,
                      }}
                    >
                      <IconComp size={20} style={{ color: category.color }} />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        {category.name}
                      </h4>
                      <p className="text-xs text-gray-500 font-mono">
                        {category.key}
                      </p>
                    </div>
                  </div>

                  {/* Toggle */}
                  <button
                    onClick={() => handleToggleCategory(category)}
                    className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${
                      category.enabled ? "bg-neon-green/30" : "bg-gray-700"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full transition-transform ${
                        category.enabled
                          ? "translate-x-5 bg-neon-green shadow-[0_0_8px_rgba(57,255,20,0.5)]"
                          : "bg-gray-500"
                      }`}
                    />
                  </button>
                </div>

                {/* Açıklama */}
                <p className="text-xs text-gray-400 mb-3 line-clamp-2">
                  {category.description}
                </p>

                {/* Ornek Domainler */}
                {category.example_domains &&
                  category.example_domains.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1.5">
                        Ornek Domainler
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {category.example_domains
                          .slice(0, 5)
                          .map((domain, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-surface-800 border border-glass-border rounded-md text-xs font-mono text-gray-300"
                            >
                              {domain}
                            </span>
                          ))}
                        {category.example_domains.length > 5 && (
                          <span className="px-2 py-0.5 text-xs text-gray-500">
                            +{category.example_domains.length - 5} daha
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                {/* Bagli Blocklist'ler */}
                {category.blocklists && category.blocklists.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1.5">
                      Bagli Listeler
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {category.blocklists.map((bl) => (
                        <span
                          key={bl.id}
                          className="px-2 py-0.5 bg-neon-cyan/5 border border-neon-cyan/20 rounded-md text-xs text-neon-cyan"
                        >
                          {bl.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Domain Sayisi + Islemler */}
                <div className="flex items-center justify-between pt-3 border-t border-glass-border">
                  <NeonBadge
                    label={`${category.domain_count.toLocaleString()} domain`}
                    variant="cyan"
                  />

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEditModal(category)}
                      className="p-1.5 text-gray-500 hover:text-neon-cyan hover:bg-neon-cyan/10 rounded-lg transition-all"
                      title="Kategoriyi Düzenle"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() =>
                        handleDeleteCategory(category.id, category.name)
                      }
                      className="p-1.5 text-gray-500 hover:text-neon-red hover:bg-neon-red/10 rounded-lg transition-all"
                      title="Kategoriyi Sil"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ========== KATEGORI EKLEME / DUZENLEME MODAL ========== */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Overlay */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={closeModal}
          />

          {/* Modal */}
          <div className="relative w-full max-w-xl bg-surface-900 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Baslik */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Shield size={20} className="text-neon-cyan" />
                {editingCategory
                  ? "Kategori Düzenle"
                  : "Yeni Kategori Ekle"}
              </h3>
              <button
                onClick={closeModal}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Form */}
            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Kategori Anahtar */}
                <div>
                  <label className={labelClass}>
                    Anahtar (Key) <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.key}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        key: e.target.value.toLowerCase().replace(/\s+/g, "_"),
                      }))
                    }
                    placeholder="örn. gambling"
                    className={inputClass}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Benzersiz tanimlayici (kucuk harf, alt çizgi)
                  </p>
                </div>

                {/* Kategori Adi */}
                <div>
                  <label className={labelClass}>
                    Kategori Adi <span className="text-neon-red">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="örn. Kumar"
                    className={inputClass}
                  />
                </div>
              </div>

              {/* Açıklama */}
              <div>
                <label className={labelClass}>Açıklama</label>
                <textarea
                  value={form.description}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Bu kategori hakkında kısa bir açıklama..."
                  rows={2}
                  className="w-full bg-surface-800 border border-glass-border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 resize-none transition-colors"
                />
              </div>

              {/* Ikon Secimi */}
              <div>
                <label className={labelClass}>Ikon</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {presetIcons.map((iconName) => {
                    const Ico = getIconComponent(iconName);
                    return (
                      <button
                        key={iconName}
                        onClick={() =>
                          setForm((prev) => ({ ...prev, icon: iconName }))
                        }
                        className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all ${
                          form.icon === iconName
                            ? "bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan"
                            : "bg-surface-800 border border-glass-border text-gray-400 hover:text-white hover:border-white/30"
                        }`}
                        title={iconName}
                      >
                        <Ico size={16} />
                      </button>
                    );
                  })}
                </div>
                <input
                  type="text"
                  value={form.icon}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, icon: e.target.value }))
                  }
                  placeholder="Ikon adi (örn. shield, ban, skull)"
                  className={inputClass}
                />
              </div>

              {/* Renk Secimi */}
              <div>
                <label className={labelClass}>Renk</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {presetColors.map((color) => (
                    <button
                      key={color}
                      onClick={() =>
                        setForm((prev) => ({ ...prev, color }))
                      }
                      className={`w-8 h-8 rounded-lg transition-all border-2 ${
                        form.color === color
                          ? "border-white scale-110"
                          : "border-transparent hover:border-white/30"
                      }`}
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
                <input
                  type="text"
                  value={form.color}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, color: e.target.value }))
                  }
                  placeholder="#00f0ff"
                  className={inputClass}
                />
              </div>

              {/* Engelleme Listeleri (Blocklist baglantisi) */}
              <div>
                <label className={labelClass}>
                  Engelleme Listeleri
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  Bu kategoriye baglanacak domain engelleme listelerini secin
                </p>
                {availableBlocklists.length === 0 ? (
                  <p className="text-xs text-gray-600 py-2">
                    Henuz engelleme listesi tanimlanmamis
                  </p>
                ) : (
                  <div className="max-h-40 overflow-y-auto space-y-1 bg-surface-800 border border-glass-border rounded-lg p-2">
                    {availableBlocklists.map((bl) => (
                      <label
                        key={bl.id}
                        className="flex items-center gap-2 cursor-pointer hover:bg-white/5 rounded px-2 py-1"
                      >
                        <input
                          type="checkbox"
                          checked={form.blocklist_ids.includes(bl.id)}
                          onChange={() => {
                            setForm((prev) => ({
                              ...prev,
                              blocklist_ids: prev.blocklist_ids.includes(bl.id)
                                ? prev.blocklist_ids.filter((id) => id !== bl.id)
                                : [...prev.blocklist_ids, bl.id],
                            }));
                          }}
                          className="w-3.5 h-3.5 accent-neon-cyan"
                        />
                        <span className="text-sm text-gray-300 flex-1">
                          {bl.name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {(bl.domain_count || 0).toLocaleString()} domain
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Ozel Domainler */}
              <div>
                <label className={labelClass}>
                  Ozel Domainler (satir basina bir domain)
                </label>
                <textarea
                  value={form.custom_domains}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      custom_domains: e.target.value,
                    }))
                  }
                  placeholder={"casino.com\nbet365.com\npokerstars.com"}
                  rows={4}
                  className="w-full bg-surface-800 border border-glass-border rounded-xl px-4 py-2.5 text-sm text-white font-mono placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 resize-none transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Elle domain ekleyin. Her satira bir domain yazin.
                </p>
              </div>

              {/* Ornek Domainler */}
              <div>
                <label className={labelClass}>
                  Ornek Domainler (virgul ile ayirin, sadece gosterim amacli)
                </label>
                <textarea
                  value={form.example_domains}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      example_domains: e.target.value,
                    }))
                  }
                  placeholder="casino.com, bet365.com, poker.com"
                  rows={2}
                  className="w-full bg-surface-800 border border-glass-border rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50 resize-none transition-colors"
                />
              </div>

              {/* Aktif/Pasif */}
              <div className="flex items-center">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.enabled}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        enabled: e.target.checked,
                      }))
                    }
                    className="w-4 h-4 rounded border-glass-border bg-surface-800 text-neon-cyan focus:ring-neon-cyan/50 accent-neon-cyan"
                  />
                  <span className="text-sm text-gray-300">
                    Kategori Aktif
                  </span>
                </label>
              </div>
            </div>

            {/* Modal Alt Butonlar */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
              <button
                onClick={closeModal}
                className="px-4 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 hover:text-white transition-all"
              >
                Iptal
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !form.key.trim() || !form.name.trim()}
                className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 rounded-xl hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-transparent border-t-neon-cyan rounded-full animate-spin" />
                    Kaydediliyor...
                  </>
                ) : editingCategory ? (
                  "Güncelle"
                ) : (
                  "Kategori Ekle"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
