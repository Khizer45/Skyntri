# Skyntri — Product Requirements Specification (PRS)

**Version:** 1.1 draft  
**Date:** 31 October 2026  
**Product direction:** Secure the existing application first; then introduce two distinct AI analysis tracks and an affordable skincare-products feature.

## 1. Product vision

Skyntri is an AI-assisted skin-care information and skin-health support application. It helps users explore facial skin concerns, receive carefully scoped information about selected skin diseases, understand skincare ingredients, compare visual progress, and discover affordable skincare products. It is **not a substitute for a dermatologist, biopsy, laboratory test, or medical diagnosis**.

The product must abstain when an image is not skin, is poor quality, is outside the supported scope, or produces an uncertain result. It must never invent a condition to force an answer.

## 2. Current product baseline

Preserve and improve the existing features:
- Account registration/login and profile.
- AI skin-image analysis and analysis history/dashboard.
- Ingredient scanner using OCR/Tesseract and ingredient database.
- Progress comparison using OpenCV visual heuristics.
- AI assistant/chat with fallback behavior.
- PDF report generation.
- Contact/help messages.
- SQLAlchemy database and React/Vite frontend.

Observed architecture: React + Vite frontend; FastAPI backend; SQLAlchemy with SQLite configuration and PostgreSQL support/configuration discussed; TensorFlow/Keras EfficientNetB0 multi-label model; pytesseract wrapper plus OS-level Tesseract executable; OpenCV progress comparisons.

## 3. Corrected AI model strategy — two distinct analysis tracks

### Shared first stage: image eligibility, quality and routing

Every uploaded image must pass secure decoding/format checks, quality assessment, skin-vs-non-skin eligibility, and OOD/uncertainty checks before any specialist model is called. The system must reject unrelated objects (electronics, buildings, documents, food, animals, screenshots, etc.) without showing skin-condition predictions. The gate must be evaluated on held-out hard negatives and representative skin images. Report non-skin false-accept rate and valid-skin rejection rate.

### Model A — Facial skin concerns / cosmetic-visible analysis

**Purpose:** analyze visible facial skin concerns and appearance-related patterns. This is not the disease-diagnosis model.

Candidate labels, subject to dataset and evaluation verification:
- Acne and blackheads.
- Dark spots / visible hyperpigmentation patterns.
- Visible pores.
- Wrinkles / fine lines.
- Oily or dry appearance.
- Redness and eye bags.
- Normal/ no supported concern detected (must not be described as medical clearance).

Scope is the face. The model must not claim to diagnose skin cancer, eczema, psoriasis, fungal infection, or other diseases. Labels such as oiliness, pores, wrinkles and dryness are appearance/skin-care concerns, not necessarily diseases. Output should be phrased as AI-estimated visible concerns with confidence/uncertainty and limitations.

### Model B — Skin disease analysis / screening support (face and body)

**Purpose:** assess images for a separately defined set of skin diseases or disease-like patterns. This model is **not limited to the body**: supported diseases may appear on the face or other body areas. It is separate from Model A because the task, labels, datasets, risks and evaluation requirements are different.

Candidate disease classes for research and staged development include:
- Eczema / atopic dermatitis patterns.
- Psoriasis patterns.
- Other dermatitis categories only when reliably distinguishable and supported by data.
- Fungal skin infections and other infectious conditions only where the dataset and clinical taxonomy support them.
- Suspicious lesions / possible skin-cancer-related patterns as a carefully controlled research or referral-support pathway.

**Skin cancer safety:** an image model must not tell a user that a lesion is cancer-free or provide a definitive cancer diagnosis. If a cancer-related pathway is included, it must be designed as risk-flagging / referral support, clinically reviewed, externally evaluated, and worded to encourage timely professional assessment of concerning lesions. A negative AI result must never reassure a user to delay care. Diagnosis may require dermoscopy, clinical examination, biopsy or other tests unavailable to a photo-only model.

Do not promise every disease class at launch. Add one condition only after confirming dataset licensing/consent, label provenance, class coverage, clinical meaning, representative examples, independent test data and qualified dermatology review. If a class cannot be reliably separated, combine it into an explicitly broader category or do not expose it.

### Model separation and routing rules

- Model A answers: “What facial skin-care concerns or visible patterns may be present?”
- Model B answers: “Does this image show patterns that may be associated with one of the supported skin diseases, and should the user seek professional assessment?”
- Model B may accept supported face and body images; it is not a body-only model.
- The user should choose the analysis purpose where ambiguity exists; scope detection may assist but must not silently misroute.
- Maintain independent datasets, label maps, preprocessing, thresholds, model versions, model cards, evaluation reports and rollback paths.
- Never combine the outputs into one undifferentiated list of “skin problems.” Clearly label which track produced each result.

## 4. Dataset, clinical governance and evaluation

For every dataset record source, version/date, license, permitted use, consent/privacy status, label definitions, annotator qualifications, geographic/skin-tone coverage, image count, class distribution and known biases. Deduplicate images and split by patient/person/source where possible. Maintain fixed internal and external test sets. Avoid leakage between train, validation and test.

For each model report per-class sensitivity/recall, specificity, precision, F1, confusion matrix, class support, calibration, confidence intervals, threshold rationale, subgroup results and failure cases. For disease models, sensitivity and false-negative risks must receive explicit clinical review; overall accuracy alone is inadequate. Validate on data independent of the training source and assess performance across skin tones, body sites, image quality and acquisition devices.

Do not describe a model as clinically validated unless the required clinical validation has actually been performed. Keep historical metrics labelled as historical/unverified until reproduced against the exact artifact, split, preprocessing and evaluation code. Current reported EfficientNetB0 figures (subset accuracy 71.52%, micro F1 81.17%, macro F1 66.73%, weighted F1 81.41%, Hamming loss 4.03%) are not clinical accuracy and must not be presented as such.

## 5. Affordable skincare products feature

**Purpose:** help users find practical, affordable skincare products that match their stated budget and skincare needs, with a focus on products realistically obtainable in Pakistan where reliable catalog/price data is available.

Requirements:
- Let users specify budget (per product or routine), currency, country/market, skin type or concern, and preferences such as fragrance-free or non-comedogenic where supported by verified product data.
- Recommend products by category (e.g. cleanser, moisturizer, sunscreen, acne-care active) and explain why each may fit the stated concern; do not imply that a product cures a disease.
- Show product name, brand, category, key ingredients, intended use, suitability caveats, estimated/current price, source and last-checked date when reliable data is available.
- Sort/filter by affordability and fit; offer a simple low-cost routine without requiring users to buy every suggested item.
- Clearly distinguish verified ingredient/product facts from general educational guidance. Do not fabricate prices, stock, seller links, ingredients, authenticity or clinical evidence.
- If live catalog/price data is unavailable or stale, label prices as estimates or ask the user to verify with the seller. Never claim current availability without a current source.
- Consider local availability, package size and cost-per-use where data permits. Provide alternatives at different budget levels only when supported by evidence.
- Avoid recommending prescription medicines or treatment regimens. For suspected skin cancer, severe eczema/psoriasis, infection, rapidly changing lesions, pain, bleeding or worsening symptoms, prioritize professional medical assessment over shopping recommendations.
- Include allergy/sensitivity cautions and advise patch testing for new cosmetic products. Do not guarantee a product is safe for every user.
- Product recommendations must not be influenced by paid placement unless sponsorship is explicitly disclosed; ranking criteria must be transparent.

## 6. Functional requirements

**FR-01 Authentication/profile:** preserve existing flows and enforce account isolation.  
**FR-02 Secure image upload:** validate format, signature, size, dimensions, decoding and quality.  
**FR-03 Skin eligibility/OOD:** reject non-skin, unsupported and uncertain images before specialist inference.  
**FR-04 Facial skin concerns:** run Model A for supported facial appearance/skin-care labels only.  
**FR-05 Skin disease screening support:** run Model B for its explicitly supported disease classes on supported face/body sites; no unsupported diagnosis or false reassurance.  
**FR-06 Results/history:** show analysis track, model version, date, limitations and safe next steps; preserve historical records.  
**FR-07 Ingredient scanner:** preserve OCR; show OCR confidence, corrections, unknown ingredients and sources; no definitive medical safety claim from OCR alone.  
**FR-08 Progress comparison:** preserve approximate visual comparison, with consistent-photo guidance; no clinical measurement claim.  
**FR-09 Chat:** preserve functionality; non-diagnostic, safe responses and protected history.  
**FR-10 Reports:** private, owner-checked reports showing analysis track/model version and limitations.  
**FR-11 Contact:** public submission may remain; listing/management admin-only.  
**FR-12 Affordable products:** provide budget-aware product discovery with traceable product/price/ingredient data and safety caveats.  
**FR-13 Administration:** secure server-side permissions for support and controlled model/catalog management.

## 7. Non-functional requirements

Security and privacy by default; bounded inference and upload workloads; reliable readiness checks; reproducible model/data versioning; migrations and tests; explainable limitations; accessible upload guidance; structured logs without sensitive images/tokens; and a documented deployment/rollback process.

## 8. UX states

Support: uploading/processing; unsupported file; too large/corrupt; poor quality; not a skin image; uncertain/OOD; facial analysis complete; disease-screening result; no supported disease pattern detected (not medical clearance); professional assessment recommended; unsupported site/class; model unavailable; and network/server error. Product feature states: budget not set; recommendations available; product/price data unavailable or stale; and no suitable product within budget.

## 9. Release roadmap

1. Security and privacy fixes; preserve existing workflows.
2. Image validation, skin/non-skin gate, OOD/abstention and evaluation.
3. Reproduce and improve current facial skin-concern model.
4. Build disease model in a separate research/validation track, beginning only with well-supported classes; clinical review before user-facing disease claims.
5. Add affordable products catalogue/recommendation feature with data provenance and price freshness.
6. Add model registry, evaluation dashboard, user export/deletion, multilingual UX and other enhancements.

## 10. Acceptance criteria

- Non-skin test images never receive facial-concern or disease labels when rejected by the gate.
- Facial model outputs only its approved facial concern taxonomy.
- Disease model outputs only classes in its released, validated taxonomy and supports explicitly tested face/body sites.
- Cancer-related output never claims diagnosis or rules out cancer; concerning cases receive professional-care guidance.
- No model is released without dataset provenance, fixed test evaluation, model card, limitations and rollback artifact.
- Product results show a source and freshness indicator for prices; unsupported product facts are omitted rather than invented.
- Existing authentication, ingredient scanner, progress, chat, reports, history and contact submission remain functional and pass regression tests.
- Critical/high security issues are fixed and verified before public deployment.

## 11. Implementation status (31 October 2026)

| Item | Status |
|---|---|
| FR-01 Authentication/profile | Preserved; hardened (roles, throttling, secure reset, validated avatar upload) |
| FR-02 Secure image upload | Done (decode-based validation, private storage, signed URLs) |
| FR-03 Skin eligibility/OOD | Done with an interim heuristic gate and model-uncertainty abstention; trained gate still required |
| FR-04 Model A facial concerns | Live behind the gate; results labelled "Facial skin concerns · AI estimate" |
| FR-05 Model B disease screening | Code path, safe result logic and training notebook ready. **Switched off** until a trained model is installed and `DISEASE_SCREENING_ENABLED=true` after clinical review |
| FR-06 Results/history | Track, model version and gate version stored for new analyses; old records kept and migrated as "legacy" |
| FR-07 Ingredient scanner | Preserved; rate-limited; OCR now installed in the container image |
| FR-08 Progress comparison | Preserved; "approximate visual comparison" note and photo-consistency guidance added |
| FR-09 Chat | Preserved; rate-limited |
| FR-10 Reports | Owner-checked download, sanitised filename, `no-store` caching |
| FR-11 Contact | Public submission; admin-only list/detail/delete |
| FR-12 Affordable products | Built: ingredient-based search (wanted/avoided ingredients, budget, skin type, category), recommendations from the latest facial analysis, cart, cash-on-delivery orders. Admins add products with price **source** and **checked date**; stale prices are labelled; sponsored items labelled, not boosted; no products for disease results. No catalogue data is shipped: the admin enters real products |
| FR-13 Administration | Server-side admin role; contact messages, product CRUD with images, order status management |
