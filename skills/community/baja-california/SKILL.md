---
name: baja-california
description: >
  Manage the Hermes Community platform for Mexico — add/update charity listings,
  professional directories, government resource guides (tramites, passports, INE,
  CURP, RFC), community service projects, and events. Full bilingual EN/ES support.
  AI guides users step-by-step through every government process and connects them
  to real professionals, charities, and community services.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [community, charity, mexico, directory, tramites, bilingual, orphanage, food-bank, shelter]
triggers:
  - community service
  - orphanage
  - charity listing
  - tramites
  - passport
  - residency
  - professional directory
  - food bank
  - shelter
  - medicine
  - community platform
  - baja california
  - INE
  - CURP
---

# Hermes Community Platform — Mexico

An AI-powered community service platform that helps everyone in Mexico navigate government
bureaucracy, find professional services, support charities, and engage in community projects.

## Core Capabilities

### 1. Guide Users Through Government Processes
When a user asks about tramites, passports, INE, CURP, RFC, birth certificates, residency,
or immigration — provide a step-by-step walkthrough:
- Required documents
- Where to go (offices, websites)
- Expected costs and timeframes
- Tips and common pitfalls
- Direct links to official government sites

Always provide information in the user's preferred language (English or Spanish).

### 2. Manage Charity & Orphanage Listings
Add, update, or search charity listings by reading/writing to the JSON data files:
- Read: `skill_view(name="baja-california", file_path="../../baja-community/data/seed/charities.json")`
- Write: Use `write_file` to update the JSON, following the schema in `references/data-schemas.md`
- Use `templates/charity-listing.json` as a template for new entries

Categories: orphanage, shelter, food-bank, medical, infrastructure, education

### 3. Manage Professional Directory
Maintain a directory of verified professionals:
- Lawyers (immigration, real estate, business, criminal)
- Doctors and dentists
- Accountants and tax advisors
- Real estate agents
- Translators and interpreters
- Notaries

Use `templates/professional-listing.json` for new entries.

### 4. Manage Community Service Projects
Track active community initiatives:
- Infrastructure repair (pothole fixing, road maintenance)
- Medicine distribution
- Food drives and food banks
- Cleanup campaigns
- Education programs
- Legal aid clinics

Use `templates/community-service.json` for new entries.

### 5. Manage Events
Create and update community events (fundraisers, volunteer days, cultural events, meetups).
Use `templates/event.json` for new entries.

## Content Guidelines

- **Bilingual**: Always provide both English and Spanish versions of content
- **Accuracy-first**: Only include verified information. Flag anything unverified.
- **Community tone**: Warm, encouraging, like a neighbor helping out
- **Free forever**: This platform is a community service, never monetized
- **Connect, don't replace**: Link people to real humans (lawyers, doctors, volunteers)

## Data Files Location

All data lives in `baja-community/data/seed/`:
- `charities.json` — Charity and orphanage listings
- `professionals.json` — Professional directory
- `resources.json` — Government process guides
- `community-services.json` — Community service projects
- `events.json` — Upcoming events
- `site-config.json` — Site metadata and statistics

## Updating Data

1. Read the current file with `skill_view` or `read_file`
2. Parse the JSON array
3. Add/modify the entry following schemas in `references/data-schemas.md`
4. Write the updated JSON back with `write_file`
5. Ensure all bilingual fields (name/nameEs, description/descriptionEs) are populated

## Researching New Entries

Use `web_search` to find and verify:
- Charity organizations, orphanages, shelters in Mexican cities
- Professional credentials and contact information
- Current government procedures and requirements
- Upcoming community events
