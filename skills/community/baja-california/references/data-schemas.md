# Data Schemas

All data files use JSON arrays. Each entry must conform to these schemas.

## Charity Schema
```json
{
  "id": "string (kebab-case slug)",
  "name": "string (English name)",
  "nameEs": "string (Spanish name)",
  "description": "string (English description)",
  "descriptionEs": "string (Spanish description)",
  "category": "orphanage | shelter | food-bank | medical | infrastructure | education | other",
  "location": {
    "city": "string",
    "state": "string",
    "address": "string (optional)",
    "coordinates": { "lat": "number", "lng": "number" }
  },
  "contactInfo": {
    "phone": "string (optional)",
    "email": "string (optional)",
    "website": "string (optional)",
    "facebook": "string (optional)",
    "whatsapp": "string (optional)"
  },
  "needs": ["string array of current needs"],
  "donationLinks": [{ "label": "string", "url": "string", "type": "string" }],
  "images": ["string array of image URLs"],
  "featured": "boolean",
  "tags": ["string array"],
  "updatedAt": "ISO 8601 date string",
  "createdAt": "ISO 8601 date string"
}
```

## Professional Schema
```json
{
  "id": "string (kebab-case slug)",
  "name": "string",
  "category": "lawyer | doctor | accountant | real-estate | translator | dentist | notary | other",
  "specialties": ["string array"],
  "description": "string (English)",
  "descriptionEs": "string (Spanish)",
  "location": {
    "city": "string",
    "state": "string",
    "address": "string (optional)",
    "coordinates": { "lat": "number", "lng": "number" }
  },
  "contactInfo": {
    "phone": "string (optional)",
    "email": "string (optional)",
    "website": "string (optional)",
    "whatsapp": "string (optional)"
  },
  "languages": ["string array"],
  "credentials": ["string array (optional)"],
  "verified": "boolean",
  "tags": ["string array"],
  "updatedAt": "ISO 8601 date string",
  "createdAt": "ISO 8601 date string"
}
```

## Resource Schema
```json
{
  "id": "string (kebab-case slug)",
  "title": "string (English)",
  "titleEs": "string (Spanish)",
  "category": "tramites | passport | residency | immigration | id-ine | birth-certificate | curp | rfc | general",
  "description": "string (English)",
  "descriptionEs": "string (Spanish)",
  "steps": [
    {
      "order": "number",
      "title": "string (English)",
      "titleEs": "string (Spanish)",
      "description": "string (English)",
      "descriptionEs": "string (Spanish)",
      "documents": ["string array (optional)"],
      "links": [{ "label": "string", "url": "string" }],
      "tips": "string (optional)"
    }
  ],
  "externalLinks": [{ "label": "string", "url": "string", "type": "string" }],
  "tags": ["string array"],
  "updatedAt": "ISO 8601 date string",
  "createdAt": "ISO 8601 date string"
}
```

## CommunityService Schema
```json
{
  "id": "string (kebab-case slug)",
  "title": "string (English)",
  "titleEs": "string (Spanish)",
  "category": "infrastructure | medicine | food-drive | cleanup | education | legal-aid | other",
  "description": "string (English)",
  "descriptionEs": "string (Spanish)",
  "location": {
    "city": "string",
    "state": "string",
    "address": "string (optional)",
    "coordinates": { "lat": "number", "lng": "number" }
  },
  "organizerName": "string",
  "contactInfo": {
    "phone": "string (optional)",
    "email": "string (optional)",
    "whatsapp": "string (optional)"
  },
  "schedule": "string (optional)",
  "volunteerNeeded": "boolean",
  "tags": ["string array"],
  "updatedAt": "ISO 8601 date string",
  "createdAt": "ISO 8601 date string"
}
```

## Event Schema
```json
{
  "id": "string (kebab-case slug)",
  "title": "string (English)",
  "titleEs": "string (Spanish)",
  "description": "string (English)",
  "descriptionEs": "string (Spanish)",
  "date": "ISO 8601 date string",
  "endDate": "ISO 8601 date string (optional)",
  "location": {
    "name": "string",
    "city": "string",
    "state": "string",
    "address": "string (optional)",
    "coordinates": { "lat": "number", "lng": "number" }
  },
  "type": "fundraiser | volunteer | cultural | meetup | food-drive | medical | other",
  "charityId": "string (optional, links to charity)",
  "registrationUrl": "string (optional)",
  "tags": ["string array"],
  "updatedAt": "ISO 8601 date string",
  "createdAt": "ISO 8601 date string"
}
```

## SiteConfig Schema
```json
{
  "siteName": "Hermes Community",
  "siteNameEs": "Comunidad Hermes",
  "tagline": "Community that Connects",
  "taglineEs": "Comunidad que Conecta",
  "stats": {
    "charitiesSupported": "number",
    "professionalsListed": "number",
    "resourcesAvailable": "number",
    "communityServices": "number",
    "eventsHosted": "number",
    "statesReached": "number"
  },
  "featuredCharityId": "string (optional)",
  "socialLinks": {
    "facebook": "string (optional)",
    "instagram": "string (optional)",
    "discord": "string (optional)"
  }
}
```
