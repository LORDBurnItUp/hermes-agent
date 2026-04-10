"use client";

import Link from "next/link";
import { Heart, MapPin, ArrowRight } from "lucide-react";
import { getFeaturedCharity } from "@/lib/data";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { GlassCard } from "@/components/ui/GlassCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";

export function FeaturedCharity() {
  const charity = getFeaturedCharity();
  const { lang } = useLanguage();
  const l = labels[lang];

  if (!charity) return null;

  return (
    <ScrollReveal>
      <GlassCard glow="sunset" className="relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-[var(--color-accent-sunset)]/10 to-transparent rounded-bl-full pointer-events-none" />

        <div className="relative">
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-[var(--color-accent-sunset)]/20 text-[var(--color-accent-sunset)] mb-4">
            <Heart className="h-3 w-3 fill-current" />
            {l.featured}
          </span>

          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
            {t(charity.name, charity.nameEs, lang)}
          </h2>

          <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)] mb-4">
            <MapPin className="h-4 w-4" />
            {charity.location.city}, {charity.location.state}
          </div>

          <p className="text-[var(--color-text-secondary)] mb-6 max-w-2xl">
            {t(charity.description, charity.descriptionEs, lang)}
          </p>

          {charity.needs.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-medium text-[var(--color-text-muted)] mb-2">
                {l.needsHelp}:
              </p>
              <div className="flex flex-wrap gap-2">
                {charity.needs.map((need) => (
                  <span
                    key={need}
                    className="px-3 py-1 rounded-full text-sm bg-[var(--color-accent-warm)]/10 text-[var(--color-accent-warm)]"
                  >
                    {need}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            {charity.donationLinks.map((link) => (
              <a
                key={link.url}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl gradient-sunset px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 transition-opacity"
              >
                <Heart className="h-4 w-4" />
                {l.donate} — {link.label}
              </a>
            ))}
            <Link
              href={`/charity/${charity.id}`}
              className="inline-flex items-center gap-1 rounded-xl border border-[var(--color-glass-border)] px-5 py-2.5 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-colors"
            >
              {l.learnMore} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </GlassCard>
    </ScrollReveal>
  );
}
