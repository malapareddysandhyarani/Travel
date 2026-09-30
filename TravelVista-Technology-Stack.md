# TravelVista — Technology Stack

| | |
|---|---|
| **Product** | TravelVista — Travel & Tourism Website |
| **Version** | 1.0 |
| **Status** | Phase 1 (static site) delivered |
| **Owner** | Web Engineering |
| **Last updated** | September 2026 |

---

## 1. Stack philosophy

Phase 1 is built with **zero runtime dependencies** on purpose. At the current scale — five data collections, under 50 catalogue items, no accounts, no payments — a framework, a bundler and a package tree would add build complexity and patch obligations to solve problems the site doesn't yet have. Every technology below was chosen because it is either a browser-native capability or, in Phase 2, because the catalogue and traffic have grown enough to justify the added surface.

---

## 2. Phase 1 — shipped stack

| Layer | Technology | Why this, not an alternative |
|---|---|---|
| Markup | HTML5 — semantic landmarks, ARIA attributes | Accessible and crawlable with no tooling; `<header>`/`<main>`/`<section>`/`<footer>` give assistive tech and search engines structure for free |
| Styling | CSS3 — custom properties, Grid, Flexbox, `clamp()`, `color-mix()` | A full theming system (light/dark, tokenised colour and spacing) without Sass, PostCSS, or a CSS-in-JS runtime |
| Behaviour | Vanilla JavaScript (ES2020), one IIFE, strict mode | No React/Vue overhead for ~50 rendered cards; direct DOM writes are faster than a virtual-DOM diff at this scale, and there is no bundler to configure |
| Imagery | Inline SVG symbol library, `<use>` references, per-instance CSS variables | All destination/hotel/gallery artwork in roughly 6 KB total; infinitely scalable, no image CDN, theme-aware by construction |
| Typography | **Bricolage Grotesque** (display) + **Karla** (body), via Google Fonts | One distinctive headline face, one workhorse text face — deliberately not a templated cream-and-serif default |
| Browser APIs | `IntersectionObserver`, `MutationObserver`, `requestAnimationFrame`, `matchMedia`, `localStorage` | Scroll reveals, animated counters, theme detection and persistence — all native, no animation library |
| Persistence | `localStorage` (one key: theme preference) | The only piece of client state worth persisting in Phase 1; wrapped in `try/catch` so private browsing never breaks the page |
| Hosting | Any static host — Netlify, Vercel, Cloudflare Pages, or S3 + CloudFront | A single HTML file is edge-cacheable everywhere; no server process to run or scale |

### 2.1 What's deliberately absent

| Not used | Reason |
|---|---|
| React / Vue / Svelte | No component reuse problem at this scale; adds 40–130 KB of runtime for no measurable benefit |
| Webpack / Vite / esbuild | Nothing to bundle — one file ships as-is |
| Tailwind / Bootstrap | A bespoke token system gives a distinct visual identity; a utility framework pushes toward the same default look every generated site has |
| jQuery | Every DOM operation used (`querySelector`, `classList`, `addEventListener`) has been native for over a decade |
| A charting or animation library | CSS transitions/keyframes plus `requestAnimationFrame` cover every effect on the page |
| npm / package.json | Zero dependencies means zero `npm install`, zero lockfile, zero `npm audit` surface to monitor |

---

## 3. Phase 1 file footprint

```
travelvista.html
├─ HTML            ~2 KB minified
├─ CSS (inline)    ~18 KB minified
├─ JS (inline)     ~14 KB minified
├─ SVG symbols     ~6 KB (8 scenes, all destinations/hotels/gallery)
└─ Fonts           loaded from Google Fonts, ~40 KB (2 families, few weights)
   ─────────────────────────────────────────────────
   Total (excl. fonts): well under the 250 KB budget
```

One HTTP request for the page, one for the stylesheet reference, a handful for font files. No image requests at all.

---

## 4. Phase 2 — proposed stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend framework | **Next.js 14** (App Router), **TypeScript** | Server rendering restores SEO and no-JS resilience; TypeScript catches data-shape errors the current plain-array model can't |
| State management | **React Query** (server state) + **Zustand** (UI state) | React Query handles caching/refetching for API-backed catalogue data; Zustand covers small client-only state (filters, modal open/closed) without Redux ceremony |
| Backend | **Node.js** + **Express**, or Next.js route handlers | Either keeps the stack in one language; route handlers avoid a second deployable if the team is small |
| Database | **PostgreSQL 16** + **Prisma** | Relational data (destinations, packages, hotels, bookings, enquiries, users) with real foreign keys; Prisma gives type-safe queries that match the TypeScript frontend |
| Cache / queue | **Redis** | Availability lookups and rate-limit counters need sub-millisecond reads that a primary database shouldn't be hit with on every request |
| Headless CMS | **Strapi** or **Sanity** | Lets operations edit the catalogue without a code deploy — the single biggest Phase 1 limitation |
| Payments | **Razorpay** (domestic) / **Stripe** (international) | Hosted-field integration keeps PCI scope at SAQ-A; both have mature webhook-based confirmation flows |
| Transactional email | **Resend** or **Amazon SES** | Booking confirmations, itinerary delivery, enquiry acknowledgements |
| Search | **PostgreSQL full-text search**, upgrading to **Meilisearch** past ~2,000 catalogue items | Avoids standing up a dedicated search service before the data volume justifies it |
| Media storage | **Amazon S3 + CloudFront** | Once illustration is swapped for real photography, this is where it's hosted and delivered with responsive `srcset` |
| Observability | **Sentry** (errors), **Plausible** or **GA4** (product analytics), **Lighthouse CI** (performance regression) | Error visibility, usage insight, and a performance budget enforced in CI rather than discovered in production |
| CI/CD | **GitHub Actions** → preview deploys → production | Every pull request gets a live preview URL before merge |
| Testing | **Vitest** (unit), **Playwright** (end-to-end), **axe-core** (accessibility regression) | Covers logic, user flows, and the accessibility bar this build was written to meet |
| Auth (admin only) | **NextAuth** or **Auth0**, Argon2id hashing, mandatory MFA | Scoped to the internal catalogue/booking console — the public site never has user accounts in this plan |

---

## 5. Stack comparison at a glance

| Concern | Phase 1 | Phase 2 |
|---|---|---|
| Rendering | Client-side, static file | Server-rendered (Next.js), hydrated |
| Content edits | Edit the HTML file, redeploy | Edit in the CMS, no deploy needed |
| Data storage | In-memory JS arrays | PostgreSQL |
| Search | Array `.filter()` in the browser | Postgres FTS → Meilisearch at scale |
| Forms | Simulated confirmation, nothing transmitted | Persisted via API, emailed, rate-limited |
| Payments | None | Razorpay/Stripe, SAQ-A scope |
| Images | Inline SVG illustration | S3 + CloudFront photography |
| Dependencies | Zero | A defined, audited set (see §4) |
| Hosting | Any static host | Vercel or equivalent Next.js-capable host |
| Testing | Manual | Vitest + Playwright + axe-core in CI |

---

## 6. Why the migration is low-risk

The Phase 1 architecture was written with this transition in mind, which keeps the Phase 2 migration closer to additive work than a rewrite:

- The five data arrays (`destinations`, `packages`, `hotels`, `gallery`, `quotes`) map one-to-one onto CMS content types — migration is a data-entry task, not a schema redesign.
- The CSS token system ports directly into CSS modules or Tailwind config with no visual change.
- The `scene()` helper is the single seam where illustration becomes photography; swapping its return value for an `<img>` is the entire change, since the 4:3 card aspect ratio is already reserved and nothing shifts layout.
- Client-side validation rules carry over as the first draft of server-side schema validation — the rules don't change, only where they're enforced.

---

## 7. Technology decision log

| Decision | Alternative considered | Why rejected |
|---|---|---|
| Vanilla JS over React for Phase 1 | React with a lightweight bundler | Bundle size and build step buy nothing at 50 items; revisit once the catalogue or interactivity grows |
| Inline SVG over stock photography | Unsplash API / licensed photo library | Keeps the artifact fully self-contained with no external image host and no licensing to track; photography is a planned Phase 2 upgrade |
| PostgreSQL over MongoDB for Phase 2 | MongoDB | The domain is relational by nature — bookings reference packages reference destinations; foreign keys and joins are a better fit than document storage |
| Razorpay + Stripe over a single gateway | Stripe only | Razorpay has stronger UPI/domestic-card support for the India-based traveller base; Stripe covers international cards cleanly |
| Strapi/Sanity over a custom admin panel | Bespoke CMS | Building and securing a custom admin panel is a larger surface than integrating a maintained headless CMS |
