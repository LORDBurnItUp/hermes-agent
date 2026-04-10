"use client";

import { useState } from "react";
import { Briefcase } from "lucide-react";
import { getProfessionals } from "@/lib/data";
import { PROFESSIONAL_CATEGORIES } from "@/lib/constants";
import { ProfessionalCard } from "@/components/ui/ProfessionalCard";
import { CategoryPill } from "@/components/ui/CategoryPill";
import { SearchBar } from "@/components/ui/SearchBar";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function DirectoryPage() {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const { lang } = useLanguage();
  const l = labels[lang];

  const allProfessionals = getProfessionals();
  const filtered =
    selectedCategory === "all"
      ? allProfessionals
      : allProfessionals.filter((p) => p.category === selectedCategory);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <ScrollReveal>
        <div className="flex items-center gap-3 mb-2">
          <Briefcase className="h-8 w-8 text-[var(--color-accent-ocean)]" />
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            {l.directory}
          </h1>
        </div>
        <p className="text-[var(--color-text-secondary)] mb-8 max-w-2xl">
          {lang === "es"
            ? "Encuentra profesionales verificados en todo Mexico. Abogados, doctores, contadores y mas."
            : "Find verified professionals across Mexico. Lawyers, doctors, accountants, and more."}
        </p>
      </ScrollReveal>

      <div className="flex flex-wrap gap-2 mb-8">
        <CategoryPill
          category={l.allCategories}
          active={selectedCategory === "all"}
          onClick={() => setSelectedCategory("all")}
          size="md"
        />
        {PROFESSIONAL_CATEGORIES.map((cat) => (
          <CategoryPill
            key={cat}
            category={cat}
            active={selectedCategory === cat}
            onClick={() => setSelectedCategory(cat)}
            size="md"
          />
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-[var(--color-text-muted)]">{l.noResults}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((pro, i) => (
            <ScrollReveal key={pro.id} delay={i * 0.05}>
              <ProfessionalCard professional={pro} />
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  );
}
