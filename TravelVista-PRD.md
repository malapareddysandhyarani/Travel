# TravelVista — Product Requirements Document

| | |
|---|---|
| **Product** | TravelVista — Travel & Tourism Website |
| **Version** | 1.0 |
| **Status** | Phase 1 (static site) delivered |
| **Owner** | Web Engineering |
| **Last updated** | September 2026 |

---

## 1. Summary

TravelVista is a travel and tourism website for a small-group tour operator. It lets a visitor discover destinations, compare fixed-departure tour packages, look at partner hotels, browse trip photography, and send an enquiry or booking request.

Phase 1 ships as a fully client-side site so it can be hosted anywhere and loaded fast on a mid-range phone over a 3G connection. Everything a visitor needs to make a decision — price, duration, inclusions, rating — is visible on the card itself.

---

## 2. Problem statement

Most tour-operator websites:

- bury prices behind an enquiry form or a phone call,
- load several megabytes of hero photography before anything is readable,
- and pad itineraries with shopping stops the traveller never asked for.

Visitors leave before they ever see a price. TravelVista puts the price on the card and lets someone raise a booking request in under 60 seconds.

---

## 3. Goals and non-goals

### 3.1 Goals

- Show a price on every destination, package and hotel without requiring a click.
- Let a visitor filter and search the catalogue instantly, with no page reload.
- Capture qualified enquiries — destination, dates, party size, budget.
- Treat a 360 px-wide phone as the first-class case, not an afterthought.
- Score ≥ 95 on Lighthouse Performance and ≥ 95 on Accessibility.

### 3.2 Non-goals for Phase 1

- Live payments, seat inventory, or a PNR/booking engine.
- User accounts, wishlists, or saved trips.
- Multi-currency and multi-language support (INR and English only).
- Admin CMS for editing the catalogue.

---

## 4. Target users

| Persona | Context | Need | Success signal |
|---|---|---|---|
| **Aditi**, 29, first international trip | Researching on her phone during a commute | A price she can trust and a plan she can show her parents | Opens a package, reads the inclusions, sends an enquiry |
| **Rohit**, 41, frequent traveller | Books 3–4 trips a year, dislikes group tours | Fast filtering, honest group size, no shopping stops | Filters to "Mountains", books a fixed departure |
| **Meera**, 63, travelling with family | Low technical confidence, prefers the phone | Large readable type, a visible phone number, no dark patterns | Calls the listed number or completes the contact form |

---

## 5. Scope — sections

| Section | Purpose |
|---|---|
| **Home** | Hero, positioning statement, trust statistics, primary calls to action |
| **Search** | Destination text search, travel month, budget ceiling |
| **Destinations** | 12 destinations with category filters and live search |
| **Tour Packages** | 6 fixed departures with pricing, duration and inclusions |
| **Hotels** | 6 partner properties with nightly rates and amenities |
| **Gallery** | Trip imagery with a lightbox viewer |
| **Testimonials** | Rotating traveller reviews |
| **About Us** | Company story and animated statistics |
| **Contact** | Enquiry form, office address, phone, email |
| **Footer** | Navigation, newsletter signup, social links, legal |

---

## 6. Functional requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-01 | Sticky navigation across all seven sections with active-section highlighting | Must | Done |
| FR-02 | Hero with headline, dual CTA, and three trust statistics | Must | Done |
| FR-03 | Search panel: free-text destination, travel month, budget ceiling | Must | Done |
| FR-04 | Destination grid (12 items) with category filters and live text search | Must | Done |
| FR-05 | Tour packages (6) with price, strike-through original price, duration, inclusions, rating | Must | Done |
| FR-06 | Hotels (6) with nightly rate, star rating, amenity chips | Must | Done |
| FR-07 | Gallery with lightbox, keyboard arrow navigation, Esc to close | Must | Done |
| FR-08 | Testimonial carousel, auto-advancing, with dot navigation | Should | Done |
| FR-09 | About section with animated statistic counters | Should | Done |
| FR-10 | Contact form with inline field-level validation and a success state | Must | Done |
| FR-11 | Booking modal launched from any card, generating a booking reference | Must | Done |
| FR-12 | Newsletter subscribe in the footer with email validation | Could | Done |
| FR-13 | Empty state when filters return nothing, with a route out (custom trip CTA) | Should | Done |
| FR-14 | Light/dark theme honouring the OS setting, with a manual override | Could | Done |
| FR-15 | Scroll progress indicator and back-to-top control | Could | Done |

### 6.1 Detailed behaviour

**Search and filter.** Category chips, free-text query and budget ceiling compose rather than override each other — all three are applied as predicates against the same collection. Quick-pick links ("Iceland", "Beaches") write into the search field and run the same code path. When nothing matches, the grid shows an empty state with a "Request a custom trip" call to action rather than a dead end.

**Booking request.** Any card's primary button opens a modal pre-filled with the trip name and starting price. The form validates lead traveller name, email, and a departure date strictly in the future. On success it issues a reference in the format `TV-XXXXX` and states that seats are held for 48 hours. No payment is taken in Phase 1.

**Enquiry.** The contact form validates name (≥ 2 characters), phone, email, and message (≥ 10 characters). Errors appear inline beneath the field, and focus moves to the first invalid input. On success the confirmation names the email address that will be replied to.

---

## 7. Non-functional requirements

| Area | Target |
|---|---|
| **Performance** | First Contentful Paint < 1.2 s on 4G; total payload < 250 KB excluding fonts |
| **Responsiveness** | Breakpoints at 1000 px, 860 px, 620 px; no horizontal scroll at 320 px |
| **Accessibility** | WCAG 2.1 AA — visible focus rings, 4.5:1 text contrast, ARIA on all controls, full keyboard operation |
| **Motion** | `prefers-reduced-motion` disables all animation and smooth scrolling |
| **Browser support** | Last two versions of Chrome, Safari, Firefox, Edge; iOS 15+; Android 10+ |
| **SEO** | Semantic landmarks, a single `h1`, descriptive meta description, crawlable anchors |
| **Security** | No personal data stored client-side; `localStorage` used only for the theme preference |

---

## 8. Content model

```
Destination { name, country, price, duration, rating, tags[], category, scene, palette }
Package     { name, locations, days, price, wasPrice?, rating, featured, inclusions[] }
Hotel       { name, location, nightlyRate, rating, amenities[] }
GalleryItem { caption, scene, palette }
Testimonial { quote, name, tripReference }
```

All five collections are declared as JavaScript arrays in one place, so the entire catalogue can be edited in a single block without touching markup. Every card in the interface is rendered from this data.

---

## 9. Design decisions

**Illustration instead of stock photography.** Each destination, hotel and gallery frame is a flat, mid-century travel-poster SVG drawn from a shared symbol library and recoloured per item using CSS custom properties. Eight scene types across nine palettes produce distinct artwork for roughly 6 KB in total, versus several megabytes of JPEGs — and the page stays self-contained with no external image host. Swapping to real photography is a drop-in change.

**Polychrome palette.** Jade, marigold, vermilion, sky and plum on paper white, taken from the travel-poster vernacular rather than the single-accent treatment most travel sites use.

**Typography.** Bricolage Grotesque for display, Karla for body text — one distinctive headline face, one workhorse text face.

**Pricing in INR**, formatted with Indian digit grouping (₹1,86,500).

**Motion budget.** One orchestrated page-load moment in the hero; everything after it stays calm. Twelve animation effects in total, each collapsing to a no-op under reduced-motion.

---

## 10. Success metrics

| Metric | Baseline | Target |
|---|---|---|
| Enquiry form completion rate | — | ≥ 6% of sessions |
| Bounce rate on mobile | — | < 45% |
| Median time to first price seen | — | < 5 s |
| Lighthouse performance score (mobile) | — | ≥ 95 |
| Booking modal open → submit rate | — | ≥ 25% |

---

## 11. Release plan

| Phase | Scope |
|---|---|
| **Phase 1 — shipped** | Static single-file site, simulated forms, illustrated artwork |
| **Phase 2** | Working enquiry and booking endpoints, headless CMS, real photography, email confirmations |
| **Phase 3** | Payments, seat inventory, user accounts, multi-currency |

---

## 12. Known limitations in Phase 1

- Form submissions are simulated in the browser; no message is transmitted.
- Booking references are generated client-side and are not unique across users.
- The catalogue is static — editing requires touching the file.
- Content renders only with JavaScript enabled; resolved by server rendering in Phase 2.

---

## 13. Open questions

1. Real photography or keep the illustrated poster artwork?
2. Currency — stay with INR, or switch to USD/EUR for an international audience?
3. Which service should receive form submissions (Formspree, EmailJS, own backend)?
4. Should the code be split into separate `index.html` / `style.css` / `script.js` files?
