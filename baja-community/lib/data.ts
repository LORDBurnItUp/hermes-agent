import type {
  Charity,
  Professional,
  Resource,
  CommunityService,
  CommunityEvent,
  SiteConfig,
} from "./types";

import charitiesData from "@/data/seed/charities.json";
import professionalsData from "@/data/seed/professionals.json";
import resourcesData from "@/data/seed/resources.json";
import communityServicesData from "@/data/seed/community-services.json";
import eventsData from "@/data/seed/events.json";
import siteConfigData from "@/data/seed/site-config.json";

export function getCharities(): Charity[] {
  return charitiesData as Charity[];
}

export function getCharityById(id: string): Charity | undefined {
  return getCharities().find((c) => c.id === id);
}

export function getCharitiesByCategory(category: string): Charity[] {
  if (category === "all") return getCharities();
  return getCharities().filter((c) => c.category === category);
}

export function getFeaturedCharity(): Charity | undefined {
  return getCharities().find((c) => c.featured);
}

export function getProfessionals(): Professional[] {
  return professionalsData as Professional[];
}

export function getProfessionalById(id: string): Professional | undefined {
  return getProfessionals().find((p) => p.id === id);
}

export function getProfessionalsByCategory(category: string): Professional[] {
  if (category === "all") return getProfessionals();
  return getProfessionals().filter((p) => p.category === category);
}

export function getResources(): Resource[] {
  return resourcesData as Resource[];
}

export function getResourceById(id: string): Resource | undefined {
  return getResources().find((r) => r.id === id);
}

export function getResourcesByCategory(category: string): Resource[] {
  if (category === "all") return getResources();
  return getResources().filter((r) => r.category === category);
}

export function getCommunityServices(): CommunityService[] {
  return communityServicesData as CommunityService[];
}

export function getCommunityServiceById(
  id: string
): CommunityService | undefined {
  return getCommunityServices().find((s) => s.id === id);
}

export function getEvents(): CommunityEvent[] {
  return eventsData as CommunityEvent[];
}

export function getEventById(id: string): CommunityEvent | undefined {
  return getEvents().find((e) => e.id === id);
}

export function getSiteConfig(): SiteConfig {
  return siteConfigData as SiteConfig;
}

export function getAllCities(): string[] {
  const cities = new Set<string>();
  getCharities().forEach((c) => cities.add(c.location.city));
  getProfessionals().forEach((p) => cities.add(p.location.city));
  getCommunityServices().forEach((s) => cities.add(s.location.city));
  getEvents().forEach((e) => cities.add(e.location.city));
  return Array.from(cities).sort();
}

export function getAllCoordinates(): {
  lat: number;
  lng: number;
  label: string;
  type: string;
  id: string;
}[] {
  const points: {
    lat: number;
    lng: number;
    label: string;
    type: string;
    id: string;
  }[] = [];

  getCharities().forEach((c) => {
    if (c.location.coordinates) {
      points.push({
        ...c.location.coordinates,
        label: c.name,
        type: "charity",
        id: c.id,
      });
    }
  });

  getProfessionals().forEach((p) => {
    if (p.location.coordinates) {
      points.push({
        ...p.location.coordinates,
        label: p.name,
        type: "professional",
        id: p.id,
      });
    }
  });

  getCommunityServices().forEach((s) => {
    if (s.location.coordinates) {
      points.push({
        ...s.location.coordinates,
        label: s.title,
        type: "service",
        id: s.id,
      });
    }
  });

  return points;
}
