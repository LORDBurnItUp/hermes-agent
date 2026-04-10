"use client";

import { HeroSection } from "@/components/ui/HeroSection";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { FeaturedCharity } from "@/components/dashboard/FeaturedCharity";
import { QuickLinks } from "@/components/dashboard/QuickLinks";
import { InteractiveMap } from "@/components/ui/InteractiveMap";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { GlowEffect } from "@/components/effects/GlowEffect";
import { useLanguage } from "@/hooks/useLanguage";

export default function Home() {
  const { lang } = useLanguage();

  return (
    <div className="relative">
      <HeroSection />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-16 pb-24">
        <section>
          <StatsGrid />
        </section>

        <section>
          <FeaturedCharity />
        </section>

        <section className="relative">
          <GlowEffect
            color="twilight"
            className="-top-20 left-1/2 -translate-x-1/2 w-[600px] h-[200px]"
          />
          <ScrollReveal>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-6 text-center">
              {lang === "es" ? "Explora" : "Explore"}
            </h2>
          </ScrollReveal>
          <QuickLinks />
        </section>

        <section>
          <ScrollReveal>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-6 text-center">
              {lang === "es"
                ? "Mapa de la Comunidad"
                : "Community Map"}
            </h2>
          </ScrollReveal>
          <ScrollReveal delay={0.2}>
            <div className="glass-card rounded-2xl p-2 overflow-hidden">
              <InteractiveMap className="w-full h-[500px]" />
            </div>
          </ScrollReveal>
          <div className="flex justify-center gap-6 mt-4">
            {[
              { color: "#ef4444", label: lang === "es" ? "Organizaciones" : "Charities" },
              { color: "#06b6d4", label: lang === "es" ? "Profesionales" : "Professionals" },
              { color: "#a855f7", label: lang === "es" ? "Servicios" : "Services" },
            ].map((item) => (
              <div key={item.color} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-[var(--color-text-muted)]">
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
