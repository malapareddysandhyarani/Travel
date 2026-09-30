# TravelVista — Security Architecture

| | |
|---|---|
| **Product** | TravelVista — Travel & Tourism Website |
| **Version** | 1.0 |
| **Status** | Phase 1 (static site) delivered |
| **Owner** | Web Engineering |
| **Last updated** | September 2026 |

---

## 1. Scope and posture

Phase 1 is a static, client-only site: no server-side code of its own, no database, no session, no stored credentials, and no personal data at rest beyond a single non-sensitive `localStorage` key for theme preference. This document covers the threat model appropriate to that posture, the hardening that should be in place regardless, and the controls that become mandatory once Phase 2 introduces a backend, a database and payments.

The guiding principle throughout: **client-side validation in this build is a usability feature, not a security control.** Nothing that arrives from a browser is ever trusted once a server exists to receive it.

---

## 2. Phase 1 threat model

| Threat | Exposure today | Why | Control |
|---|---|---|---|
| Cross-site scripting (XSS) | Low | All rendered values come from a static in-file catalogue, never from user input, a URL parameter, or a third-party response | User input is only ever read (`.value`), never interpolated into `innerHTML`; confirmation messages echo user text via `textContent`, not markup concatenation |
| DOM clobbering / prototype pollution | Low | No `eval`, no `Function` constructor, no dynamic `<script>` injection anywhere in the codebase | All logic runs inside one IIFE in strict mode |
| Clickjacking | Medium | The site could be framed by a malicious page to hijack clicks on booking/contact buttons | `X-Frame-Options: DENY` and `frame-ancestors 'none'` at the CDN |
| Transport interception | Medium | Form data (name, email, phone) travels in the clear if HTTPS isn't enforced | HTTPS-only delivery, HSTS with preload |
| Third-party compromise | Low | One external origin in use: Google Fonts | Restrictive CSP scoped to that origin only; self-hosting removes it entirely |
| Local storage tampering | Very low | The only key stored is a theme preference (`tv-theme`) | No security or business decision depends on its value; all reads wrapped in `try/catch` so a corrupted or blocked value never breaks rendering |
| Supply chain | Very low | Zero npm dependencies, zero build tooling | Kept intentionally — every dependency added is a future patch obligation |

**What is explicitly out of scope for Phase 1** because the surface doesn't exist yet: authentication attacks, session hijacking, SQL/NoSQL injection, payment fraud, and server-side request forgery. These become in-scope the moment Phase 2 ships (§6).

---

## 3. Recommended response headers

These should sit at the CDN/edge layer regardless of phase:

```
Content-Security-Policy: default-src 'self';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src  'self' https://fonts.gstatic.com;
  img-src   'self' data:;
  script-src 'self';
  connect-src 'self' https://api.travelvista.example;
  frame-ancestors 'none'; base-uri 'self'; form-action 'self'

Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()
```

**Known caveat:** the single-file build inlines `<style>` and `<script>`, which requires `'unsafe-inline'` in `style-src` and (implicitly, if not tightened) in `script-src`. This is the single highest-value hardening step before a public launch — extract both to external files (or apply a nonce/hash per deploy) and drop `'unsafe-inline'` from `script-src` entirely. `style-src 'unsafe-inline'` is a lower-severity trade-off and can remain if extraction of CSS isn't prioritised immediately.

| Header | Purpose |
|---|---|
| `Content-Security-Policy` | Whitelists exactly which origins may supply scripts, styles, fonts and images; blocks inline script execution from injected content |
| `Strict-Transport-Security` | Forces HTTPS for all future visits, including subdomains, and qualifies for browser preload lists |
| `X-Content-Type-Options: nosniff` | Stops the browser from guessing a MIME type and executing a file as something it isn't |
| `Referrer-Policy` | Limits how much of the current URL leaks to destinations the site links out to |
| `Permissions-Policy` | Explicitly denies browser features the site never uses, closing off unused attack surface |

---

## 4. Input validation

### 4.1 Client-side rules (Phase 1, usability layer)

| Field | Rule |
|---|---|
| Name | ≥ 2 characters |
| Phone | `/^[+\d][\d\s-]{7,}$/` |
| Email | `/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i` |
| Message | ≥ 10 characters |
| Departure date | Present and strictly later than today |

These exist to give the visitor immediate, specific feedback — a red border and a sentence explaining what to fix, with focus moved to the first invalid field. They prevent nothing from a security standpoint, because a request can always be sent directly to an endpoint bypassing the browser entirely.

### 4.2 Server-side rules (mandatory from Phase 2 onward)

Every rule above must be re-implemented server-side, plus:

- **Schema validation** on the full payload shape (reject unexpected fields rather than silently dropping them).
- **Output encoding** wherever a submitted value is later rendered anywhere (an admin dashboard, an email template) — the risk moves from the public site to internal tooling if this is skipped.
- **Length ceilings**, not just floors, on every free-text field to bound storage and email payload size.
- **Allow-list validation** for enum-like fields (traveller count, month) rather than trusting the client's `<select>` to have constrained the value.

---

## 5. Data classification

| Data | Classification | Where it lives in Phase 1 | Where it lives in Phase 2 |
|---|---|---|---|
| Theme preference | Non-sensitive | `localStorage`, this browser only | Same |
| Name, email, phone (enquiry/booking forms) | Personal data | Nowhere — never transmitted | Postgres, encrypted at rest |
| Trip preferences, budget, dates | Personal data | Nowhere | Postgres |
| Payment details | Sensitive / regulated | N/A — no payment exists | Never touches our servers; handled entirely by the gateway's hosted fields (§6.4) |
| Booking reference | Non-sensitive, session-scoped | Generated client-side, not persisted | Generated server-side, persisted, unique |

---

## 6. Phase 2 controls

### 6.1 Transport and network

- TLS 1.3 with automatic certificate rotation.
- HSTS preload, no plaintext HTTP fallback at any hop.
- Strict CORS allow-list — the API accepts requests only from the production and staging site origins, never `*`.

### 6.2 API layer

- Schema validation (e.g. Zod or JSON Schema) on every request body before it reaches business logic.
- Parameterised queries or an ORM (Prisma) exclusively — no string-built SQL, anywhere, ever.
- Consistent error shapes that never leak stack traces, internal paths, or library versions to the client.

### 6.3 Abuse prevention

| Control | Applied to |
|---|---|
| Rate limiting (10 requests/hour/IP as a starting point) | Enquiry and booking endpoints |
| Honeypot field (hidden, bots fill it, humans don't) | Contact and newsletter forms |
| CAPTCHA challenge after repeated submissions | Contact, booking, newsletter |
| Request size limits | All POST endpoints |

### 6.4 Payments

- **PCI-DSS SAQ-A scope**: card data is entered directly into gateway-hosted fields (Razorpay/Stripe Elements) and never transits our servers in any form — this is what keeps the compliance burden to the lightest self-assessment tier.
- Payment confirmation is driven by **verified webhook signatures** from the gateway, never by trusting a client-side "payment succeeded" callback.
- Idempotency keys on booking creation, so a retried request or a double-click cannot create two charges.

### 6.5 Authentication (admin console only — the public site has no user accounts)

- Password hashing with **Argon2id**.
- Short-lived JWT access tokens plus rotating refresh tokens.
- **Mandatory MFA** for any account with catalogue-edit or booking-data access.
- Session cookies: `HttpOnly; Secure; SameSite=Strict`.
- Anti-CSRF token required on every state-changing admin route.

### 6.6 Data protection

- **AES-256 at rest** for the database.
- **Field-level encryption** for phone numbers and any field classified as personal data beyond what's needed for basic display.
- **24-month retention** on enquiry records, after which they are purged unless converted to a booking or an active subscriber.
- Backups encrypted with a separate key from the primary database.

### 6.7 Privacy and regulatory compliance

- **DPDP Act 2023** (India) and **GDPR** (for any EU visitor) both apply given the international traveller base:
  - Explicit, separately-recorded consent before adding an email to marketing (the footer newsletter is a double opt-in, not a single checkbox that also submits an enquiry).
  - A documented data export endpoint and a data erasure endpoint, both actionable on request.
  - A public list of data processors (payment gateway, email provider, hosting) in the privacy policy.
  - A lawful basis recorded for every category of data collected.

### 6.8 Monitoring and audit

- Centralised, append-only audit log for every booking mutation (created, modified, cancelled, refunded) — who, what, when.
- Alerting on abnormal 4xx/5xx rate spikes on the API gateway.
- Dependency vulnerability scanning in CI (e.g. `npm audit` / Dependabot) on every merge to main, blocking on high-severity findings.
- Structured logging with PII redaction — request logs never contain full email addresses or phone numbers in plaintext.

---

## 7. Dependency and supply-chain posture

Phase 1 has **zero npm dependencies** and **one external origin** (Google Fonts), so the supply-chain surface is effectively limited to the CDN provider and that single font host. This is a deliberate constraint, not an oversight — it should be preserved for as long as the product's complexity allows. Every dependency introduced in Phase 2 should be evaluated against:

1. Is there a zero-dependency or standard-library way to do this?
2. What is the maintainer's release cadence and issue-response history?
3. Does it pull in a deep transitive tree, or is it self-contained?

---

## 8. Incident response readiness (Phase 2)

| Element | Requirement |
|---|---|
| Ownership | A named on-call rotation for the API and payment paths |
| Detection | Alerting wired to the monitoring stack in §6.8, not just dashboards someone might check |
| Containment | Ability to revoke a compromised API key or rotate database credentials without a full redeploy |
| Disclosure | A documented process and timeline for notifying affected users, consistent with DPDP/GDPR breach-notification windows |
| Post-incident | A blameless retrospective for any incident that touches personal data or payments |

---

## 9. Security checklist before public launch

- [ ] Extract inline `<style>`/`<script>` and tighten CSP to remove `'unsafe-inline'` from `script-src`
- [ ] Confirm HSTS preload submission
- [ ] Self-host fonts or confirm the Google Fonts CSP scope is minimal
- [ ] Penetration test scoped to the API once Phase 2 endpoints exist
- [ ] Verify webhook signature checks on the payment integration before enabling live payments
- [ ] Confirm rate limiting is active on enquiry, booking and newsletter endpoints
- [ ] Publish a privacy policy naming every data processor
- [ ] Verify data export and erasure endpoints function end-to-end
