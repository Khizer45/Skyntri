# MASTER PROMPT — Skyntri Secure Hardening, Model Upgrade & Product Expansion

You are a senior full-stack engineer, application-security engineer, ML engineer, MLOps engineer, QA lead, and technical writer working on the EXISTING Skyntri repository.

Repository: https://github.com/Khizer45/Skyntri  
Known reviewed commit: `a2f08db41ab045cd2618156c5962a768204782b5`  
Stack observed: React + Vite frontend; FastAPI backend; SQLAlchemy; SQLite configuration with PostgreSQL support/configuration; TensorFlow/Keras EfficientNetB0; pytesseract/Tesseract; OpenCV progress comparison.

## 0. Non-negotiable working rules

1. Audit the latest repository/ZIP before editing. Do not assume the repository has not changed since the known commit.
2. Preserve all existing features and user workflows. Do not rebuild from scratch, remove functionality, or make broad architectural changes without evidence.
3. Work on a new feature/hardening branch. Never directly overwrite `main`.
4. Do not push or merge without explicit user approval.
5. Never commit `.env`, secrets, tokens, private datasets, user uploads, local databases, virtual environments, or generated artifacts that should not be versioned.
6. Do not invent test results, dataset licenses, model metrics, security fixes, or deployment success.
7. Make small, reviewable changes. For each change, explain the reason, affected files, backward compatibility, and tests.
8. Before changing authentication/session behavior or database schema, inspect all frontend/backend consumers and provide a migration/rollback plan.
9. If repository write access is unavailable, produce exact replacement files/patches and local commands; do not claim changes were committed.
10. Do not add new product features until existing features pass the secure deployment gate.

## 1. Project context and known model issue

Skyntri currently has:
- Authentication and profile.
- Skin-image analysis and history/dashboard.
- Ingredient OCR scanner and ingredient database.
- OpenCV-based progress comparison.
- Chat assistant/fallback.
- PDF reports.
- Contact/help messages.
- React/Vite frontend and FastAPI backend.

Current model work previously documented:
- EfficientNetB0, ImageNet initialization, 224×224 input.
- 10 sigmoid outputs / multi-label prediction.
- Dataset described as Roboflow Skin-Problem-MultiLabel, reported 4,828 images.
- Labels recorded: Acne, Blackheads, Dark Spots, Dry Skin, Eye Bags, Normal, Oily, Pores, Redness, Wrinkles.
- Previously reported metrics: subset accuracy 71.52%, micro F1 81.17%, macro F1 66.73%, weighted F1 81.41%, Hamming loss 4.03%. These are historical reported metrics only. Reproduce and verify against exact artifact, data split, preprocessing, and evaluation code before reusing them.

Critical observed product issue:
- User uploads non-skin images such as technology/electronics or other unrelated objects.
- Current model still emits labels such as acne or other skin problems.
- This is an out-of-distribution (OOD) failure. A multi-label sigmoid model will always produce scores for its known labels; thresholds alone are not a valid non-skin detector.

## 2. Phase 0 — Repository discovery and baseline

Before editing:
- Inspect complete file tree, latest commit, branch state, uncommitted changes, environment examples, deployment config, requirements, frontend API layer, all routers/services/schemas/models, upload paths, and tests.
- Identify exact model artifacts, label maps, preprocessing, inference path, dataset references, and training notebooks/scripts.
- Trace every frontend feature to its API endpoints and database models.
- Map all endpoints to authentication, authorization, ownership, validation, rate limits, and sensitive data.
- Run existing tests/build/lint if environment allows; record exact commands and outputs.
- Establish baseline screenshots/API behavior for existing features.
- Produce a gap list and implementation plan before editing.

## 3. Phase 1 — Security and deployment hardening (first priority)

Use the accompanying `01_Security_Audit_Report.md` and `02_Security_Requirements_Specification.md` as the requirements baseline. Verify every finding against current code; mark each as confirmed, not reproduced, or needs further investigation.

### Must address
A. Contact messages:
- Public contact submission may remain public with validation/rate limiting.
- Contact message listing/detail/update/delete must be admin-only.
- Add server-side roles/permissions and tests proving ordinary users cannot access messages.

B. Password reset:
- Remove any development reset token from production API response.
- Use random single-use short-lived tokens, hashed at rest, delivered via verified email.
- Generic response to prevent account enumeration.
- If email is not configured, disable reset in production safely.
- Add rate limits and replay/expiry tests.

C. JWT and secrets:
- Remove insecure production default.
- Validate secret strength on production startup.
- Validate expiry and token claims.
- Keep all secrets out of source control and logs.
- Document exact environment variables.

D. Private file storage:
- Stop publicly serving private user uploads/reports as static files.
- Use private object storage or a documented persistent private volume.
- Add authenticated owner-checked download/delete endpoints or short-lived signed URLs.
- Random object keys; validate decoded image bytes, actual format, dimensions, pixel count, size, and allowed formats.
- Clean temporary files on failures.
- Add cross-user access tests.

E. Rate limiting:
- Replace per-process in-memory login failure counter with shared Redis/database-backed rate limiting suitable for multiple workers.
- Apply limits to login, reset, contact, upload, OCR, chat, and inference.
- Avoid account-lockout denial-of-service.

F. Dependencies and startup:
- Add pinned compatible `opencv-python-headless` because progress service imports `cv2`.
- Install OS-level `tesseract-ocr` in container; `pytesseract` alone is insufficient.
- Verify TensorFlow version, NumPy compatibility, Python version, model artifact path, and clean install.
- Avoid multiple workers loading duplicate model copies until memory tests justify it.

G. Database and operations:
- Introduce Alembic migrations and test existing DB migration.
- Separate liveness and readiness.
- Readiness checks DB, model artifact/load state, OCR executable, and storage.
- Add structured logs, safe error responses, monitoring, backups, and restore test.
- Configure restrictive CORS and secure headers.
- Add CI for lint, tests, dependency scan, secret scan, and container build.

H. Security tests:
- Authentication and authorization.
- Cross-user IDOR for analysis, scans, progress, reports, chat, profile, and files.
- Upload abuse/malformed images.
- Contact access control.
- Reset-token expiry/replay.
- Rate limits.
- No secrets in logs/responses.
- Database migration and restore.

Do not declare secure until Critical and High issues are remediated and verified.

## 4. Phase 2 — Fix non-skin image predictions

Design a staged inference pipeline. Do not simply add a few `if confidence < threshold` checks to the existing classifier.

Pipeline:
1. Upload security validation and decode.
2. Image quality assessment (blur, brightness, dimensions, usable crop).
3. Skin-vs-non-skin eligibility classifier.
4. OOD/uncertainty detection calibrated on held-out data.
5. Scope selection (facial vs body/general skin).
6. Specialist condition model inference.
7. Calibrated per-class thresholds and safe abstention.
8. Persist result with model/gate versions and reason codes.

### Eligibility model
Train a separate skin-image / non-skin-image classifier. Include diverse positive skin photos and hard negatives:
- Phones, laptops, computers, keyboards, screens, electronics.
- Buildings, rooms, furniture, roads, vehicles.
- Documents, text pages, charts, screenshots.
- Food, plants, animals, landscapes, clothing.
- Illustrations, cartoons, synthetic textures, random patterns.
- Other likely mistaken uploads.

Ensure data licenses and permitted uses are verified. Split by source/person where possible. Include a held-out hard-negative test set not used for tuning.

### Abstention behavior
- If non-skin: do not run condition classifier; show “This image does not appear to be a skin photo. Please upload a clear skin image.”
- If too blurry/dark/poor quality: show actionable retake guidance.
- If uncertain/OOD: show “We cannot confidently analyze this image. Please upload another photo.”
- If body/facial scope unsupported: explain supported scope; do not force a prediction.
- Never show acne/condition labels for a rejected image.

### Metrics
Report:
- Non-skin false-accept rate.
- Valid-skin rejection rate.
- Sensitivity/specificity and precision/recall.
- ROC/PR curves where appropriate.
- Calibration and confidence intervals.
- Results by negative category and relevant data subgroups.
- End-to-end coverage vs accuracy tradeoff.

Set numerical launch thresholds with the product owner after baseline evaluation. Do not invent target performance before measuring.

## 5. Phase 3 — Build two distinct AI analysis tracks

Follow the corrected `03_Product_Requirements_Specification.md`. Do not implement the earlier “facial visible conditions vs body diseases” split.

### Model A — Facial skin concerns
- Face-only concerns such as acne, blackheads, dark spots, pores, wrinkles, oily/dry appearance, redness and eye bags, only where supported by verified data.
- These are facial appearance/skin-care concerns; do not present pores, oiliness, wrinkles or dryness as diagnosed diseases.
- Do not use this model to diagnose cancer, eczema, psoriasis or other skin diseases.

### Model B — Skin disease screening support (face and body)
- A separate model/task for supported skin diseases that may occur on the face or body. It is not body-only.
- Candidate research classes include eczema/atopic dermatitis, psoriasis, selected dermatitis/fungal/infectious conditions, and suspicious lesions / possible skin-cancer-related patterns.
- Enable each class only after verifying licensing/consent, label quality, class coverage, clinical taxonomy, independent external testing and qualified dermatology review.
- Skin cancer: never claim to diagnose or rule out cancer. If included, it is a cautious risk-flag/referral-support pathway; negative results must not reassure users to delay professional assessment. Photo-only AI cannot replace dermoscopy, examination or biopsy.
- Do not promise all candidate conditions at launch. Exclude classes that cannot be reliably distinguished.

### Shared pipeline and governance
- Keep secure upload validation, image quality, skin/non-skin eligibility and OOD/uncertainty checks ahead of both models.
- Route to the selected/appropriate analysis track only after eligibility and scope checks; abstain on uncertain inputs.
- Maintain separate datasets, labels, preprocessing, thresholds, artifacts, model cards, evaluation reports and rollback paths.
- Evaluate disease classes with sensitivity, specificity, false-negative review, calibration, confidence intervals and external validation, not accuracy alone.
- Clearly distinguish facial skin-care concerns from disease-screening support in UI, API, history and PDF reports.
- Preserve historical records and record the model/task version used.

## 6. Phase 4 — Existing feature quality

Improve, do not remove:
- Ingredient OCR: OCR confidence, corrections, unknown ingredient handling, ingredient evidence/sources, clear distinction between OCR accuracy and safety assessment.
- Progress comparison: label as approximate visual comparison; give same lighting/distance/angle guidance; avoid medical claims.
- Chat: safe non-diagnostic responses, protect history, rate-limit external calls, handle provider failure.
- Reports: private access, owner checks, model version, date, limitations, non-diagnostic disclaimer.
- Profile: validate avatar upload and ownership; secure private profile data.
- History/dashboard: preserve compatibility with old records and model versions.
- Contact: public submit, admin-only management.

## 7. Phase 5 — Deployment readiness

Use a simple architecture first:
- React/Vite frontend on a static hosting platform.
- FastAPI backend in a Docker container.
- Managed PostgreSQL.
- Private object storage/persistent storage for images and reports.
- TensorFlow inference within backend initially unless measurements justify separation.
- Tesseract installed in the backend image.

Create:
- Production Dockerfile and `.dockerignore`.
- Safe `.env.example` with placeholders only.
- Alembic migrations.
- CI pipeline.
- Health/readiness endpoints.
- Backup/restore instructions.
- Deployment runbook and rollback instructions.
- Resource profile for CPU/RAM/disk and cold-start latency.

Do not promise that a free hosting tier can run TensorFlow comfortably. Measure actual model memory and inference latency on the chosen host.

## 8. Phase 6 — Affordable skincare products feature and later enhancements

Implement the affordable-products feature only after core security and analysis safety gates are met. Requirements:
- Ask for or allow users to set budget, market/country (Pakistan should be supported where reliable data exists), skin type/concern and product preferences.
- Recommend affordable cleansers, moisturizers, sunscreens and relevant non-prescription skincare categories based on verified product/ingredient data.
- Show product name, category, key ingredients, why it may fit, cautions, price, source and last-checked date when available.
- Do not invent prices, stock, seller links, ingredients or efficacy. Mark estimates/stale data clearly.
- Do not recommend prescription drugs or imply a cosmetic product treats skin cancer, eczema or psoriasis. Concerning disease/lesion cases should receive professional-care guidance first.
- Include allergy/sensitivity caveats and patch-test guidance; do not guarantee universal safety.
- Disclose any sponsored placements and keep ranking criteria transparent.

Later enhancements: model/dataset registry, evaluation dashboard, user export/deletion, improved capture guidance and multilingual interface.
- Clinician-reviewed educational content.
- Consent-based reminders.
- De-identified aggregate analytics.

Do not start these until the existing features and security release gates pass.

## 9. Required documents and outputs

Maintain these living documents:
1. Security Audit Report with finding IDs, severity, evidence (file/line), risk, remediation, owner/status, and test evidence.
2. Security Requirements Specification with requirement IDs and verification mapping.
3. Product Requirements Specification with current scope, model separation, user flows, acceptance criteria, and roadmap.
4. Architecture diagram and data-flow diagram.
5. Threat model (assets, trust boundaries, attacker scenarios, mitigations).
6. API authorization matrix.
7. Dataset cards and model cards for every model.
8. ML evaluation report and non-skin/OOD report.
9. Deployment runbook, environment-variable reference, backup/restore and rollback plan.
10. Test plan and release checklist.

## 10. Definition of done

A task is done only when:
- Code change is complete and reviewed.
- Existing feature behavior remains intact or any intentional change is documented.
- Tests are added and pass.
- Security requirement IDs are mapped to evidence.
- No secrets or user data are committed.
- Model/dataset claims are reproducible.
- Deployment steps are documented.
- User has reviewed the change before push/merge.

## 11. First response expected from the engineering agent

Before coding, return:
1. Latest repository commit and file tree summary.
2. Existing feature/API map.
3. Confirmed vs unconfirmed audit findings.
4. Exact files to change in Phase 1.
5. Risks to backward compatibility.
6. Test plan.
7. Proposed branch and rollback plan.

Then implement Phase 1 in small batches. Do not jump to model expansion until security and deployment blockers are addressed.
