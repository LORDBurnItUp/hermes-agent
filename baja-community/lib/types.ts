export interface Location {
  city: string;
  state: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
}

export interface ContactInfo {
  phone?: string;
  email?: string;
  website?: string;
  facebook?: string;
  whatsapp?: string;
}

export interface Charity {
  id: string;
  name: string;
  nameEs: string;
  description: string;
  descriptionEs: string;
  category:
    | "orphanage"
    | "shelter"
    | "food-bank"
    | "medical"
    | "infrastructure"
    | "education"
    | "other";
  location: Location;
  contactInfo: ContactInfo;
  needs: string[];
  donationLinks: { label: string; url: string; type: string }[];
  images: string[];
  featured: boolean;
  tags: string[];
  updatedAt: string;
  createdAt: string;
}

export interface Professional {
  id: string;
  name: string;
  category:
    | "lawyer"
    | "doctor"
    | "accountant"
    | "real-estate"
    | "translator"
    | "dentist"
    | "notary"
    | "other";
  specialties: string[];
  description: string;
  descriptionEs: string;
  location: Location;
  contactInfo: ContactInfo;
  languages: string[];
  credentials?: string[];
  verified: boolean;
  tags: string[];
  updatedAt: string;
  createdAt: string;
}

export interface ResourceStep {
  order: number;
  title: string;
  titleEs: string;
  description: string;
  descriptionEs: string;
  documents?: string[];
  links?: { label: string; url: string }[];
  tips?: string;
}

export interface Resource {
  id: string;
  title: string;
  titleEs: string;
  category:
    | "tramites"
    | "passport"
    | "residency"
    | "immigration"
    | "id-ine"
    | "birth-certificate"
    | "curp"
    | "rfc"
    | "general";
  description: string;
  descriptionEs: string;
  steps: ResourceStep[];
  externalLinks: { label: string; url: string; type: string }[];
  tags: string[];
  updatedAt: string;
  createdAt: string;
}

export interface CommunityService {
  id: string;
  title: string;
  titleEs: string;
  category:
    | "infrastructure"
    | "medicine"
    | "food-drive"
    | "cleanup"
    | "education"
    | "legal-aid"
    | "other";
  description: string;
  descriptionEs: string;
  location: Location;
  organizerName: string;
  contactInfo: Pick<ContactInfo, "phone" | "email" | "whatsapp">;
  schedule?: string;
  volunteerNeeded: boolean;
  tags: string[];
  updatedAt: string;
  createdAt: string;
}

export interface CommunityEvent {
  id: string;
  title: string;
  titleEs: string;
  description: string;
  descriptionEs: string;
  date: string;
  endDate?: string;
  location: {
    name: string;
    city: string;
    state: string;
    address?: string;
    coordinates?: { lat: number; lng: number };
  };
  type:
    | "fundraiser"
    | "volunteer"
    | "cultural"
    | "meetup"
    | "food-drive"
    | "medical"
    | "other";
  charityId?: string;
  registrationUrl?: string;
  tags: string[];
  updatedAt: string;
  createdAt: string;
}

export interface SiteConfig {
  siteName: string;
  siteNameEs: string;
  tagline: string;
  taglineEs: string;
  stats: {
    charitiesSupported: number;
    professionalsListed: number;
    resourcesAvailable: number;
    communityServices: number;
    eventsHosted: number;
    statesReached: number;
  };
  featuredCharityId?: string;
  socialLinks: {
    facebook?: string;
    instagram?: string;
    discord?: string;
  };
}

export type Language = "en" | "es";
