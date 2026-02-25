// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cyberpunk temalı yükleme göstergesi

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-neon-cyan animate-spin" />
        <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-neon-magenta animate-spin" style={{ animationDirection: "reverse", animationDuration: "0.8s" }} />
        <div className="absolute inset-4 rounded-full bg-neon-cyan/20 animate-pulse-neon" />
      </div>
    </div>
  );
}
