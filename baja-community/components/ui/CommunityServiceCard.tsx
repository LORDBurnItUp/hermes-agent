"use client";

import { MapPin, Clock, Users } from "lucide-react";
import type { CommunityService } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { CategoryPill } from "./CategoryPill";

interface CommunityServiceCardProps {
  service: CommunityService;
}

export function CommunityServiceCard({ service }: CommunityServiceCardProps) {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="glass-card rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
          {t(service.title, service.titleEs, lang)}
        </h3>
        {service.volunteerNeeded && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent-twilight)]/20 text-[var(--color-accent-twilight)]">
            <Users className="h-3 w-3" />
            {l.volunteerNeeded}
          </span>
        )}
      </div>

      <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)] mb-2">
        <MapPin className="h-3.5 w-3.5" />
        {service.location.city}, {service.location.state}
      </div>

      {service.schedule && (
        <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)] mb-3">
          <Clock className="h-3.5 w-3.5" />
          {service.schedule}
        </div>
      )}

      <p className="text-sm text-[var(--color-text-secondary)] mb-4 flex-1">
        {t(service.description, service.descriptionEs, lang)}
      </p>

      <div className="flex items-center justify-between mt-auto">
        <CategoryPill category={service.category} />
        <span className="text-xs text-[var(--color-text-muted)]">
          {service.organizerName}
        </span>
      </div>
    </div>
  );
}
