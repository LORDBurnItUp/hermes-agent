"use client";

import { createContext, useContext } from "react";
import type { Language } from "@/lib/types";

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
}

export const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
});

export function useLanguage() {
  return useContext(LanguageContext);
}
