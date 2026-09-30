# TravelVista — System Workflow

| | |
|---|---|
| **Product** | TravelVista — Travel & Tourism Website |
| **Version** | 1.0 |
| **Status** | Phase 1 (static site) delivered |
| **Owner** | Web Engineering |
| **Last updated** | September 2026 |

---

## 1. Purpose

This document traces every user-triggered flow through the system, from the moment a request leaves the browser to the state the interface ends in. Phase 1 flows are entirely client-side; each one also states what changes once the Phase 2 backend (see the Technical Architecture doc, §8) is in place.

---

## 2. Page load

```
Request HTML
   └─ Parse begins; inline <style> applies immediately
      └─ No external stylesheet blocks paint → no flash of unstyled content
         └─ DOM ready → IIFE executes
            ├─ Theme resolved: localStorage → OS preference (matchMedia) → light
            ├─ Hero sky custom properties set for the resolved theme
            ├─ Five data collections rendered into their grids
            │    (destinations · packages · hotels · gallery · testimonials)
            ├─ IntersectionObservers attached to .reveal elements and [data-count]
            ├─ Scroll and resize listeners registered (passive)
            └─ Hero choreography plays:
                 sun rises and scales in (1.5 s)
                 → three ridgeline layers stagger up (0.15 s apart)
                 → headline, subhead, CTAs, stats lift in sequence
                 (entire sequence skipped under prefers-reduced-motion)
```

**Phase 2 change:** the HTML arrives pre-rendered from the server with the catalogue already in the markup (Next.js SSR), so content is visible even before JavaScript executes. Hydration then attaches the same behaviour modules.

---

## 3. Search and filter

```
User types in the search field, picks a month/budget, or presses "Search trips"
   └─ Form submit intercepted, default prevented
      └─ State updated: { query, maxBudget, activeCat: "All" }
         └─ destinations.filter(category ∧ text-match ∧ budget-ceiling)
            ├─ Matches found
            │    → grid re-rendered from the filtered array
            │    → page scrolls to the Destinations section
            └─ No matches
                 → empty state rendered: "No trips match that yet"
                 → CTA offered: "Request a custom trip" → links to #contact
```

**Category chips** mutate only `activeCat` and re-run the identical predicate chain, so category and free-text search compose rather than override each other.

**Quick-pick links** ("Iceland", "Beaches", "Japan", "Trekking") write their value into the search field and invoke the same `runSearch()` function — one code path, three entry points (form submit, chip click, quick-pick click).

```
                 ┌────────────┐
  free text ────►│            │
  category ──────►│  predicate ├────► filtered array ────► re-render
  budget ────────►│   chain    │
                 └────────────┘
```

**Phase 2 change:** for a catalogue beyond ~2,000 items, filtering moves server-side: `GET /api/destinations?q=&category=&maxBudget=` against Postgres full-text search or Meilisearch, with the client showing a loading state between request and response.

---

## 4. Booking request

```
Click "Book now" / "Book this trip" / "Check availability" on any card
   └─ Delegated document-level click handler reads data-book and data-price
      └─ Modal populated: title = trip name, subtitle = starting price + cancellation note
         └─ Form and prior error states reset
            └─ Overlay opens
                 ├─ Previously focused element stored
                 ├─ Focus moves to the first field
                 └─ Body scroll locked
                    └─ User submits
                       └─ validate(name ≥2 chars, valid email, date strictly future)
                          ├─ Invalid
                          │    → inline error messages rendered per field
                          │    → focus moves to the first invalid field
                          └─ Valid
                               → reference generated: TV-XXXXX
                               → confirmation panel shown:
                                   "N seat(s) held for 48 hours,
                                    itinerary will be emailed to {address}"
                               → submit button label changes to "Request sent"
   Close via × / Esc / backdrop click
      → overlay closes, body scroll unlocked, focus restored to the trigger button
```

**Phase 2 change:** the valid branch calls `POST /api/bookings` instead of generating a local reference. The server checks live availability, creates a payment intent (Razorpay/Stripe), and only issues the reference after the intent is confirmed. A webhook then triggers the confirmation email. Failure states (sold out, payment declined) become new branches in this flow.

```
Phase 2:
  valid submit → POST /api/bookings
      ├─ 409 (sold out)      → "This departure just filled up" + alternate dates
      ├─ 402 (payment failed) → return to payment step with a clear reason
      └─ 201 (created)        → reference from server, confirmation email queued
```

---

## 5. Contact / enquiry

```
Contact form submit
   └─ default prevented
      └─ validate(
           name ≥ 2 chars,
           phone matches /^[+\d][\d\s-]{7,}$/,
           email matches emailRe,
           message ≥ 10 chars
         )
         ├─ Any rule fails
         │    → field marked invalid, message shown beneath it
         │    → focus moves to the first failing field
         └─ All pass
              → success note rendered, naming the email address that will be replied to
              → form fields reset
              → note scrolled into view
```

**Phase 2 change:** `POST /api/enquiries` persists the enquiry to Postgres, sends an acknowledgement email to the visitor, and notifies the planner queue (Slack or email). Rate limiting and a honeypot field guard the endpoint against spam before it reaches the database.

---

## 6. Gallery / lightbox

```
Click a gallery frame
   └─ Index stored (lbi)
      └─ Lightbox overlay opens with that scene rendered at full size and its caption
         ├─ → / next button    → showLB(lbi + 1), wraps to the first image
         ├─ ← / prev button    → showLB(lbi − 1), wraps to the last image
         └─ Esc / × / backdrop → overlay closes, focus restored to the clicked frame
```

Arrow-key handling is scoped to only fire while the lightbox `.overlay` has the `open` class, so left/right arrows do not interfere with normal page scrolling elsewhere.

---

## 7. Testimonial carousel

```
Page load → autoQuote() starts a 6.5 s interval → goQuote(current + 1)
User clicks a dot
   → clearInterval on the existing timer
   → goQuote(selected index): track transform = translateX(-index × 100%)
   → aria-current updated on all dots
   → autoQuote() restarts the interval from the new position
```

The interval is cleared and restarted on every manual interaction rather than paused, so a visitor who has been reading a review isn't immediately interrupted by an auto-advance.

**Reduced motion:** `autoQuote()` exits immediately if `prefers-reduced-motion` is set — the carousel becomes manual-only, dots still function.

---

## 8. Theme switch

```
Toggle click
   └─ data-theme attribute flipped on <html> (light ⇄ dark)
      ├─ CSS token block swaps — every surface, border, and text colour repaints
      ├─ Icon path morphs sun ⇄ moon; aria-label updated to reflect the next action
      ├─ Preference written to localStorage["tv-theme"], wrapped in try/catch
      └─ MutationObserver watching data-theme fires
         └─ Hero sky, ridgelines, snow caps and treeline custom properties
            recalculated for the new theme (skyVars())
```

Resolution order at load is `localStorage` → `matchMedia("prefers-color-scheme: dark")` → light fallback. If `localStorage` is unavailable (private browsing, quota exceeded), the `try/catch` swallows the error and the page still renders correctly using the OS preference for that session.

---

## 9. Navigation and scroll state

```
Scroll event (passive listener) fires on every frame the browser allows
   ├─ nav gets .is-stuck once scrollY > 8          → border appears under the bar
   ├─ #totop gets .show once scrollY > 700          → back-to-top button fades in
   ├─ #progress width set to (scrollY / scrollable height) × 100%
   └─ scroll-spy: walk all <section id> elements,
        set "active" on the nav link whose section's offsetTop
        is the closest one at or above the current scroll position
```

```
Mobile burger tap
   → nav gains/loses .open class
   → aria-expanded and aria-label toggle together
   → drawer links each close the drawer on click, so a same-page
     anchor navigation doesn't leave the menu open over the destination
```

---

## 10. Newsletter subscribe

```
Footer form submit
   └─ email tested against emailRe
      ├─ invalid → field border reddens, focus moves to the field, nothing else happens
      └─ valid   → confirmation line shown below the form, input cleared
```

**Phase 2 change:** valid submissions call `POST /api/subscribe`, which upserts into a `subscribers` table and triggers a double opt-in confirmation email before the address is marked active — required for deliverability and for consent record-keeping under the DPDP Act / GDPR.

---

## 11. Cross-cutting flow: overlay lifecycle

Every modal in the system (booking, lightbox) shares one lifecycle, which is why the behaviour is consistent everywhere it appears:

```
openOverlay(el)
   ├─ lastFocus = document.activeElement
   ├─ el.classList.add("open")
   ├─ document.body.style.overflow = "hidden"
   └─ focus moves to the first input or button inside el

closeOverlay(el)
   ├─ el.classList.remove("open")
   ├─ document.body.style.overflow = ""
   └─ lastFocus.focus()

Global listeners:
   Esc key          → closes every open overlay
   backdrop click   → closes only the overlay that was clicked
```

---

## 12. End-to-end sequence — a typical visit

```
1. Land on Home         → hero animates in, trust stats visible
2. Use the search bar   → type "beach", set budget            → jump to Destinations
3. Apply a category     → tap "Beaches"                        → grid narrows further
4. Open a card          → "Book this trip" on Phuket           → modal opens
5. Fill the form        → name, email, a future date           → submit
6. See confirmation     → reference TV-4K9QP, seats held 48h   → close modal
7. Scroll to Gallery    → open a frame, arrow through a few     → close
8. Read a testimonial   → carousel auto-advances while reading
9. Reach Contact        → send a broader enquiry about a custom route
10. Subscribe           → footer newsletter form
11. Toggle dark theme   → whole page repaints, preference saved
```

Every step in this sequence is reachable by keyboard alone and produces an announced state change for assistive technology (inline error text, `aria-current`, `aria-expanded`, `aria-pressed`).

---

## 13. Phase 2 workflow additions

| New flow | Trigger | Outcome |
|---|---|---|
| Payment capture | Booking form valid submit | Payment intent created, 3-D Secure if required, webhook confirms |
| Availability check | Booking form valid submit, before payment | Live seat count checked against Redis cache backed by Postgres |
| Admin catalogue edit | CMS save | Webhook rebuilds/revalidates the affected page (ISR) |
| Abandoned booking | Modal closed without submitting, twice in a session | Optional exit-intent nudge, no data sent unless the user opts in |
| Email confirmation | Booking or enquiry created | Transactional email queued via Resend/SES, retried on failure |
| Rate limiting | Repeated enquiry/booking submissions from one IP | 429 response after threshold, CAPTCHA challenge shown |
