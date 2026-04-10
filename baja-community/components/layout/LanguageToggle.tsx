"use client";

import { useLanguage } from "@/hooks/useLanguage";
import { Globe } from "lucide-react";

export function LanguageToggle() {
  const { lang, setLang } = useLanguage();

  return (
    <button
      onClick={() => setLang(lang === "en" ? "es" : "en")}
      className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-colors"
      aria-label="Toggle language"
    >
      <Globe className="h-3.5 w-3.5" />
      <span>{lang === "en" ? "ES" : "EN"}</span>
    </button>
  );
}
