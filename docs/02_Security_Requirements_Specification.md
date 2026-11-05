# Skyntri — Security Requirements Specification (SRSec)

**Version:** 1.0 draft  
**Date:** 31 October 2026  
**Status:** Requirements baseline; implementation and verification pending.

## 1. Purpose

Define mandatory security, privacy, and operational controls for Skyntri before public deployment. Skyntri processes user accounts, skin photographs, analysis history, ingredient scans, progress comparisons, chat, and generated reports. Skin photographs and associated records must be treated as sensitive personal data.

## 2. Security objectives

- Confidentiality: users can access only their own records and files.
- Integrity: users cannot alter another user's data or model outputs.
- Availability: uploads and inference cannot easily exhaust service resources.
- Accountability: security-relevant actions are logged without unnecessarily collecting sensitive content.
- Safety: unsupported images and uncertain predictions result in safe abstention, not fabricated skin-condition labels.
- Recoverability: database and object data can be restored.

## 3. Identity and access control

**SEC-AUTH-001:** All private API endpoints shall require authenticated access.  
**SEC-AUTH-002:** Every data query shall be scoped to the authenticated user unless an explicitly authorized administrator operation is being performed.  
**SEC-AUTH-003:** The system shall implement server-enforced roles/permissions for administrative operations. A frontend-only admin flag is prohibited.  
**SEC-AUTH-004:** Contact-message listing, user management, operational dashboards, and administrative exports shall be admin-only.  
**SEC-AUTH-005:** Passwords shall be stored using a current, appropriately configured password hashing algorithm (bcrypt or Argon2id), never plaintext or reversible encryption.  
**SEC-AUTH-006:** Login and password-reset endpoints shall be rate-limited.  
**SEC-AUTH-007:** Password-reset tokens shall be random, single-use, short-lived, stored hashed, and delivered through a verified channel. Tokens shall never appear in production API responses or logs.  
**SEC-AUTH-008:** Production startup shall fail if JWT signing secrets are missing, weak, or equal to known development placeholders.  
**SEC-AUTH-009:** Tokens shall have explicit expiry and validated issuer/audience/algorithm policy where applicable.  
**SEC-AUTH-010:** Logout/session revocation behavior and refresh-token policy shall be documented and tested.

## 4. Authorization and tenant isolation

**SEC-ACL-001:** Analysis, scan, progress, report, chat, profile, and uploaded-object reads shall enforce owner checks on the server.  
**SEC-ACL-002:** Object identifiers shall not be treated as authorization. UUIDs are not a substitute for access control.  
**SEC-ACL-003:** Cross-user IDOR tests shall be included for every resource endpoint.  
**SEC-ACL-004:** Admin privilege shall be granted only through trusted server-side data/configuration and protected administrative workflows.  
**SEC-ACL-005:** Public contact submission shall not grant access to contact-message records.

## 5. Data protection and privacy

**SEC-DATA-001:** All production traffic shall use HTTPS.  
**SEC-DATA-002:** Skin images and generated reports shall be private by default.  
**SEC-DATA-003:** Private files shall be served through authenticated ownership-checked endpoints or short-lived signed URLs.  
**SEC-DATA-004:** The application shall not expose the uploads directory as a public static directory for private user content.  
**SEC-DATA-005:** The system shall define data retention, account deletion, image deletion, and backup retention policies.  
**SEC-DATA-006:** Logs shall not contain passwords, JWTs, reset tokens, API keys, raw skin images, or unnecessary personal data.  
**SEC-DATA-007:** Secrets shall be stored in deployment environment/secret management, not committed to Git.  
**SEC-DATA-008:** User-facing privacy notice shall explain what is collected, why, storage/retention, third-party AI processing, and deletion options.  
**SEC-DATA-009:** If external LLM/OCR/AI services receive user data, the exact data sent and provider retention/processing terms shall be reviewed and disclosed.

## 6. Upload and inference protection

**SEC-UP-001:** Enforce maximum request size at proxy/platform and application layers.  
**SEC-UP-002:** Allow only explicitly supported raster image formats.  
**SEC-UP-003:** Validate file signatures and successfully decode the image; do not trust filename extension or client MIME type.  
**SEC-UP-004:** Enforce maximum width, height, total pixel count, and processing time.  
**SEC-UP-005:** Generate random server-side object names; prevent path traversal and filename injection.  
**SEC-UP-006:** Reject corrupt, animated, unsupported, or suspicious files according to the supported-format policy.  
**SEC-UP-007:** Limit concurrent model inference and queue/backpressure requests.  
**SEC-UP-008:** Clean temporary files after success and failure.  
**SEC-UP-009:** Use private storage with encryption at rest where supported and least-privilege credentials.  
**SEC-UP-010:** Validate ownership before file download, replacement, or deletion.

## 7. Model safety requirements

**SEC-ML-001:** The inference pipeline shall run image-quality checks before prediction.  
**SEC-ML-002:** A dedicated skin-vs-non-skin gate shall determine whether an image is eligible for skin analysis.  
**SEC-ML-003:** The system shall include a validated OOD/uncertainty policy; raw class confidence alone shall not be treated as proof that an input is in-distribution.  
**SEC-ML-004:** Non-skin, low-quality, and uncertain inputs shall be rejected/abstained with actionable user guidance.  
**SEC-ML-005:** The condition classifier shall not run when the input gate rejects the image.  
**SEC-ML-006:** Every model artifact shall have a version, checksum, training dataset/version, label mapping, preprocessing specification, and evaluation report.  
**SEC-ML-007:** Training/validation/test splits shall avoid patient/person/source leakage where identifiable.  
**SEC-ML-008:** Evaluation shall include per-class precision, recall, F1, confusion matrices, calibration, class support, and subgroup analysis where ethically and legally appropriate.  
**SEC-ML-009:** Report coverage, false-accept rate for non-skin images, and valid-skin rejection rate for the input gate.  
**SEC-ML-010:** User-facing copy shall describe outputs as AI estimates/decision support, not a diagnosis. The product shall recommend qualified medical care for concerning or persistent symptoms.

## 8. Application and infrastructure hardening

**SEC-APP-001:** Configure restrictive CORS allowlists for known frontend origins; do not use wildcard origins with credentials.  
**SEC-APP-002:** Configure secure headers including CSP where applicable, HSTS at HTTPS edge, `X-Content-Type-Options`, and frame protections.  
**SEC-APP-003:** Validate all API inputs using explicit schemas, field lengths, and allowed values.  
**SEC-APP-004:** Return generic client errors; do not expose stack traces, secrets, SQL, filesystem paths, or internal model details.  
**SEC-APP-005:** Add shared rate limits for login, reset, contact, upload, OCR, chat, and inference.  
**SEC-APP-006:** Pin and regularly scan dependencies; remove unused packages.  
**SEC-APP-007:** Use Alembic migrations; do not rely on automatic production schema creation as the migration process.  
**SEC-APP-008:** Separate liveness and readiness checks.  
**SEC-APP-009:** Use structured logs, error monitoring, and alerts without sensitive payloads.  
**SEC-APP-010:** Back up the database and verify restore procedures.

## 9. Medical-AI safety and product recommendation requirements

**SEC-MED-001:** Facial skin-concern analysis and skin-disease screening shall be separate model tasks with separate approved label taxonomies, datasets, thresholds, model cards and evaluation reports.  
**SEC-MED-002:** The skin-disease model may cover supported facial and body sites; it shall not be described as a body-only model.  
**SEC-MED-003:** Disease labels (including eczema, psoriasis, fungal/infectious conditions and suspicious lesions) shall not be enabled until dataset provenance, licensing/consent, annotation quality, representative test coverage and qualified dermatology review are documented.  
**SEC-MED-004:** Skin-cancer-related functionality shall be risk-flagging/referral support only unless a separately approved clinical/regulatory pathway establishes otherwise. It shall not diagnose cancer, rule out cancer, or reassure users to delay assessment.  
**SEC-MED-005:** A negative or uncertain image result shall not override concerning symptoms or user-reported changes; provide appropriate professional-care guidance.  
**SEC-MED-006:** Disease-model evaluation shall report class-specific sensitivity, specificity, false-negative analysis, calibration, confidence intervals and independent external validation; overall accuracy alone is insufficient.  
**SEC-MED-007:** User-facing output shall distinguish facial cosmetic/appearance concerns from disease-screening support and state the model's scope and limitations.  
**SEC-PROD-001:** Product recommendations shall use verified product/ingredient data and display source and price freshness where price data is shown.  
**SEC-PROD-002:** The system shall not fabricate prices, availability, seller links, ingredients, product authenticity or evidence. Stale/unavailable data shall be labelled or omitted.  
**SEC-PROD-003:** Recommendations shall consider user budget and stated preferences, disclose suitability caveats and avoid guaranteed safety/efficacy claims.  
**SEC-PROD-004:** Product recommendations shall not replace professional care or recommend prescription treatment; concerning lesions or severe/worsening symptoms shall trigger medical-care guidance.  
**SEC-PROD-005:** Sponsored placement, if ever introduced, shall be clearly disclosed and shall not be disguised as an independent clinical ranking.

## 10. Verification requirements

Each security requirement shall map to one or more automated tests or documented manual checks. Release pipeline shall include:
- Unit and API tests.
- Authentication/authorization and cross-user IDOR tests.
- Upload validation tests.
- Dependency vulnerability scan.
- Secret scan.
- Static analysis/lint.
- Container build and smoke test.
- Database migration test.
- Model/OCR readiness and inference smoke test.
- Non-skin/OOD evaluation suite.

## 11. Release gate

A release is blocked by any open Critical finding, any untested cross-user data access path, public exposure of private images/reports, default production secrets, reset-token leakage, or a model pipeline that confidently emits condition labels for known non-skin inputs.

## Appendix — verification status (31 October 2026)

| Requirement(s) | Status | Evidence |
|---|---|---|
| SEC-AUTH-001/002, SEC-ACL-001..003 | Implemented | Owner-filtered queries; IDOR tests in `test_security_integration.py`, `test_security_hardening.py` |
| SEC-AUTH-003/004, SEC-ACL-004/005 | Implemented | `users.role`, `require_admin`, `ADMIN_EMAILS`; contact tests |
| SEC-AUTH-005 | Implemented (pre-existing) | bcrypt, cost 12 |
| SEC-AUTH-006, SEC-APP-005 | Implemented | `services/rate_limit.py` (database-backed) |
| SEC-AUTH-007 | Implemented | Hashed, single-use, 30-min tokens; e-mail only |
| SEC-AUTH-008/009 | Implemented | `validate_for_startup`; iss/aud/iat/typ/exp validation |
| SEC-AUTH-010 | Partial | 30-min access tokens, no refresh tokens, logout clears client token; server-side revocation not implemented |
| SEC-DATA-002/003/004, SEC-UP-010 | Implemented | Private storage + signed URLs; reports owner-checked |
| SEC-DATA-005 | Partial | Account deletion removes files; retention policy documented in the runbook; privacy notice pending |
| SEC-DATA-006/007 | Implemented | JSON logs with no tokens or passwords; `.env` ignored; gitleaks in CI (not run here) |
| SEC-DATA-001, 008, 009 | Open | HTTPS at hosting edge; privacy notice; LLM provider disclosure |
| SEC-UP-001..006, 008 | Implemented | `services/uploads.py`, request-size middleware; `test_upload_security.py` |
| SEC-UP-007 | Implemented | Per-process inference semaphore + per-user limit |
| SEC-UP-009 | Depends on host | Use an encrypted volume or bucket |
| SEC-ML-001..005 | Implemented with an interim heuristic gate | `services/image_gate.py`; `test_input_gate.py` |
| SEC-ML-006 | Partial | Model card with version and checksum; dataset card pending |
| SEC-ML-007/008 | Open | Requires reproducing training/evaluation |
| SEC-ML-009 | Partial | `scripts/evaluate_input_gate.py`; sample results only (not held-out) |
| SEC-ML-010, SEC-MED-007 | Implemented | UI and API wording; track label on results |
| SEC-MED-001..006 | Implemented as "Model B not released" | `track_not_available` |
| SEC-APP-001/002/003/004 | Implemented | CORS allowlist, security headers, schemas, generic errors |
| SEC-APP-006 | Implemented | Pinned requirements; pip-audit/npm audit in CI |
| SEC-APP-007 | Implemented | Alembic baseline + 0002 |
| SEC-APP-008/009 | Implemented | `/health`, `/health/ready`, structured logs |
| SEC-APP-010 | Documented, not tested | `docs/DEPLOYMENT_RUNBOOK.md` |
| SEC-PROD-001..005 | Not started | Product feature blocked by the release gate |
