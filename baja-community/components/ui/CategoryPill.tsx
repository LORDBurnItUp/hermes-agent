"use client";

import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

interface CategoryPillProps {
  category: string;
  active?: boolean;
  onClick?: () => void;
  size?: "sm" | "md";
}

export function CategoryPill({
  category,
  active = false,
  onClick,
  size = "sm",
}: CategoryPillProps) {
  const { lang } = useLanguage();
  const l = labels[lang];
  const label = l[category] || category;

  const sizeClasses = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm";

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center rounded-full font-medium transition-all ${sizeClasses} ${
        active
          ? "bg-[var(--color-accent-sunset)] text-white"
          : "bg-[var(--color-glass-bg)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)]"
      }`}
    >
      {label}
    </button>
  );
}
