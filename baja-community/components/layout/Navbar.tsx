"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Zap } from "lucide-react";
import { useState } from "react";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";
import { NAV_LINKS } from "@/lib/constants";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageToggle } from "./LanguageToggle";

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { lang } = useLanguage();
  const l = labels[lang];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-[var(--color-glass-border)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-sunset">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold gradient-text-sunset">
              Hermes
            </span>
            <span className="text-sm text-[var(--color-text-secondary)] hidden sm:inline">
              {l.tagline}
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "text-[var(--color-accent-sunset)] bg-[var(--color-glass-hover)]"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)]"
                  }`}
                >
                  {l[link.labelKey]}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            <LanguageToggle />
            <ThemeToggle />
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)]"
            >
              {mobileOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden glass border-t border-[var(--color-glass-border)]">
          <div className="px-4 py-3 space-y-1">
            {NAV_LINKS.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "text-[var(--color-accent-sunset)] bg-[var(--color-glass-hover)]"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {l[link.labelKey]}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
}
