// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Neon isikli durum rözeti

import clsx from "clsx";

interface NeonBadgeProps {
  label: string;
  variant?: "cyan" | "magenta" | "green" | "amber" | "red";
  pulse?: boolean;
}

export function NeonBadge({
  label,
  variant = "cyan",
  pulse = false,
}: NeonBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        variant === "cyan" &&
          "bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30",
        variant === "magenta" &&
          "bg-neon-magenta/10 text-neon-magenta border-neon-magenta/30",
        variant === "green" &&
          "bg-neon-green/10 text-neon-green border-neon-green/30",
        variant === "amber" &&
          "bg-neon-amber/10 text-neon-amber border-neon-amber/30",
        variant === "red" &&
          "bg-neon-red/10 text-neon-red border-neon-red/30",
        pulse && "animate-pulse-neon"
      )}
    >
      {label}
    </span>
  );
}
