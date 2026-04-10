"use client";

import { type ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: "sunset" | "ocean" | "twilight";
  onClick?: () => void;
}

export function GlassCard({
  children,
  className = "",
  hover = true,
  glow,
  onClick,
}: GlassCardProps) {
  const glowClass = glow ? `glow-${glow}` : "";
  const hoverClass = hover ? "glass-card" : "glass";
  const cursorClass = onClick ? "cursor-pointer" : "";

  return (
    <div
      onClick={onClick}
      className={`${hoverClass} ${glowClass} ${cursorClass} rounded-2xl p-6 ${className}`}
    >
      {children}
    </div>
  );
}
