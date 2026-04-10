"use client";

import Link from "next/link";
import { FileText, ArrowRight } from "lucide-react";
import type { Resource } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";

interface ResourceCardProps {
  resource: Resource;
}

export function ResourceCard({ resource }: ResourceCardProps) {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <Link href={`/resources/${resource.category}`}>
      <div className="glass-card rounded-2xl p-6 h-full flex flex-col group">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-accent-sunset)]/10">
            <FileText className="h-5 w-5 text-[var(--color-accent-sunset)]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
              {t(resource.title, resource.titleEs, lang)}
            </h3>
            <span className="text-xs text-[var(--color-accent-ocean)]">
              {l[resource.category] || resource.category}
            </span>
          </div>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-2 flex-1">
          {t(resource.description, resource.descriptionEs, lang)}
        </p>
        <div className="flex items-center justify-between mt-auto">
          <span className="text-xs text-[var(--color-text-muted)]">
            {resource.steps.length} {l.steps.toLowerCase()}
          </span>
          <span className="flex items-center gap-1 text-sm font-medium text-[var(--color-accent-sunset)] group-hover:gap-2 transition-all">
            {l.getStarted}
            <ArrowRight className="h-4 w-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}
