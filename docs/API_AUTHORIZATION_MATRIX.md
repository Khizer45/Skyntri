# API authorization matrix

Legend: **Public** = no token. **User** = valid access token; data is always filtered by `user_id = current user`. **Admin** = `users.role = 'admin'` read from the database (granted via `ADMIN_EMAILS` or a DB update, never from the client). **Signed** = short-lived HMAC-signed URL issued only inside the owner's API responses.

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
| `GET /analyses/tracks` | Public | Which analysis tracks are available | — |
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
| `GET /admin/orders`, `PATCH /admin/orders/{id}` | **Admin** | Status transitions are validated | — |
| `GET /files/products/{name}` | Public | Product photos only (never user photos) | — |
| `GET /files/{folder}/{name}?exp&sig` | **Signed** | Signature bound to the exact path; expires after `SIGNED_URL_TTL_SECONDS` (900 s) | — |
| `GET /health`, `/health/live` | Public | Liveness only | — |
| `GET /health/ready` | Public | Dependency status booleans, model version; no paths or secrets | — |
| `/docs`, `/openapi.json` | Public in development, **disabled in production** | — | — |

Removed: the public static mount `GET /uploads/...`.
