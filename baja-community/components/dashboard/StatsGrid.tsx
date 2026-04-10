"use client";

import {
  Heart,
  Briefcase,
  BookOpen,
  Users,
  CalendarHeart,
  MapPin,
} from "lucide-react";
import { AnimatedCounter } from "@/components/ui/AnimatedCounter";
import { GlassCard } from "@/components/ui/GlassCard";
import { ScrollReveal } from "@/components/effects/ScrollReveal";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";
import { getSiteConfig } from "@/lib/data";

const iconMap = [
  { key: "charitiesSupported", icon: Heart, color: "text-[var(--color-accent-warm)]" },
  { key: "professionalsListed", icon: Briefcase, color: "text-[var(--color-accent-ocean)]" },
  { key: "resourcesAvailable", icon: BookOpen, color: "text-[var(--color-accent-sunset)]" },
  { key: "communityServices", icon: Users, color: "text-[var(--color-accent-twilight)]" },
  { key: "eventsHosted", icon: CalendarHeart, color: "text-[var(--color-accent-green)]" },
  { key: "statesReached", icon: MapPin, color: "text-[var(--color-accent-gold)]" },
];

export function StatsGrid() {
  const { lang } = useLanguage();
  const l = labels[lang];
  const config = getSiteConfig();

  const labelMap: Record<string, string> = {
    charitiesSupported: l.charitiesSupported,
    professionalsListed: l.professionalsListed,
    resourcesAvailable: l.resourcesAvailable,
    communityServices: l.communityServicesActive,
    eventsHosted: l.eventsHosted,
    statesReached: l.statesReached,
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {iconMap.map(({ key, icon: Icon, color }, i) => (
        <ScrollReveal key={key} delay={i * 0.1}>
          <GlassCard className="text-center">
            <Icon className={`h-6 w-6 mx-auto mb-2 ${color}`} />
            <div className="text-2xl font-bold text-[var(--color-text-primary)]">
              <AnimatedCounter
                target={config.stats[key as keyof typeof config.stats]}
                suffix="+"
              />
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              {labelMap[key]}
            </p>
          </GlassCard>
        </ScrollReveal>
      ))}
    </div>
  );
}
