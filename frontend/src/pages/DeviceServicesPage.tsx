// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cihaz bazinda servis engelleme sayfası
// AdGuard Home tarzi toggle ile servis engelle/ac

import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Shield,
  ShieldOff,
  Search,
  Tv,
  Gamepad2,
  MessageCircle,
  Users,
  ShoppingCart,
  Brain,
  Globe,
  HardDrive,
  Heart,
  Dices,
  Eye,
  Package,
} from "lucide-react";
import { TopBar } from "../components/layout/TopBar";
import { GlassCard } from "../components/common/GlassCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useWebSocket } from "../hooks/useWebSocket";
import {
  fetchDeviceServices,
  fetchServiceGroups,
  toggleDeviceService,
} from "../services/serviceBlockApi";
import { fetchDevices } from "../services/deviceApi";
import type { DeviceBlockedService, ServiceGroup, Device } from "../types";

const GROUP_ICONS: Record<string, typeof Tv> = {
  streaming: Tv,
  gaming: Gamepad2,
  messenger: MessageCircle,
  social_network: Users,
  shopping: ShoppingCart,
  ai: Brain,
  cdn: Globe,
  hosting: HardDrive,
  dating: Heart,
  gambling: Dices,
  privacy: Eye,
  software: Package,
};

const GROUP_LABELS: Record<string, string> = {
  streaming: "Yayin",
  gaming: "Oyun",
  messenger: "Mesajlasma",
  social_network: "Sosyal Ag",
  shopping: "Alisveris",
  ai: "Yapay Zeka",
  cdn: "CDN",
  hosting: "Hosting",
  dating: "Tanisma",
  gambling: "Kumar",
  privacy: "Gizlilik",
  software: "Yazilim",
};

export default function DeviceServicesPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const { connected } = useWebSocket();

  const [device, setDevice] = useState<Device | null>(null);
  const [services, setServices] = useState<DeviceBlockedService[]>([]);
  const [groups, setGroups] = useState<ServiceGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeGroup, setActiveGroup] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [togglingService, setTogglingService] = useState<string | null>(null);

  const numDeviceId = Number(deviceId);

  const loadData = useCallback(async () => {
    try {
      const [svcData, grpData, devicesData] = await Promise.all([
        fetchDeviceServices(numDeviceId),
        fetchServiceGroups(),
        fetchDevices(),
      ]);
      setServices(svcData);
      setGroups(grpData);
      const dev = devicesData.data?.find(
        (d: Device) => d.id === numDeviceId
      );
      if (dev) setDevice(dev);
    } catch (err) {
      console.error("Veri yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  }, [numDeviceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (feedback) {
      const t = setTimeout(() => setFeedback(null), 3000);
      return () => clearTimeout(t);
    }
  }, [feedback]);

  const handleToggle = async (serviceId: string, currentBlocked: boolean) => {
    const newBlocked = !currentBlocked;
    setTogglingService(serviceId);

    // Iyimser güncelleme
    setServices((prev) =>
      prev.map((s) =>
        s.service_id === serviceId ? { ...s, blocked: newBlocked } : s
      )
    );

    try {
      await toggleDeviceService(numDeviceId, serviceId, newBlocked);
      const svc = services.find((s) => s.service_id === serviceId);
      setFeedback({
        type: "success",
        message: `${svc?.name || serviceId} ${newBlocked ? "engellendi" : "acildi"}`,
      });
    } catch (err) {
      // Geri al
      setServices((prev) =>
        prev.map((s) =>
          s.service_id === serviceId
            ? { ...s, blocked: currentBlocked }
            : s
        )
      );
      setFeedback({ type: "error", message: "İşlem başarısız oldu" });
    } finally {
      setTogglingService(null);
    }
  };

  const filteredServices = services.filter((s) => {
    const matchGroup =
      activeGroup === "all" || s.group_name === activeGroup;
    const matchSearch =
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.service_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchGroup && matchSearch;
  });

  const blockedCount = services.filter((s) => s.blocked).length;

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <TopBar
        title={`Servis Engelleme - ${device?.hostname || device?.ip_address || "Cihaz"}`}
        connected={connected}
      />

      {/* Ust bar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate("/devices")}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={18} />
          <span>Cihazlara Don</span>
        </button>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <span>
            IP: <span className="text-white font-mono">{device?.ip_address}</span>
          </span>
          <span>
            MAC: <span className="text-white font-mono">{device?.mac_address}</span>
          </span>
          <span>
            Engelli:{" "}
            <span className="text-neon-red font-bold">{blockedCount}</span> /{" "}
            {services.length}
          </span>
        </div>
      </div>

      {/* Feedback */}
      {feedback && (
        <div
          className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border mb-4 ${
            feedback.type === "success"
              ? "bg-neon-green/10 text-neon-green border-neon-green/20"
              : "bg-neon-red/10 text-neon-red border-neon-red/20"
          }`}
        >
          {feedback.type === "success" ? (
            <Shield size={16} />
          ) : (
            <ShieldOff size={16} />
          )}
          {feedback.message}
        </div>
      )}

      {/* Arama */}
      <div className="relative mb-4">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
        />
        <input
          type="text"
          placeholder="Servis ara... (YouTube, Netflix, WhatsApp...)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-surface-800 border border-glass-border rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
        />
      </div>

      {/* Grup tablari */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setActiveGroup("all")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeGroup === "all"
              ? "bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30"
              : "bg-surface-800 text-gray-400 border border-glass-border hover:text-white"
          }`}
        >
          Tümü ({services.length})
        </button>
        {groups.map((g) => {
          const Icon = GROUP_ICONS[g.group] || Globe;
          return (
            <button
              key={g.group}
              onClick={() => setActiveGroup(g.group)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeGroup === g.group
                  ? "bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30"
                  : "bg-surface-800 text-gray-400 border border-glass-border hover:text-white"
              }`}
            >
              <Icon size={12} />
              {GROUP_LABELS[g.group] || g.group} ({g.count})
            </button>
          );
        })}
      </div>

      {/* Servis grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {filteredServices.map((svc) => (
          <GlassCard key={svc.service_id} hoverable>
            <div className="flex flex-col items-center text-center p-3 gap-2">
              {/* SVG ikon */}
              {svc.icon_svg ? (
                <div
                  className={`w-10 h-10 flex items-center justify-center ${
                    svc.blocked ? "opacity-40 grayscale" : ""
                  }`}
                  dangerouslySetInnerHTML={{ __html: svc.icon_svg }}
                />
              ) : (
                <div
                  className={`w-10 h-10 flex items-center justify-center rounded-lg bg-surface-700 ${
                    svc.blocked ? "opacity-40" : ""
                  }`}
                >
                  <Globe size={20} className="text-gray-400" />
                </div>
              )}

              {/* Isim */}
              <span
                className={`text-xs font-medium truncate w-full ${
                  svc.blocked ? "text-gray-500 line-through" : "text-white"
                }`}
              >
                {svc.name}
              </span>

              {/* Toggle */}
              <button
                onClick={() => handleToggle(svc.service_id, svc.blocked)}
                disabled={togglingService === svc.service_id}
                className={`relative w-12 h-6 rounded-full transition-all duration-300 ${
                  svc.blocked
                    ? "bg-neon-red/30 border border-neon-red/40"
                    : "bg-neon-green/30 border border-neon-green/40"
                } ${togglingService === svc.service_id ? "opacity-50" : ""}`}
              >
                <div
                  className={`absolute top-0.5 w-5 h-5 rounded-full transition-all duration-300 ${
                    svc.blocked
                      ? "left-0.5 bg-neon-red shadow-[0_0_8px_rgba(239,68,68,0.5)]"
                      : "left-[1.625rem] bg-neon-green shadow-[0_0_8px_rgba(57,255,20,0.5)]"
                  }`}
                />
              </button>

              {/* Durum */}
              <span
                className={`text-[10px] ${
                  svc.blocked ? "text-neon-red" : "text-gray-500"
                }`}
              >
                {svc.blocked ? "ENGELLI" : "ACIK"}
              </span>
            </div>
          </GlassCard>
        ))}
      </div>

      {filteredServices.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          Eşleşen servis bulunamadı.
        </div>
      )}
    </div>
  );
}
