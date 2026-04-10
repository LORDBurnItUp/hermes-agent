"use client";

import { Users } from "lucide-react";
import { getCommunityServices } from "@/lib/data";
import { CommunityServiceCard } from "@/components/ui/CommunityServiceCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function CommunityPage() {
  const services = getCommunityServices();
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <ScrollReveal>
        <div className="flex items-center gap-3 mb-2">
          <Users className="h-8 w-8 text-[var(--color-accent-twilight)]" />
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            {l.community}
          </h1>
        </div>
        <p className="text-[var(--color-text-secondary)] mb-8 max-w-2xl">
          {lang === "es"
            ? "Proyectos activos de servicio comunitario. Reparacion de infraestructura, distribucion de medicina, colectas de alimentos y mas."
            : "Active community service projects. Infrastructure repair, medicine distribution, food drives, and more."}
        </p>
      </ScrollReveal>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map((service, i) => (
          <ScrollReveal key={service.id} delay={i * 0.05}>
            <CommunityServiceCard service={service} />
          </ScrollReveal>
        ))}
      </div>
    </div>
  );
}
