"use client";

import { ExternalLink, FileText, Lightbulb } from "lucide-react";
import type { ResourceStep } from "@/lib/types";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";

interface StepGuideProps {
  steps: ResourceStep[];
}

export function StepGuide({ steps }: StepGuideProps) {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="space-y-6">
      {steps.map((step) => (
        <div key={step.order} className="relative pl-10">
          <div className="absolute left-0 top-0 flex h-7 w-7 items-center justify-center rounded-full gradient-sunset text-sm font-bold text-white">
            {step.order}
          </div>
          {step.order < steps.length && (
            <div className="absolute left-3.5 top-8 bottom-0 w-px bg-[var(--color-glass-border)]" />
          )}

          <div className="glass-card rounded-xl p-5">
            <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-2">
              {t(step.title, step.titleEs, lang)}
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-3">
              {t(step.description, step.descriptionEs, lang)}
            </p>

            {step.documents && step.documents.length > 0 && (
              <div className="mb-3">
                <p className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
                  <FileText className="h-3.5 w-3.5" />
                  {l.requiredDocs}:
                </p>
                <ul className="space-y-1">
                  {step.documents.map((doc, i) => (
                    <li
                      key={i}
                      className="text-sm text-[var(--color-text-secondary)] pl-4 relative before:content-[''] before:absolute before:left-1 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-[var(--color-accent-ocean)]"
                    >
                      {doc}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {step.links && step.links.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {step.links.map((link, i) => (
                  <a
                    key={i}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-[var(--color-accent-ocean)]/10 text-[var(--color-accent-ocean)] hover:bg-[var(--color-accent-ocean)]/20 transition-colors"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {link.label}
                  </a>
                ))}
              </div>
            )}

            {step.tips && (
              <div className="flex items-start gap-2 rounded-lg bg-[var(--color-accent-gold)]/10 p-3">
                <Lightbulb className="h-4 w-4 text-[var(--color-accent-gold)] shrink-0 mt-0.5" />
                <p className="text-xs text-[var(--color-accent-gold)]">
                  {step.tips}
                </p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
