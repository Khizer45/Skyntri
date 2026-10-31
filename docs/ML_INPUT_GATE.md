# Skin-analysis input gate and abstention (ML-01)

## Why

Model A (EfficientNetB0, 10 sigmoid outputs) always outputs a score for every label, even for a photo of a laptop. Thresholds alone cannot tell you whether an image is skin. The two sample images that shipped in the repository (`backend/test_skin.jpg`, solid black, and `backend/tests/test_input_image.jpg`, solid blue) both reached the model before this change.

## Pipeline (`POST /analyses/analyze`)

```
upload → decode + validate (uploads.save_upload)
       → quality: size, darkness, over-exposure, flat image, blur
       → skin vs non-skin (trained gate model if present, else heuristic)
       → facial scope for Model A (frontal face found, or skin fills the frame)
       → Model A inference
       → abstain if no label (not even "Normal Skin") reaches its threshold
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
| `model_uncertain` | No label passed its validated threshold | "We cannot confidently analyze this image…" |
| `track_not_available` | Model B requested | Explains it is not released; recommends a dermatologist for concerns |

## Current gate: `skin-gate-heuristic-v1` (interim)

A rule-based detector in `backend/app/services/image_gate.py`:

* skin-colour mask (YCrCb + RGB rules), skin-pixel ratio and largest connected skin region,
* near-grey pixel ratio (documents, screens, grayscale images),
* OpenCV Haar frontal-face detector for the facial scope check.

### Sample evaluation (not a validation)

Run with `python scripts/evaluate_input_gate.py <folder>` on 112 public sample images (OpenCV/scikit-image/dlib/darknet sample images and face crops). Images are not committed.

| Set | Images | Result | 95% CI (Wilson) |
|---|---|---|---|
| Skin (face crops + portraits) | 56 | valid-skin rejection **10.7 %** (6 of 56 turned away, 5 of them as "uncertain" with retake guidance) | 5.0 – 21.5 % |
| Non-skin (objects, scenes, animals, food, documents, textures) | 56 | non-skin false accept **7.1 %** (4 of 56) | 2.8 – 17.0 % |

Before this change the false-accept rate on the same non-skin images was 100 % (every image reached the model).

**Limitations, stated plainly:**

* The thresholds were tuned on these same images, so this is **not** a held-out result.
* The sample is small and not representative: few real electronics photos, few dark-skin close-ups, no real skin-condition close-ups, no phone camera images.
* Known false accepts: close-ups of orange/brown fur (cat), a yellow chick, a photo with dogs where the face detector fired.
* Grayscale skin photos are rejected (by design, the model needs colour).

## Replacing it with a trained gate (required before launch)

1. Collect a licensed dataset: diverse skin photos (all skin tones, face and body sites, phone cameras, lighting) and hard negatives (phones, laptops, keyboards, screens, rooms, furniture, vehicles, documents, screenshots, charts, food, plants, animals, landscapes, clothing, cartoons, textures).
2. Split by source/person; keep a **held-out hard-negative test set** that is never used for tuning.
3. Train a binary classifier with a single sigmoid output = P(skin). Save it as `backend/models/skin_gate.keras` (or set `SKIN_GATE_MODEL_PATH`).
4. Set `SKIN_GATE_ACCEPT_THRESHOLD` / `SKIN_GATE_REJECT_THRESHOLD` from the validation set; between them the API answers "uncertain".
5. Evaluate with `scripts/evaluate_input_gate.py` on the held-out set and report false-accept and valid-skin rejection rates per category with confidence intervals. Agree launch thresholds with the product owner.

The service uses the trained model automatically when the file exists (`gate_version` becomes `skin-gate-model:<file>`); quality and facial-scope checks still run.
