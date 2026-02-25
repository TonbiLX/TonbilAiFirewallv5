// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Profil detay karti

import { Users, Clock, Shield, Gauge } from "lucide-react";
import { GlassCard } from "../common/GlassCard";
import { NeonBadge } from "../common/NeonBadge";
import type { Profile } from "../../types";

interface ProfileCardProps {
  profile: Profile;
}

const typeVariant = {
  child: "amber" as const,
  adult: "cyan" as const,
  guest: "magenta" as const,
};

const typeLabel = {
  child: "Çocuk",
  adult: "Yetişkin",
  guest: "Misafir",
};

export function ProfileCard({ profile }: ProfileCardProps) {
  return (
    <GlassCard hoverable neonColor={typeVariant[profile.profile_type]}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <Users size={24} className="text-neon-cyan" />
          <h3 className="font-semibold text-lg">{profile.name}</h3>
        </div>
        <NeonBadge
          label={typeLabel[profile.profile_type]}
          variant={typeVariant[profile.profile_type]}
        />
      </div>

      <div className="space-y-2 text-sm text-gray-400">
        {profile.allowed_hours && (
          <div className="flex items-center gap-2">
            <Clock size={14} />
            <span>
              {profile.allowed_hours.start} - {profile.allowed_hours.end}
            </span>
          </div>
        )}
        {profile.content_filters && profile.content_filters.length > 0 && (
          <div className="flex items-center gap-2">
            <Shield size={14} />
            <span>{profile.content_filters.join(", ")}</span>
          </div>
        )}
        {profile.bandwidth_limit_mbps && (
          <div className="flex items-center gap-2">
            <Gauge size={14} />
            <span>{profile.bandwidth_limit_mbps} Mbps limit</span>
          </div>
        )}
      </div>
    </GlassCard>
  );
}
