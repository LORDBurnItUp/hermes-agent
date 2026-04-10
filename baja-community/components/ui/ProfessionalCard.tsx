"use client";

import { MapPin, Phone, Mail, MessageCircle, CheckCircle } from "lucide-react";
import type { Professional } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { CategoryPill } from "./CategoryPill";

interface ProfessionalCardProps {
  professional: Professional;
}

export function ProfessionalCard({ professional }: ProfessionalCardProps) {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="glass-card rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
            {professional.name}
          </h3>
          <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)]">
            <MapPin className="h-3.5 w-3.5" />
            {professional.location.city}, {professional.location.state}
          </div>
        </div>
        {professional.verified && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent-green)]/20 text-[var(--color-accent-green)]">
            <CheckCircle className="h-3 w-3" />
            {l.verified}
          </span>
        )}
      </div>

      <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-2 flex-1">
        {t(professional.description, professional.descriptionEs, lang)}
      </p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <CategoryPill category={professional.category} />
        {professional.specialties.slice(0, 2).map((s) => (
          <span
            key={s}
            className="px-2 py-0.5 rounded-full text-xs bg-[var(--color-glass-bg)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)]"
          >
            {s}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap gap-1 mb-4">
        {professional.languages.map((lang) => (
          <span
            key={lang}
            className="px-2 py-0.5 rounded-full text-xs bg-[var(--color-accent-ocean)]/10 text-[var(--color-accent-ocean)]"
          >
            {lang}
          </span>
        ))}
      </div>

      <div className="mt-auto pt-4 border-t border-[var(--color-glass-border)] flex flex-wrap gap-3">
        {professional.contactInfo.phone && (
          <a
            href={`tel:${professional.contactInfo.phone}`}
            className="flex items-center gap-1 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent-sunset)] transition-colors"
          >
            <Phone className="h-3.5 w-3.5" />
            {professional.contactInfo.phone}
          </a>
        )}
        {professional.contactInfo.email && (
          <a
            href={`mailto:${professional.contactInfo.email}`}
            className="flex items-center gap-1 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent-sunset)] transition-colors"
          >
            <Mail className="h-3.5 w-3.5" />
            Email
          </a>
        )}
        {professional.contactInfo.whatsapp && (
          <a
            href={`https://wa.me/${professional.contactInfo.whatsapp.replace(/[^0-9]/g, "")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-[var(--color-accent-green)] hover:text-[var(--color-accent-green)]/80 transition-colors"
          >
            <MessageCircle className="h-3.5 w-3.5" />
            WhatsApp
          </a>
        )}
      </div>
    </div>
  );
}
