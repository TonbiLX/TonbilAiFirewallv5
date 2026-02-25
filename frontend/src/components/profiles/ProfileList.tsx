// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Profil listesi bileseni

import { ProfileCard } from "./ProfileCard";
import { LoadingSpinner } from "../common/LoadingSpinner";
import type { Profile } from "../../types";

interface ProfileListProps {
  profiles: Profile[];
  loading: boolean;
}

export function ProfileList({ profiles, loading }: ProfileListProps) {
  if (loading) return <LoadingSpinner />;

  if (profiles.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        Kayıtlı profil bulunamadı.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {profiles.map((profile) => (
        <ProfileCard key={profile.id} profile={profile} />
      ))}
    </div>
  );
}
