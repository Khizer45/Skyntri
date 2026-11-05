# Threat model (summary)

## Assets
* Skin photographs, analysis history, progress images, PDF reports (sensitive personal/health-adjacent data).
* Account credentials, reset links, access tokens, `SECRET_KEY`, SMTP/LLM API keys.
* Contact messages (names, e-mails, free text).
* Model artifacts and their integrity (wrong model = wrong advice).

## Trust boundaries
1. Browser ↔ API (HTTPS; untrusted input, bearer token).
2. API ↔ database (PostgreSQL in production).
3. API ↔ private file storage (persistent volume / object storage).
4. API ↔ external providers (SMTP, optional Gemini/OpenAI).
5. Build/CI ↔ deployment (secrets, images).

## Attacker scenarios and mitigations

| Scenario | Mitigation | Status |
|---|---|---|
| Anonymous user reads contact messages | Admin-only endpoints, server-side role | Fixed |
| Account takeover via reset token in API response | Token only e-mailed, hashed at rest, single-use, 30 min | Fixed |
| Forged JWT using default secret | Production refuses weak/default secrets; iss/aud/typ/exp checked | Fixed |
| Guessing/scraping image URLs | No public mount; signed, expiring, path-bound URLs | Fixed |
| User A reads user B's records (IDOR) | Every query filtered by owner; tests for analyses, reports, progress, scans, files | Fixed (keep adding tests for new endpoints) |
| Malicious upload (polyglot, bomb, SVG, huge image) | Decode-based validation, pixel/size caps, random names, body-size limit | Fixed |
| Brute force / credential stuffing | DB-backed rolling limits per e-mail and IP, constant-ish timing | Fixed |
| Inference DoS | Per-user limits, concurrency cap, one worker | Partial (measure on host) |
| XSS stealing the token from localStorage | React escaping, production CSP, short token life | Partial (cookie sessions planned) |
| Misleading medical output on non-skin/uncertain images | Input gate + abstention; Model B disabled | Partial (heuristic gate) |
| Secrets committed to Git | `.gitignore`, `.dockerignore`, gitleaks in CI | Configured, not run here |
| Data loss on redeploy | Persistent private volume, DB backups, restore drill | Documented, not tested here |
| Personal data sent to LLM provider | LLM disabled by default; disclosure needed before enabling | Open |
