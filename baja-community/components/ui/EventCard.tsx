"use client";

import { Calendar, MapPin, ExternalLink } from "lucide-react";
import type { CommunityEvent } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { CategoryPill } from "./CategoryPill";

interface EventCardProps {
  event: CommunityEvent;
}

export function EventCard({ event }: EventCardProps) {
  const { lang } = useLanguage();
  const l = labels[lang];
  const date = new Date(event.date);
  const month = date.toLocaleString(lang === "es" ? "es-MX" : "en-US", {
    month: "short",
  });
  const day = date.getDate();

  return (
    <div className="glass-card rounded-2xl p-6 h-full flex flex-col">
      <div className="flex gap-4">
        <div className="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-[var(--color-accent-sunset)]/10 shrink-0">
          <span className="text-xs font-medium text-[var(--color-accent-sunset)] uppercase">
            {month}
          </span>
          <span className="text-xl font-bold text-[var(--color-text-primary)]">
            {day}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-1">
            {t(event.title, event.titleEs, lang)}
          </h3>
          <div className="flex items-center gap-1 text-sm text-[var(--color-text-muted)]">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">
              {event.location.name}, {event.location.city}
            </span>
          </div>
        </div>
      </div>

      <p className="text-sm text-[var(--color-text-secondary)] mt-3 mb-4 line-clamp-2 flex-1">
        {t(event.description, event.descriptionEs, lang)}
      </p>

      <div className="flex items-center justify-between mt-auto">
        <CategoryPill category={event.type} />
        <div className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
          <Calendar className="h-3.5 w-3.5" />
          {date.toLocaleDateString(lang === "es" ? "es-MX" : "en-US", {
            weekday: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      {event.registrationUrl && (
        <a
          href={event.registrationUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 flex items-center justify-center gap-1 rounded-lg bg-[var(--color-accent-sunset)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-sunset)]/90 transition-colors"
        >
          {l.getStarted} <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}
    </div>
  );
}
