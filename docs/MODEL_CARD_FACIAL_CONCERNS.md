# Model card — Model A: facial skin concerns

| Field | Value |
|---|---|
| Version string | `facial-concerns-effnetb0-v1` (stored with every new analysis) |
| Artifact | `backend/models/EfficientNetB0_weighted_focal_finetuned_best.keras` |
| SHA-256 | `848c270c056e735948f500b804976b7361b994c741b490c90319e4a1feb63d48` (41,660,624 bytes) |
| Architecture | EfficientNetB0 (ImageNet init), 224×224 RGB, 10 sigmoid outputs, weighted focal loss, fine-tuned |
| Preprocessing | RGB → bilinear resize 224×224 → float32, no manual /255 (EfficientNet rescaling is inside the model) |
| Labels | Acne, Blackheads, Dark Spots, Dry Skin, Eye bags, Normal Skin, Oily Skin, Pores, Skin Redness, Wrinkles |
| Thresholds | Per class, tuned on validation F1 (see `DATASET3_THRESHOLDS` in `services/skin_analysis.py`) |
| Training data | Roboflow "Skin-Problem-MultiLabel", reported 4,828 images. **Licence, consent status, skin-tone coverage and split method not yet documented.** |
| Intended use | Educational, AI-estimated *visible facial skin-care concerns* behind the input gate. Not a diagnosis. |
| Out of scope | Diseases (eczema, psoriasis, infections, skin cancer), body sites, non-skin images, medical decisions. |

## Reported metrics (historical, unverified)

Subset accuracy 71.52 %, micro-F1 81.17 %, macro-F1 66.73 %, weighted-F1 81.41 %, Hamming loss 4.03 %.
These come from the original training notebook and have **not** been reproduced against this exact artifact, split and code. They are not clinical accuracy.

## Safety behaviour in the API

* Runs only after the input gate accepts the image (`docs/ML_INPUT_GATE.md`).
* If no label, not even "Normal Skin", reaches its threshold, the API abstains (`model_uncertain`).
* "Normal Skin" is shown as "No supported facial concern detected", which is not medical clearance.
* Labels such as pores, oiliness, dryness and wrinkles are presented as appearance and skin-care concerns, not diseases.

## Known limitations

* Multi-label sigmoid outputs are not calibrated probabilities; the "confidence" shown is the highest detected-label score.
* No subgroup (skin tone, age, sex, device) evaluation is available.
* Performance on phone photos with varied lighting is unknown.

## To do before release

Reproduce the metrics with a fixed test split and published evaluation code. Report per-class precision, recall, F1, support, the confusion matrix and calibration. Record the dataset card (licence, consent, demographics).
