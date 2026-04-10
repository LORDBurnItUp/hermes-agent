export const SITE_NAME = "Hermes Community";
export const SITE_NAME_ES = "Comunidad Hermes";

export const CHARITY_CATEGORIES = [
  "orphanage",
  "shelter",
  "food-bank",
  "medical",
  "infrastructure",
  "education",
  "other",
] as const;

export const PROFESSIONAL_CATEGORIES = [
  "lawyer",
  "doctor",
  "accountant",
  "real-estate",
  "translator",
  "dentist",
  "notary",
  "other",
] as const;

export const RESOURCE_CATEGORIES = [
  "tramites",
  "passport",
  "residency",
  "immigration",
  "id-ine",
  "birth-certificate",
  "curp",
  "rfc",
  "general",
] as const;

export const COMMUNITY_SERVICE_CATEGORIES = [
  "infrastructure",
  "medicine",
  "food-drive",
  "cleanup",
  "education",
  "legal-aid",
  "other",
] as const;

export const EVENT_TYPES = [
  "fundraiser",
  "volunteer",
  "cultural",
  "meetup",
  "food-drive",
  "medical",
  "other",
] as const;

export const MEXICAN_STATES = [
  "Aguascalientes",
  "Baja California",
  "Baja California Sur",
  "Campeche",
  "Chiapas",
  "Chihuahua",
  "Ciudad de Mexico",
  "Coahuila",
  "Colima",
  "Durango",
  "Estado de Mexico",
  "Guanajuato",
  "Guerrero",
  "Hidalgo",
  "Jalisco",
  "Michoacan",
  "Morelos",
  "Nayarit",
  "Nuevo Leon",
  "Oaxaca",
  "Puebla",
  "Queretaro",
  "Quintana Roo",
  "San Luis Potosi",
  "Sinaloa",
  "Sonora",
  "Tabasco",
  "Tamaulipas",
  "Tlaxcala",
  "Veracruz",
  "Yucatan",
  "Zacatecas",
] as const;

export const NAV_LINKS = [
  { href: "/", labelKey: "home" },
  { href: "/charity", labelKey: "charities" },
  { href: "/directory", labelKey: "directory" },
  { href: "/resources", labelKey: "resources" },
  { href: "/community", labelKey: "community" },
  { href: "/events", labelKey: "events" },
] as const;

export const CATEGORY_ICONS: Record<string, string> = {
  orphanage: "Heart",
  shelter: "Home",
  "food-bank": "UtensilsCrossed",
  medical: "Stethoscope",
  infrastructure: "Wrench",
  education: "GraduationCap",
  lawyer: "Scale",
  doctor: "Stethoscope",
  accountant: "Calculator",
  "real-estate": "Building",
  translator: "Languages",
  dentist: "Smile",
  notary: "FileCheck",
  tramites: "FileText",
  passport: "BookOpen",
  residency: "MapPin",
  immigration: "Plane",
  "id-ine": "CreditCard",
  "birth-certificate": "Baby",
  curp: "Fingerprint",
  rfc: "Receipt",
  medicine: "Pill",
  "food-drive": "Apple",
  cleanup: "Sparkles",
  "legal-aid": "Scale",
  fundraiser: "HandCoins",
  volunteer: "Users",
  cultural: "Palette",
  meetup: "CalendarHeart",
  other: "MoreHorizontal",
};

export const MEXICO_CENTER = { lat: 23.6345, lng: -102.5528 };
export const DEFAULT_ZOOM = 5;
