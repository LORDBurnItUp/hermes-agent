import Fuse from "fuse.js";
import {
  getCharities,
  getProfessionals,
  getResources,
  getCommunityServices,
  getEvents,
} from "./data";

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  type: "charity" | "professional" | "resource" | "service" | "event";
  category: string;
  city?: string;
  href: string;
}

function buildSearchIndex(): SearchResult[] {
  const items: SearchResult[] = [];

  getCharities().forEach((c) => {
    items.push({
      id: c.id,
      title: c.name,
      description: c.description,
      type: "charity",
      category: c.category,
      city: c.location.city,
      href: `/charity/${c.id}`,
    });
  });

  getProfessionals().forEach((p) => {
    items.push({
      id: p.id,
      title: p.name,
      description: p.description,
      type: "professional",
      category: p.category,
      city: p.location.city,
      href: `/directory/${p.category}`,
    });
  });

  getResources().forEach((r) => {
    items.push({
      id: r.id,
      title: r.title,
      description: r.description,
      type: "resource",
      category: r.category,
      href: `/resources/${r.category}`,
    });
  });

  getCommunityServices().forEach((s) => {
    items.push({
      id: s.id,
      title: s.title,
      description: s.description,
      type: "service",
      category: s.category,
      city: s.location.city,
      href: "/community",
    });
  });

  getEvents().forEach((e) => {
    items.push({
      id: e.id,
      title: e.title,
      description: e.description,
      type: "event",
      category: e.type,
      city: e.location.city,
      href: "/events",
    });
  });

  return items;
}

let fuseInstance: Fuse<SearchResult> | null = null;

function getFuse(): Fuse<SearchResult> {
  if (!fuseInstance) {
    const items = buildSearchIndex();
    fuseInstance = new Fuse(items, {
      keys: ["title", "description", "category", "city"],
      threshold: 0.4,
      includeScore: true,
    });
  }
  return fuseInstance;
}

export function search(query: string): SearchResult[] {
  if (!query.trim()) return [];
  const fuse = getFuse();
  return fuse.search(query).map((r) => r.item);
}
