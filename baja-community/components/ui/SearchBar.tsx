"use client";

import { useState, useCallback } from "react";
import { Search, X } from "lucide-react";
import { useLanguage } from "@/hooks/useLanguage";
import { labels } from "@/lib/i18n";
import { search, type SearchResult } from "@/lib/search";
import Link from "next/link";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const { lang } = useLanguage();
  const l = labels[lang];

  const handleSearch = useCallback(
    (value: string) => {
      setQuery(value);
      if (value.trim().length > 1) {
        const found = search(value);
        setResults(found.slice(0, 8));
        setIsOpen(true);
      } else {
        setResults([]);
        setIsOpen(false);
      }
    },
    []
  );

  const typeColors: Record<string, string> = {
    charity: "text-[var(--color-accent-warm)]",
    professional: "text-[var(--color-accent-ocean)]",
    resource: "text-[var(--color-accent-sunset)]",
    service: "text-[var(--color-accent-green)]",
    event: "text-[var(--color-accent-twilight)]",
  };

  return (
    <div className="relative w-full max-w-xl">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={l.searchPlaceholder}
          className="w-full rounded-xl bg-[var(--color-glass-bg)] border border-[var(--color-glass-border)] py-2.5 pl-10 pr-10 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-sunset)] focus:ring-1 focus:ring-[var(--color-accent-sunset)] transition-colors"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setResults([]);
              setIsOpen(false);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full rounded-xl glass border border-[var(--color-glass-border)] shadow-2xl overflow-hidden z-50">
          {results.map((result) => (
            <Link
              key={`${result.type}-${result.id}`}
              href={result.href}
              className="flex items-start gap-3 px-4 py-3 hover:bg-[var(--color-glass-hover)] transition-colors"
            >
              <span
                className={`text-xs font-medium uppercase ${typeColors[result.type] || ""}`}
              >
                {result.type}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                  {result.title}
                </p>
                <p className="text-xs text-[var(--color-text-muted)] truncate">
                  {result.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
