# API authorization matrix

Legend: **Public** = no token. **User** = valid access token; data is always filtered by `user_id = current user`. **Admin** = `users.role = 'admin'` read from the database (granted via `ADMIN_EMAILS`, the `python -m app.cli make-admin` command or another admin in *Admin → Users*; never from the client). **Signed** = short-lived HMAC-signed URL issued only inside the owner's API responses.

| Endpoint | Access | Ownership / notes | Rate limit |
|---|---|---|---|
| `POST /auth/register` | Public | Role always `user` unless e-mail is in `ADMIN_EMAILS` | 20/h per IP |
| `POST /auth/login` | Public | Same error for unknown e-mail and wrong password | 5 failures / 15 min per e-mail; 50 attempts / 15 min per IP |
| `GET /auth/me` | User | Own profile | — |
| `POST /auth/forgot-password` | Public | Generic response; token e-mailed, never returned; disabled in production without SMTP | 5/h per IP, 3/h per e-mail (silent) |
| `POST /auth/reset-password` | Public | Hashed, single-use, expiring token | 10/h per IP |
| `POST /auth/change-password` | User | Requires current password | — |
| `DELETE /auth/account` | User | Deletes own records and private files | — |
| `GET/PUT /profile`, `PUT /profile/notifications` | User | Own profile | — |
| `POST /profile/avatar` | User | Validated private upload | 20/h per user |
| `POST /contact` | Public | Returns receipt only, never stored messages | 5/h per IP |
| `GET /contact`, `GET/DELETE /contact/{id}` | **Admin** | — | — |
| `GET /analyses/tracks` | Public | Which analysis tracks are available, with a `reason` when a model is not installed | — |
| `POST /analyses/analyze` | User | Input gate + abstention; Model B only when enabled (else `track_not_available`) | 30/h per user; max 2 concurrent inferences per process |
| `POST /analyses` | User | `image_url` must already belong to the caller | — |
| `GET /analyses`, `GET /analyses/{id}` | User | Filtered by owner (404 otherwise) | — |
| `POST /scans/scan` | User | Own scans | 40/h per user |
| `GET /scans`, `GET /scans/{id}` | User | Owner only | — |
| `GET /ingredients…` | Public | Reference data, no personal data | — |
| `POST /progress` | User | Own images | 20/h per user |
| `GET /progress`, `/progress/summary`, `/progress/{id}` | User | Owner only | — |
| `POST /reports/generate` | User | Referenced analysis/progress must belong to the caller | — |
| `GET /reports`, `GET /reports/{id}/download` | User | Owner only; `Cache-Control: private, no-store` | — |
| `GET /history` | User | Owner only | — |
| `POST /chat`, `GET/DELETE /chat/history` | User | Owner only | 60/h per user |
| `GET /products`, `/products/meta`, `/products/{id}` | Public | Active products only; ingredient search | — |
| `GET /products/recommended` | User | Based on the caller's latest **facial** analysis only | — |
| `GET/POST/PATCH/DELETE /cart…` | User | Own cart only | — |
| `POST /orders`, `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel` | User | Own orders only; prices taken from the database; atomic stock reservation | 20 orders/h per user |
| `GET/POST/PUT/DELETE /admin/products…`, `POST /admin/products/{id}/image` | **Admin** | — | — |
| `GET /admin/orders`, `PATCH /admin/orders/{id}` | **Admin** | Order status and payment status (`unpaid → paid → refunded`) transitions are validated; cancelling restocks | — |
| `GET /admin/stats` | **Admin** | Aggregate counts and payment totals only | — |
| `GET /admin/users`, `PATCH /admin/users/{id}` | **Admin** | Change role (`user`/`admin`) or deactivate; an admin cannot demote or deactivate themselves | — |
| `POST /auth/google` | Public | Google ID token verified on the server (signature, audience, issuer, expiry, verified e-mail); 503 when `GOOGLE_CLIENT_ID` is empty | 50 per 15 min per IP |
| `POST /auth/set-password` | User | Only for accounts created with Google that have no password yet | — |
| `POST /profile/email` | User | Current password required; refused for Google-linked accounts and for addresses in `ADMIN_EMAILS` | 5/h per user |
| `GET /config` | Public | Clinic name, currency, time zone, Google client ID (public by design) | — |
| `GET /chat/capabilities` | User | Which assistant features are configured | — |
| `GET /doctors`, `/doctors/{id}`, `/doctors/{id}/slots` | User | Approved, active doctors only; licence number and e-mail are not included | — |
| `POST /doctors/apply`, `GET/PUT /doctors/me`, `PUT /doctors/me/availability` | User | Own doctor profile only; a new application is `pending` until an admin approves | 5 applications/day |
| `POST /appointments` | User | Books for the caller only; the time must be a free slot of the doctor; a shared analysis must belong to the caller; double booking is blocked by a unique slot lock | 6 bookings/day per user |
| `GET /appointments`, `/appointments/{id}`, `POST /appointments/{id}/cancel` | User | The patient of the appointment (404 otherwise); the treating doctor can also read it | — |
| `GET/POST /appointments/{id}/messages`, `GET /appointments/{id}/prescription.pdf` | User | Patient or treating doctor of that appointment only (404 otherwise) | 120 messages/h per user |
| `GET /doctor/appointments`, `PATCH /doctor/appointments/{id}`, `PUT /doctor/appointments/{id}/prescription`, `GET /doctor/patients` | **Doctor** (approved profile and `doctor` role, checked on every request) | Own appointments and own patients only; status changes follow `requested → confirmed → completed/no_show`; private notes are never returned to the patient or an admin | — |
| `GET /admin/doctors`, `PATCH /admin/doctors/{id}` | **Admin** | Approve, reject, suspend; the `doctor` role follows the approval | — |
| `GET /admin/appointments`, `PATCH /admin/appointments/{id}/payment` | **Admin** | No private notes, messages or shared photo; payment `unpaid → paid → refunded` | — |
| `GET /payments/methods`, `POST /payments/checkout` | User | Own unpaid order or appointment only; the amount comes from the database | 20 checkouts/h per user |
| `POST /payments/{id}/confirm`, `POST /payments/{id}/cancel` | User | Own payment only; the result is read from the provider, not from the browser | 60/h per user |
| `POST /payments/safepay/webhook` | **Safepay signature** | HMAC-SHA512 of the body with `SAFEPAY_WEBHOOK_SECRET`; only `payment.succeeded` for a tracker this server created is acted on; repeats change nothing | — |
| `GET/POST /payments/safepay/return` | Public | Forwards the browser to this site's own `/payment/return` page (fixed target, payment id checked against a pattern). Decides nothing: the page then calls `confirm` | — |
| `POST /payments/stripe/webhook` | **Stripe signature** | HMAC-SHA256 with `STRIPE_WEBHOOK_SECRET`, 5-minute tolerance; the session is re-read from Stripe before anything is marked paid | — |
| `GET /admin/payments` | **Admin** | Provider references and amounts; no card data exists | — |
| `GET/PUT /admin/settings`, `GET /admin/audit` | **Admin** | Run-time switches (disease screening, auto-publish); every change is audited | — |
| `POST /admin/connections/{name}/test` | **Admin** | One harmless request to an outside service with the configured key. Fixed provider addresses only; a key is never part of the answer | — |
| `/admin/automation…`, `/admin/posts…` | **Admin** | API keys (shown once, stored hashed), webhooks (URL checked against private addresses), agents, clinic posts | — |
| `GET /posts` | User | Published clinic posts only | — |
| `/automation/v1/…` | **API key** with the matching scope | A session token is not accepted here and an API key is not accepted anywhere else | 600/h per key |
| `GET /files/products/{name}` | Public | Product photos only (never user photos) | — |
| `GET /files/{folder}/{name}?exp&sig` | **Signed** | Signature bound to the exact path; expires after `SIGNED_URL_TTL_SECONDS` (900 s) | — |
| `GET /health`, `/health/live` | Public | Liveness only | — |
| `GET /health/ready` | Public | Dependency status booleans, model version; no paths or secrets | — |
| `/docs`, `/openapi.json` | Public in development, **disabled in production** | — | — |

Removed: the public static mount `GET /uploads/...`.
