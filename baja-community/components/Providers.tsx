"use client";

import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { LanguageContext } from "@/hooks/useLanguage";
import type { Language } from "@/lib/types";

export function Providers({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>("en");

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <LanguageContext.Provider value={{ lang, setLang }}>
        {children}
      </LanguageContext.Provider>
    </ThemeProvider>
  );
}
