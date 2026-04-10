"use client";

import { BookOpen } from "lucide-react";
import { getResources } from "@/lib/data";
import { ResourceCard } from "@/components/ui/ResourceCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function ResourcesPage() {
  const resources = getResources();
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <ScrollReveal>
        <div className="flex items-center gap-3 mb-2">
          <BookOpen className="h-8 w-8 text-[var(--color-accent-sunset)]" />
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            {l.resources}
          </h1>
        </div>
        <p className="text-[var(--color-text-secondary)] mb-8 max-w-2xl">
          {lang === "es"
            ? "Guias paso a paso para tramites, pasaportes, INE, CURP, RFC y mas. Todo lo que necesitas para navegar procesos gubernamentales en Mexico."
            : "Step-by-step guides for government procedures, passports, INE, CURP, RFC, and more. Everything you need to navigate government processes in Mexico."}
        </p>
      </ScrollReveal>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {resources.map((resource, i) => (
          <ScrollReveal key={resource.id} delay={i * 0.05}>
            <ResourceCard resource={resource} />
          </ScrollReveal>
        ))}
      </div>
    </div>
  );
}
