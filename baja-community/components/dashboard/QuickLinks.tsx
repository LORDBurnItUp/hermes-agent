"use client";

import Link from "next/link";
import {
  Heart,
  Briefcase,
  BookOpen,
  Users,
  CalendarHeart,
  ArrowRight,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

const links = [
  {
    href: "/charity",
    labelKey: "charities",
    icon: Heart,
    color: "var(--color-accent-warm)",
    descEn: "Support orphanages, shelters, and food banks across Mexico",
    descEs: "Apoya orfanatos, albergues y bancos de alimentos en Mexico",
  },
  {
    href: "/directory",
    labelKey: "directory",
    icon: Briefcase,
    color: "var(--color-accent-ocean)",
    descEn: "Find verified lawyers, doctors, accountants, and more",
    descEs: "Encuentra abogados, doctores, contadores verificados y mas",
  },
  {
    href: "/resources",
    labelKey: "resources",
    icon: BookOpen,
    color: "var(--color-accent-sunset)",
    descEn: "Step-by-step guides for passports, INE, CURP, RFC, and more",
    descEs: "Guias paso a paso para pasaportes, INE, CURP, RFC y mas",
  },
  {
    href: "/community",
    labelKey: "community",
    icon: Users,
    color: "var(--color-accent-twilight)",
    descEn: "Join community projects — road repairs, cleanups, food drives",
    descEs: "Unete a proyectos comunitarios — bacheo, limpieza, colectas",
  },
  {
    href: "/events",
    labelKey: "events",
    icon: CalendarHeart,
    color: "var(--color-accent-green)",
    descEn: "Upcoming fundraisers, volunteer days, and community events",
    descEs: "Proximas recaudaciones, dias de voluntariado y eventos comunitarios",
  },
];

export function QuickLinks() {
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {links.map((link, i) => (
        <ScrollReveal key={link.href} delay={i * 0.1}>
          <Link href={link.href} className="block h-full">
            <GlassCard className="h-full group">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-xl mb-4"
                style={{ backgroundColor: `color-mix(in srgb, ${link.color} 15%, transparent)` }}
              >
                <link.icon
                  className="h-5 w-5"
                  style={{ color: link.color }}
                />
              </div>
              <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-1">
                {l[link.labelKey]}
              </h3>
              <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                {lang === "es" ? link.descEs : link.descEn}
              </p>
              <span className="inline-flex items-center gap-1 text-sm font-medium text-[var(--color-accent-sunset)] group-hover:gap-2 transition-all mt-auto">
                {l.viewAll} <ArrowRight className="h-4 w-4" />
              </span>
            </GlassCard>
          </Link>
        </ScrollReveal>
      ))}
    </div>
  );
}
