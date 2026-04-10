"use client";

import { Zap } from "lucide-react";
import { ParticleBackground } from "@/components/effects/ParticleBackground";
import { GlowEffect } from "@/components/effects/GlowEffect";
import { SearchBar } from "@/components/ui/SearchBar";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export function HeroSection() {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      <ParticleBackground />
      <GlowEffect
        color="sunset"
        className="-top-40 -right-40 w-96 h-96"
      />
      <GlowEffect
        color="ocean"
        className="-bottom-40 -left-40 w-96 h-96"
      />

      <div className="relative mx-auto max-w-4xl px-4 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-[var(--color-glass-bg)] border border-[var(--color-glass-border)] px-4 py-1.5">
          <Zap className="h-4 w-4 text-[var(--color-accent-sunset)]" />
          <span className="text-sm text-[var(--color-text-secondary)]">
            {lang === "es"
              ? "Impulsado por Hermes AI"
              : "Powered by Hermes AI"}
          </span>
        </div>

        <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-6xl">
          <span className="gradient-text-sunset">{l.tagline}</span>
        </h1>

        <p className="mb-10 text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto leading-relaxed">
          {l.heroSubtitle}
        </p>

        <div className="flex justify-center">
          <SearchBar />
        </div>
      </div>
    </section>
  );
}
