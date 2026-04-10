"use client";

import { use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  MapPin,
  Phone,
  Mail,
  Globe,
  Heart,
  MessageCircle,
} from "lucide-react";
import { getCharityById } from "@/lib/data";
import { useLanguage } from "@/hooks/useLanguage";
import { labels, t } from "@/lib/i18n";
import { CategoryPill } from "@/components/ui/CategoryPill";
import { GlassCard } from "@/components/ui/GlassCard";

export default function CharityDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const charity = getCharityById(slug);
  const { lang } = useLanguage();
  const l = labels[lang];

  if (!charity) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <p className="text-[var(--color-text-muted)]">{l.noResults}</p>
        <Link
          href="/charity"
          className="inline-flex items-center gap-1 mt-4 text-[var(--color-accent-sunset)]"
        >
          <ArrowLeft className="h-4 w-4" /> {l.backToAll}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-12">
      <Link
        href="/charity"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-accent-sunset)] transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" /> {l.backToAll}
      </Link>

      <div className="flex items-center gap-2 mb-2">
        {charity.featured && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent-sunset)]/20 text-[var(--color-accent-sunset)]">
            <Heart className="h-3 w-3 fill-current" />
            {l.featured}
          </span>
        )}
        <CategoryPill category={charity.category} />
      </div>

      <h1 className="text-3xl font-bold text-[var(--color-text-primary)] mb-2">
        {t(charity.name, charity.nameEs, lang)}
      </h1>

      <div className="flex items-center gap-1 text-[var(--color-text-muted)] mb-6">
        <MapPin className="h-4 w-4" />
        {charity.location.city}, {charity.location.state}
        {charity.location.address && ` — ${charity.location.address}`}
      </div>

      <p className="text-[var(--color-text-secondary)] text-lg mb-8 leading-relaxed">
        {t(charity.description, charity.descriptionEs, lang)}
      </p>

      {charity.needs.length > 0 && (
        <GlassCard className="mb-6">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
            {l.needsHelp}
          </h2>
          <div className="flex flex-wrap gap-2">
            {charity.needs.map((need) => (
              <span
                key={need}
                className="px-3 py-1 rounded-full text-sm bg-[var(--color-accent-warm)]/10 text-[var(--color-accent-warm)]"
              >
                {need}
              </span>
            ))}
          </div>
        </GlassCard>
      )}

      <GlassCard className="mb-6">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
          {l.contact}
        </h2>
        <div className="space-y-2">
          {charity.contactInfo.phone && (
            <a
              href={`tel:${charity.contactInfo.phone}`}
              className="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-sunset)] transition-colors"
            >
              <Phone className="h-4 w-4" /> {charity.contactInfo.phone}
            </a>
          )}
          {charity.contactInfo.email && (
            <a
              href={`mailto:${charity.contactInfo.email}`}
              className="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-sunset)] transition-colors"
            >
              <Mail className="h-4 w-4" /> {charity.contactInfo.email}
            </a>
          )}
          {charity.contactInfo.website && (
            <a
              href={charity.contactInfo.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-sunset)] transition-colors"
            >
              <Globe className="h-4 w-4" /> {charity.contactInfo.website}
            </a>
          )}
          {charity.contactInfo.whatsapp && (
            <a
              href={`https://wa.me/${charity.contactInfo.whatsapp.replace(/[^0-9]/g, "")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-[var(--color-accent-green)] hover:text-[var(--color-accent-green)]/80 transition-colors"
            >
              <MessageCircle className="h-4 w-4" /> WhatsApp
            </a>
          )}
        </div>
      </GlassCard>

      {charity.donationLinks.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {charity.donationLinks.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl gradient-sunset px-6 py-3 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              <Heart className="h-4 w-4" />
              {l.donate} — {link.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
