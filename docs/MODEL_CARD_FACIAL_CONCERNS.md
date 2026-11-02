# Model card — Model A: facial skin concerns

**Status: no model installed.** The previous model (`EfficientNetB0_weighted_focal_finetuned_best.keras`, Roboflow "Skin-Problem-MultiLabel", 10 sigmoid outputs) was removed. Its labels were noisy, the training set held many augmented duplicates, and its metrics could not be reproduced. Until a new model is trained with `ml/notebooks/01_facial_skin_concerns_efficientnet.ipynb` and copied into `backend/models/`, the API reports the facial track as unavailable (`GET /analyses/tracks` → `available: false`, `reason`; `POST /analyses/analyze` → HTTP 422 `model_not_installed`).

| Field | Value (filled in by the notebook's dataset card and metadata) |
|---|---|
| Version string | `model_version` in `facial_concerns_metadata.json`; stored with every analysis |
| Artifact | `backend/models/facial_concerns_efficientnet.keras` + `facial_concerns_metadata.json` (SHA-256 in the metadata) |
| Architecture | EfficientNetB3 at 300 px by default (B0 / V2-S selectable), ImageNet init, softmax over the classes, label smoothing 0.1, class weights, mixed precision; exported as float32 |
| Preprocessing | EXIF-rotate → RGB → largest-face crop with 35 % margin (Haar cascade; whole image if no face) → bilinear resize → float32 0–255 (EfficientNet rescaling is inside the model). Shared code: `backend/app/services/model_io.py::prepare_batch` |
| Test-time augmentation | Original + horizontal flip averaged (`tta: true` in metadata) |
| Labels | Acne, Blackheads & Whiteheads, Dark Spots (incl. pigmentation), Pores, Wrinkles, Skin Redness, optional Normal Skin |
| Decision rules | Top class always reported; a second/third class is reported when it passes its per-class threshold (precision ≥ 0.55 on validation). If the top probability is below `abstain_below` (chosen for ≥ 85 % selective accuracy at ≥ 80 % coverage) the API abstains with `model_uncertain` |
| Training data | Kaggle *Skin Issues v2 (balanced)* and Kaggle *Facial Skin: Acne, Pigmentation, Pores, Wrinkles*, plus optional checked clear-skin faces. Links and licences: `ml/README.md` |
| Cleaning and split | Unreadable/tiny/dark/over-exposed/blurry images removed; MD5 and perceptual-hash duplicates grouped; `StratifiedGroupKFold` so duplicates never cross splits |
| Intended use | Educational, AI-estimated *visible facial skin-care concerns* behind the input gate. Not a diagnosis. |
| Out of scope | Diseases (eczema, psoriasis, infections, skin cancer), body sites, non-skin images, medical decisions |

## Metrics to record after training

The notebook prints, and writes into the metadata and dataset card: accuracy, balanced accuracy, macro and weighted F1, top-2 accuracy, one-vs-rest ROC-AUC, per-class precision / recall / specificity / F1 / AUC with support, confusion matrix, ECE with reliability diagram, bootstrap 95 % CIs, results by approximate skin tone (ITA), by source and by face-found, and an error gallery. Copy the headline numbers into this card when a model is installed.

## Safety behaviour in the API

* Runs only after the input gate accepts the image (`docs/ML_INPUT_GATE.md`).
* Abstains (`model_uncertain`) when the model is not confident, instead of guessing.
* "Normal Skin" is shown as "No supported facial concern detected", which is not medical clearance.
* Labels are presented as appearance and skin-care concerns, not diseases.

## Known limitations

* Each training image has one label, so the model learns the *most visible* concern; secondary concerns depend on threshold tuning.
* Public facial datasets under-represent darker skin tones; check the ITA subgroup table before release.
* Phone photos in poor light remain harder than the curated training images.
