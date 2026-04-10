"use client";

import { CalendarHeart } from "lucide-react";
import { getEvents } from "@/lib/data";
import { EventCard } from "@/components/ui/EventCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function EventsPage() {
  const events = getEvents().sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <ScrollReveal>
        <div className="flex items-center gap-3 mb-2">
          <CalendarHeart className="h-8 w-8 text-[var(--color-accent-green)]" />
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            {l.events}
          </h1>
        </div>
        <p className="text-[var(--color-text-secondary)] mb-8 max-w-2xl">
          {lang === "es"
            ? "Proximos eventos comunitarios. Recaudaciones, dias de voluntariado, jornadas medicas y mas."
            : "Upcoming community events. Fundraisers, volunteer days, medical days, and more."}
        </p>
      </ScrollReveal>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {events.map((event, i) => (
          <ScrollReveal key={event.id} delay={i * 0.05}>
            <EventCard event={event} />
          </ScrollReveal>
        ))}
      </div>
    </div>
  );
}
