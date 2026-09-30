# TravelVista — Technical Architecture

| | |
|---|---|
| **Product** | TravelVista — Travel & Tourism Website |
| **Version** | 1.0 |
| **Status** | Phase 1 (static site) delivered |
| **Owner** | Web Engineering |
| **Last updated** | September 2026 |

---

## 1. Architecture style

Phase 1 is a **single-page static application**: one self-contained HTML document with inlined CSS and JavaScript, no build step, no runtime dependencies, and no network calls except Google Fonts. It is served from a CDN edge and remains fully functional offline once cached.

This choice is deliberate. At the current catalogue size — under 50 items across five collections — a framework would add 40–130 KB of runtime to solve problems the site does not have. Rendering 12 cards with template literals is measurably faster than mounting a component tree, and it keeps the deployment surface to a single file.

### 1.1 Principles

1. **Zero dependencies.** Every added library is a permanent patch obligation.
2. **One source of truth for content.** All catalogue data lives in five arrays; markup is derived, never hand-written per item.
3. **Tokens over hard-coded values.** Colour, radius, shadow and spacing flow from CSS custom properties, which is what makes theming a single attribute flip.
4. **Progressive enhancement of motion.** Every animation has a defined no-op state under `prefers-reduced-motion`.
5. **Accessibility is structural, not a pass at the end.** Semantic landmarks, focus management and ARIA are written with the component, not retrofitted.

---

## 2. System diagram

```
┌────────────────────────────────────────────────────────────────┐
│                           Browser                              │
│                                                                │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐  │
│  │ Presentation │   │   Behaviour    │   │    Data layer    │  │
│  │              │◄──┤                │◄──┤                  │  │
│  │  HTML5       │   │  Vanilla JS    │   │  In-memory JS    │  │
│  │  CSS tokens  │   │  11 modules    │   │  arrays          │  │
│  │  Grid/Flex   │   │  inside 1 IIFE │   │  (the catalogue) │  │
│  └──────────────┘   └────────────────┘   └──────────────────┘  │
│         ▲                   ▲                                  │
│         │                   │                                  │
│  ┌──────┴───────┐    ┌──────┴────────┐                         │
│  │ SVG symbol   │    │ localStorage  │                         │
│  │ library      │    │ (theme key)   │                         │
│  │ 8 scenes     │    └───────────────┘                         │
│  └──────────────┘                                              │
│                                                                │
│  Browser APIs used: IntersectionObserver · MutationObserver ·  │
│  requestAnimationFrame · matchMedia · localStorage             │
└────────────────────────────────────────────────────────────────┘
                              │  HTTPS
                              ▼
        ┌────────────────────────────────────────────┐
        │  Static CDN — Netlify / Vercel / S3+CF     │
        │  Edge cache · TLS 1.3 · security headers   │
        └────────────────────────────────────────────┘
                              │
                              │  Phase 2 (planned)
                              ▼
        ┌────────────────────────────────────────────┐
        │  API gateway                               │
        │   ├─ Enquiry service    → email provider   │
        │   ├─ Booking service    → PostgreSQL       │
        │   ├─ Catalogue service  → headless CMS     │
        │   └─ Payment service    → Razorpay/Stripe  │
        └────────────────────────────────────────────┘
```

---

## 3. Layer breakdown

### 3.1 Presentation layer

**Token system.** Colour, radius, shadow and navigation height are declared as CSS custom properties on `:root`. Dark mode is expressed three times to get the cascade right:

```css
:root { /* light tokens */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark tokens */ }
}

:root[data-theme="dark"] { /* dark tokens, explicit override */ }
```

The guard on the media query is what allows a user who prefers dark at the OS level to still force light mode in the interface. Without it, the media query would win and the toggle would appear broken.

**Layout.** CSS Grid for all card grids and the two-column About/Contact splits; Flexbox for the navigation bar, card internals and button rows. `clamp()` handles fluid type and section padding so there are fewer breakpoints to maintain. `color-mix()` derives translucent surfaces from existing tokens rather than introducing new ones.

**Specificity discipline.** Section padding is owned by a single `.section` class; modifiers such as `.section--tint` change background only. Spacing is never set from two competing selectors, which is the usual source of cancelled-out CSS.

**Breakpoints.**

| Width | Change |
|---|---|
| ≤ 1000 px | 4-up and 3-up grids collapse to 2-up; About and Contact stack; search becomes 2-up |
| ≤ 860 px | Desktop navigation swaps for the drawer; gallery goes 2-up and drops its spanning tiles |
| ≤ 620 px | All grids single-column; search and form pairs stack; base font drops to 16 px |

**Safe areas.** `viewport-fit=cover` plus `env(safe-area-inset-*)` padding on `:root` and `scroll-padding-top` on `html`, so content clears translucent system bars on modern phones and the sticky header never hides an anchor target.

### 3.2 Behaviour layer

All JavaScript runs inside one IIFE in strict mode, so nothing reaches the global scope. Eleven independent modules:

| Module | Responsibility |
|---|---|
| `render*` | Builds destination, package, hotel, gallery and testimonial markup from data |
| `filter/search` | Applies category, free-text and budget predicates; re-renders the destination grid |
| `nav` | Sticky state, mobile drawer, scroll-spy active link |
| `carousel` | Testimonial track transform, dots, auto-advance timer |
| `reveal` | IntersectionObserver entrance animations |
| `counters` | IntersectionObserver animated statistics with cubic easing |
| `overlay` | Shared open/close, focus management, Esc handling, body scroll lock |
| `booking` | Modal population, reference generation, confirmation state |
| `lightbox` | Gallery navigation with wrap-around and keyboard arrows |
| `validation` | Shared rule-runner used by the contact, booking and newsletter forms |
| `theme` | Theme application, persistence, hero sky recolouring via MutationObserver |

**Event delegation.** Card buttons are not bound individually. A single document-level click handler reads `data-book` and `data-price` from whatever was clicked, which means re-rendering the grid after a filter never orphans a listener.

**Shared primitives.** `openOverlay` / `closeOverlay` serve both the booking modal and the lightbox: store the previously focused element, open, move focus inward, lock body scroll, and on close restore focus to the trigger. `validate(rules)` takes an array of `[fieldId, predicate, message]` tuples and is reused by all three forms — one implementation, three consumers.

### 3.3 Data layer

Five arrays hold the entire catalogue:

```
destinations[12] · packages[6] · hotels[6] · gallery[10] · quotes[4]
```

A `scene(symbolId, paletteKey)` helper composes an SVG instance:

```js
`<svg viewBox="0 0 400 300" style="${PALETTE[key]}"
      preserveAspectRatio="xMidYMid slice">
   <use href="#sc-${symbolId}"/>
 </svg>`
```

The palette is injected as inline custom properties, and those properties inherit into the `<use>` shadow tree. That is the mechanism by which eight symbols render in nine distinct colourways — 72 possible combinations from roughly 6 KB of geometry.

One constraint worth recording: **gradients cannot be parameterised this way.** A `<linearGradient>` lives in the light-DOM `<defs>`, so its stop colours resolve against the defs context, not against each `<use>` instance. All scene artwork therefore uses flat colour fields — which also happens to suit the travel-poster aesthetic.

---

## 4. Rendering approach

Cards are produced with template literals and written with a single `innerHTML` assignment per section — one reflow instead of N. Filtering re-renders only the destination grid; the other four collections are rendered once at load and never touched again.

```
data array → .filter(predicates) → .map(template) → .join("") → innerHTML
```

No virtual DOM, no diffing, no keys. At this catalogue size the full re-render costs under a millisecond and ships 0 KB of framework runtime.

---

## 5. Performance engineering

| Technique | Effect |
|---|---|
| Inlined CSS | No render-blocking stylesheet request; no flash of unstyled content |
| SVG symbols instantiated by `<use>` | All artwork for the site in ~6 KB, versus megabytes of JPEG |
| `{ passive: true }` scroll listener | Scrolling is never blocked; the handler only reads layout |
| IntersectionObserver for reveals and counters | No scroll-thrash; observers `unobserve` after firing once |
| `requestAnimationFrame` counters | Animation synced to the compositor, capped at 1.3 s with ease-out cubic |
| `font-display: swap` + preconnect | Text is readable before the webfont arrives |
| Transform/opacity-only animation | Every effect stays on the compositor; no layout-triggering properties animated |
| Single-file delivery | One request, fully edge-cacheable |

**Budget:** total payload under 250 KB excluding fonts; First Contentful Paint under 1.2 s on 4G.

---

## 6. Theming architecture

```
Toggle click
  └─ data-theme flipped on <html>
     ├─ Token block swaps (CSS handles every surface, border and text colour)
     ├─ Icon morphs sun ⇄ moon; aria-label updated
     ├─ Preference written to localStorage inside try/catch
     └─ MutationObserver on data-theme fires skyVars()
        └─ Hero sky, ridgelines, snow caps and treeline repainted
```

The hero illustration cannot be themed by CSS tokens alone, because its colours need different relationships in dark mode rather than a straight inversion — a dusk sky, deeper ridgelines, a muted treeline. A `MutationObserver` watching the `data-theme` attribute sets a second group of custom properties for the hero specifically. This keeps the theme logic in one place regardless of what triggered the change.

Resolution order at load: `localStorage` → OS preference via `matchMedia` → light. All `localStorage` access is wrapped in `try/catch`, and the page renders correctly when storage is unavailable or empty.

---

## 7. Accessibility architecture

| Concern | Implementation |
|---|---|
| Landmarks | `header` / `nav` / `main` / `section[id]` / `footer`, one `h1` |
| Skip link | First focusable element, jumps to `#main` |
| Focus visibility | `:focus-visible` with a 3 px marigold ring and offset, never removed |
| Focus management | Overlays trap entry and restore focus to the trigger on close |
| Keyboard | Esc closes overlays; ←/→ navigate the lightbox; every control is reachable by Tab |
| State communication | `aria-pressed` on filters, `aria-current` on carousel dots, `aria-expanded` on the drawer, `aria-modal` on overlays |
| Motion | `prefers-reduced-motion` zeroes all durations and switches smooth scrolling to instant |
| Contrast | All text pairs meet 4.5:1 in both themes |

---

## 8. Phase 2 target architecture

| Concern | Technology | Rationale |
|---|---|---|
| Frontend | Next.js 14 App Router, TypeScript | Server rendering for SEO and no-JS resilience |
| Styling | Same token system ported to CSS modules | Zero visual regression from Phase 1 |
| Content | Headless CMS — Strapi or Sanity | Operations edits the catalogue without a deploy |
| API | Next route handlers or Express, REST with JSON schema validation | Small surface; no GraphQL complexity at this scale |
| Database | PostgreSQL 16 + Prisma | `destinations`, `packages`, `hotels`, `bookings`, `enquiries`, `users` |
| Cache | Redis | Availability lookups and rate-limit counters |
| Payments | Razorpay (domestic), Stripe (international) | Server-side order creation, webhook confirmation |
| Email | Resend or Amazon SES | Booking confirmations and itinerary delivery |
| Search | Postgres full-text → Meilisearch beyond ~2,000 items | Avoid a search service until the catalogue justifies it |
| Media | S3 + CloudFront | Real photography with responsive `srcset` |
| Observability | Sentry, Plausible, Lighthouse CI | Error, product and performance signals |
| CI/CD | GitHub Actions → preview deploys → production | Every PR gets a URL |
| Testing | Vitest, Playwright, axe-core | Unit, end-to-end and accessibility regression |

### 8.1 Migration path

The Phase 1 data arrays map one-to-one onto CMS content types, so migration is a data-entry task rather than a rewrite. The `scene()` helper is the single seam where illustration becomes photography — swapping its return value for an `<img>` with `loading="lazy"` and `decoding="async"` is the entire change, and the 4:3 aspect box is already reserved so there is no layout shift.

---

## 9. Deliverable structure

```
travelvista.html                single self-contained file
├─ <head>
│   ├─ meta viewport-fit=cover, description
│   └─ Google Fonts preconnect + stylesheet
├─ <style>                      ~520 lines
│   ├─ token block (light · media-dark · explicit-dark)
│   ├─ base + typography scale
│   ├─ components (nav, hero, search, card, filters, gallery,
│   │              carousel, forms, footer, overlay)
│   ├─ motion (hero choreography, reveals, reduced-motion reset)
│   └─ breakpoints (1000 · 860 · 620)
├─ <body>
│   ├─ skip link · progress bar · header/nav · mobile drawer
│   ├─ hero · search · destinations · packages · hotels
│   ├─ gallery · testimonials · about · contact
│   ├─ footer · back-to-top
│   └─ booking modal · gallery lightbox
├─ <svg> symbol library         8 poster scenes, display:none
└─ <script>                     ~330 lines
    ├─ helpers ($, $$, rupee, scene)
    ├─ palettes + 5 data collections
    ├─ renderers
    └─ 11 behaviour modules
```

---

## 10. Constraints and trade-offs

| Decision | Gained | Given up |
|---|---|---|
| No framework | 0 KB runtime, no build step, no dependency upgrades | Component reuse, type safety, ecosystem tooling |
| Single file | One request, trivial deployment | Requires `'unsafe-inline'` in CSP until CSS/JS are extracted |
| Client-side rendering | Instant filtering, no server | Content invisible without JavaScript; weaker SEO until Phase 2 |
| SVG illustration | ~6 KB of artwork, theme-aware, infinitely scalable | Not photoreal; less persuasive than genuine trip photography |
| In-file catalogue | Zero infrastructure | Content edits require a developer and a deploy |

---

## 11. Known technical debt

1. Inline `<style>` and `<script>` force `'unsafe-inline'` in the Content-Security-Policy. Extracting both to external files is the highest-value hardening step and should precede a public launch.
2. Google Fonts is the only third-party origin. Self-hosting the two families removes it entirely and improves privacy posture.
3. Booking references are generated client-side and are not guaranteed unique — acceptable only because no record is persisted.
4. Scroll-spy uses `offsetTop` comparisons; an IntersectionObserver implementation would be cheaper if the page grows past a dozen sections.
