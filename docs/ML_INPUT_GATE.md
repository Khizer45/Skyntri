# Skin-analysis input gate and abstention (ML-01)

## Why

A classifier always outputs a score for every label, even for a photo of a laptop. Thresholds alone cannot tell you whether an image is skin. The two sample images that shipped in the repository (`backend/test_skin.jpg`, solid black, and `backend/tests/test_input_image.jpg`, solid blue) both reached the model before this change.

## Pipeline (`POST /analyses/analyze`)

```
upload → decode + validate (uploads.save_upload)
       → quality: size, darkness, over-exposure, flat image, blur
       → skin vs non-skin (trained gate model if present, else heuristic)
       → facial scope for Model A (frontal face found, or skin fills the frame)
       → Model A inference
       → abstain if the model is not confident (top probability < abstain_below)
       → save result with analysis_track, model_version, gate_version
```

If any stage does not accept the image:

* the condition model is **not** called (or its output is discarded at the last step),
* the uploaded file is deleted and nothing is saved to history,
* the API returns **HTTP 422** with `{code, status, message, guidance}`,
* an `analysis_abstained` log event records the stage, reason code and versions (no image, no user data).

| `code` | Meaning | User message |
|---|---|---|
| `not_skin_image` | Not a skin photo | "This image does not appear to be a skin photo. Please upload a clear skin image." |
| `uncertain_input` | Borderline gate decision | "We cannot confidently analyze this image. Please upload another photo." |
| `face_not_detected` | Skin-like, but no face for facial analysis | Asks for a front-facing or close-up facial photo |
| `image_too_small` / `image_too_dark` / `image_overexposed` / `image_low_detail` / `image_too_blurry` | Quality | Retake guidance |
| `model_uncertain` | Model not confident enough | "We cannot confidently analyze this image…" |
| `model_not_installed` | No facial model file in `backend/models/` | Explains the model is not installed yet |
| `track_not_available` | Model B requested while `DISEASE_SCREENING_ENABLED=false` or its file is missing | Explains it is not released; recommends a dermatologist for concerns |

## Current gate: `skin-gate-heuristic-v2` (interim)

A rule-based detector in `backend/app/services/image_gate.py`:

* skin-colour mask: YCrCb + RGB + HSV rules, computed on the original image **and** on a gray-world white-balanced copy (gains clipped to 0.8–1.25, with an original-saturation guard), so skin under warm/yellow or cool indoor light is still recognised,
* skin-pixel ratio and largest connected skin region,
* near-grey pixel ratio (documents, screens, grayscale images),
* OpenCV Haar frontal-face detector for the facial scope check.

v2 was made because users reported real skin photos being rejected as "not a skin image" by v1.

### Sample evaluation (not a validation)

Run with `python scripts/evaluate_input_gate.py <folder>` on 112 public sample images (OpenCV/scikit-image/dlib/darknet sample images and face crops). Images are not committed.

| Set | Images | v1 | **v2** | v2 95% CI (Wilson) |
|---|---|---|---|---|
| Skin (face crops + portraits): valid-skin rejection | 56 | 10.7 % | **1.8 %** (1 of 56, as "too blurry") | 0.3 – 9.5 % |
| Non-skin (objects, scenes, animals, food, documents, textures): false accept | 56 | 7.1 % | **12.5 %** (7 of 56) | 6.2 – 23.6 % |

v2 deliberately trades some non-skin false accepts for far fewer wrongly rejected skin photos. 25 of the 38 object/scene photos end as "uncertain" (retake guidance), not as an analysis. Before the gate existed the false-accept rate was 100 %.

**Limitations, stated plainly:**

* The thresholds were tuned on these same images, so this is **not** a held-out result.
* The sample is small and not representative: few real electronics photos, few dark-skin close-ups, no real skin-condition close-ups, no phone camera images.
* Known false accepts: close-ups of orange/brown fur, wood and food with skin-like colours.
* Grayscale skin photos are rejected (by design, the model needs colour).

## Replacing it with a trained gate (required before launch)

`ml/notebooks/03_skin_gate_efficientnet.ipynb` does steps 1–4: positives are the cleaned images from notebooks 01 and 02, negatives are COCO 2017 photos without people, DTD textures and your own `extra_negatives/`. It exports `skin_gate.keras` + `skin_gate_metadata.json` (accept/reject thresholds at 1 % false accept and 1 % skin rejection on validation). Copy both into `backend/models/`; the thresholds in the metadata override `SKIN_GATE_ACCEPT_THRESHOLD` / `SKIN_GATE_REJECT_THRESHOLD`.

1. Collect a licensed dataset: diverse skin photos (all skin tones, face and body sites, phone cameras, lighting) and hard negatives (phones, laptops, keyboards, screens, rooms, furniture, vehicles, documents, screenshots, charts, food, plants, animals, landscapes, clothing, cartoons, textures).
2. Split by source/person; keep a **held-out hard-negative test set** that is never used for tuning.
3. Train a binary classifier with a single sigmoid output = P(skin). Save it as `backend/models/skin_gate.keras` (or set `SKIN_GATE_MODEL_PATH`).
4. Set `SKIN_GATE_ACCEPT_THRESHOLD` / `SKIN_GATE_REJECT_THRESHOLD` from the validation set; between them the API answers "uncertain".
5. Evaluate with `scripts/evaluate_input_gate.py` on the held-out set and report false-accept and valid-skin rejection rates per category with confidence intervals. Agree launch thresholds with the product owner.

The service uses the trained model automatically when the file exists (`gate_version` becomes `skin-gate-model:<file>`); quality and facial-scope checks still run.
