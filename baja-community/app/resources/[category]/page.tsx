"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getResourcesByCategory } from "@/lib/data";
import { StepGuide } from "@/components/ui/StepGuide";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";

export default function ResourceCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = use(params);
  const resources = getResourcesByCategory(category);
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-12">
      <Link
        href="/resources"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-accent-sunset)] transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" /> {l.backToAll}
      </Link>

      <h1 className="text-3xl font-bold text-[var(--color-text-primary)] mb-8 capitalize">
        {l[category] || category}
      </h1>

      {resources.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-[var(--color-text-muted)]">{l.noResults}</p>
        </div>
      ) : (
        <div className="space-y-12">
          {resources.map((resource) => (
            <ScrollReveal key={resource.id}>
              <div>
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
                  {t(resource.title, resource.titleEs, lang)}
                </h2>
                <p className="text-[var(--color-text-secondary)] mb-6">
                  {t(resource.description, resource.descriptionEs, lang)}
                </p>
                <StepGuide steps={resource.steps} />

                {resource.externalLinks.length > 0 && (
                  <div className="mt-6 flex flex-wrap gap-2">
                    {resource.externalLinks.map((link, i) => (
                      <a
                        key={i}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-4 py-2 rounded-xl text-sm font-medium bg-[var(--color-accent-ocean)]/10 text-[var(--color-accent-ocean)] hover:bg-[var(--color-accent-ocean)]/20 transition-colors"
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  );
}
