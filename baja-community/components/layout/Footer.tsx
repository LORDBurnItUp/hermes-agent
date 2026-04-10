"use client";

import { Heart, Zap } from "lucide-react";
import { useLanguage } from "@/hooks/useLanguage";

export function Footer() {
  const { lang } = useLanguage();

  return (
    <footer className="border-t border-[var(--color-glass-border)] bg-[var(--color-bg-secondary)]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[var(--color-accent-sunset)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              Hermes Community
            </span>
          </div>
          <p className="flex items-center gap-1 text-sm text-[var(--color-text-muted)]">
            {lang === "es"
              ? "Hecho con"
              : "Made with"}
            <Heart className="h-4 w-4 text-[var(--color-accent-warm)] fill-current" />
            {lang === "es"
              ? "para Mexico"
              : "for Mexico"}
          </p>
          <p className="text-xs text-[var(--color-text-muted)]">
            {lang === "es"
              ? "Plataforma comunitaria gratuita. Siempre libre, siempre abierta."
              : "Free community platform. Always free, always open."}
          </p>
        </div>
      </div>
    </footer>
  );
}
