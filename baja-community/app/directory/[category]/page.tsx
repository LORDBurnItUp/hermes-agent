"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getProfessionalsByCategory } from "@/lib/data";
import { ProfessionalCard } from "@/components/ui/ProfessionalCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function DirectoryCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = use(params);
  const professionals = getProfessionalsByCategory(category);
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <Link
        href="/directory"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-accent-sunset)] transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" /> {l.backToAll}
      </Link>

      <h1 className="text-3xl font-bold text-[var(--color-text-primary)] mb-8 capitalize">
        {l[category] || category}
      </h1>

      {professionals.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-[var(--color-text-muted)]">{l.noResults}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {professionals.map((pro, i) => (
            <ScrollReveal key={pro.id} delay={i * 0.05}>
              <ProfessionalCard professional={pro} />
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  );
}
