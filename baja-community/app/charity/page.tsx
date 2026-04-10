"use client";

import { useState } from "react";
import { Heart } from "lucide-react";
import { getCharities } from "@/lib/data";
import { CHARITY_CATEGORIES } from "@/lib/constants";
import { CharityCard } from "@/components/ui/CharityCard";
import { CategoryPill } from "@/components/ui/CategoryPill";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";

export default function CharityPage() {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedCity, setSelectedCity] = useState("all");
  const { lang } = useLanguage();
  const l = labels[lang];

  const allCharities = getCharities();
  const cities = [...new Set(allCharities.map((c) => c.location.city))].sort();

  const filtered = allCharities.filter((c) => {
    if (selectedCategory !== "all" && c.category !== selectedCategory) return false;
    if (selectedCity !== "all" && c.location.city !== selectedCity) return false;
    return true;
  });

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
      <ScrollReveal>
        <div className="flex items-center gap-3 mb-2">
          <Heart className="h-8 w-8 text-[var(--color-accent-warm)]" />
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            {l.charities}
          </h1>
        </div>
        <p className="text-[var(--color-text-secondary)] mb-8 max-w-2xl">
          {lang === "es"
            ? "Apoya organizaciones que hacen la diferencia en comunidades de todo Mexico."
            : "Support organizations making a difference in communities across Mexico."}
        </p>
      </ScrollReveal>

      <div className="flex flex-wrap gap-2 mb-4">
        <CategoryPill
          category={l.allCategories}
          active={selectedCategory === "all"}
          onClick={() => setSelectedCategory("all")}
          size="md"
        />
        {CHARITY_CATEGORIES.map((cat) => (
          <CategoryPill
            key={cat}
            category={cat}
            active={selectedCategory === cat}
            onClick={() => setSelectedCategory(cat)}
            size="md"
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => setSelectedCity("all")}
          className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
            selectedCity === "all"
              ? "bg-[var(--color-accent-ocean)] text-white"
              : "bg-[var(--color-glass-bg)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)] hover:bg-[var(--color-glass-hover)]"
          }`}
        >
          {l.allCities}
        </button>
        {cities.map((city) => (
          <button
            key={city}
            onClick={() => setSelectedCity(city)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
              selectedCity === city
                ? "bg-[var(--color-accent-ocean)] text-white"
                : "bg-[var(--color-glass-bg)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)] hover:bg-[var(--color-glass-hover)]"
            }`}
          >
            {city}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-[var(--color-text-muted)]">{l.noResults}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((charity, i) => (
            <ScrollReveal key={charity.id} delay={i * 0.05}>
              <CharityCard charity={charity} />
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  );
}
