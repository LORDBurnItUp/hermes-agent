"use client";

interface GlowEffectProps {
  color?: "sunset" | "ocean" | "twilight";
  className?: string;
}

export function GlowEffect({ color = "sunset", className = "" }: GlowEffectProps) {
  const gradients: Record<string, string> = {
    sunset: "from-[#f97316]/20 via-[#ef4444]/10 to-[#a855f7]/20",
    ocean: "from-[#06b6d4]/20 via-[#3b82f6]/10 to-[#a855f7]/20",
    twilight: "from-[#a855f7]/20 via-[#3b82f6]/10 to-[#06b6d4]/20",
  };

  return (
    <div
      className={`absolute rounded-full bg-gradient-to-r ${gradients[color]} blur-3xl animate-pulse-glow pointer-events-none ${className}`}
      aria-hidden="true"
    />
  );
}
