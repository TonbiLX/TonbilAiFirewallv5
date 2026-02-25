// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Statik IP ataması formu

import { useState } from "react";
import { Plus } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { createStaticLease } from "../../services/dhcpApi";

interface StaticLeaseFormProps {
  onCreated: () => void;
}

export function StaticLeaseForm({ onCreated }: StaticLeaseFormProps) {
  const [mac, setMac] = useState("");
  const [ip, setIp] = useState("");
  const [hostname, setHostname] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mac || !ip) return;
    setSubmitting(true);
    try {
      await createStaticLease({ mac_address: mac, ip_address: ip, hostname: hostname || undefined });
      setMac("");
      setIp("");
      setHostname("");
      onCreated();
    } catch (err) {
      console.error("Statik lease oluşturulamadi:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <GlassCard>
      <h4 className="text-sm font-semibold text-gray-300 mb-3">
        Statik IP Ataması Ekle
      </h4>
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
        <input
          type="text"
          value={mac}
          onChange={(e) => setMac(e.target.value)}
          placeholder="MAC (AA:BB:CC:DD:EE:FF)"
          className="flex-1 min-w-[180px] bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
        />
        <input
          type="text"
          value={ip}
          onChange={(e) => setIp(e.target.value)}
          placeholder="IP (192.168.1.x)"
          className="flex-1 min-w-[140px] bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
        />
        <input
          type="text"
          value={hostname}
          onChange={(e) => setHostname(e.target.value)}
          placeholder="Hostname (opsiyonel)"
          className="flex-1 min-w-[140px] bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan/50"
        />
        <button
          type="submit"
          disabled={submitting || !mac || !ip}
          className="px-4 py-2 bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/20 rounded-lg text-sm hover:bg-neon-magenta/20 transition-colors disabled:opacity-50 flex items-center gap-1"
        >
          <Plus size={16} />
          Ekle
        </button>
      </form>
    </GlassCard>
  );
}
