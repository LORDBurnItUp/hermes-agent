"use client";

import Link from "next/link";
import { MapPin, Heart, ExternalLink } from "lucide-react";
import type { Charity } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { CategoryPill } from "./CategoryPill";

interface CharityCardProps {
  charity: Charity;
}

export function CharityCard({ charity }: CharityCardProps) {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <Link href={`/charity/${charity.id}`}>
      <div className="glass-card rounded-2xl p-6 h-full flex flex-col">
        {charity.featured && (
          <span className="inline-flex items-center gap-1 self-start px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent-sunset)]/20 text-[var(--color-accent-sunset)] mb-3">
            <Heart className="h-3 w-3" />
            {l.featured}
          </span>
        )}
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
          {t(charity.name, charity.nameEs, lang)}
        </h3>
        <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)] mb-3">
          <MapPin className="h-3.5 w-3.5" />
          {charity.location.city}, {charity.location.state}
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-3 flex-1">
          {t(charity.description, charity.descriptionEs, lang)}
        </p>
        <div className="flex flex-wrap gap-1.5 mb-4">
          <CategoryPill category={charity.category} />
        </div>
        {charity.needs.length > 0 && (
          <div className="mt-auto">
            <p className="text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
              {l.needsHelp}:
            </p>
            <div className="flex flex-wrap gap-1">
              {charity.needs.slice(0, 3).map((need) => (
                <span
                  key={need}
                  className="px-2 py-0.5 rounded-full text-xs bg-[var(--color-accent-warm)]/10 text-[var(--color-accent-warm)]"
                >
                  {need}
                </span>
              ))}
              {charity.needs.length > 3 && (
                <span className="px-2 py-0.5 rounded-full text-xs text-[var(--color-text-muted)]">
                  +{charity.needs.length - 3}
                </span>
              )}
            </div>
          </div>
        )}
        {charity.donationLinks.length > 0 && (
          <div className="mt-4 pt-4 border-t border-[var(--color-glass-border)]">
            <span className="inline-flex items-center gap-1 text-sm font-medium text-[var(--color-accent-sunset)] hover:text-[var(--color-accent-sunset)]/80">
              {l.donate} <ExternalLink className="h-3.5 w-3.5" />
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}
