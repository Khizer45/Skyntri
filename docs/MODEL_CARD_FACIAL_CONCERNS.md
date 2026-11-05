# Model card — Model A: facial skin concerns

**Status: trained (v1, 2026-11-05), not stored in git.** The model `facial-concerns-efficientnetb3-v2` was trained with `ml/notebooks/01_facial_skin_concerns_efficientnet.ipynb` on Colab. Results, training log and the split list are in [`ml/results/facial_v1/`](../ml/results/facial_v1/README.md). The `.keras` file is kept in Google Drive (`MyDrive/skyntri/export/`) and must be copied with its metadata into `backend/models/`. Without it, the API reports the facial track as unavailable (`GET /analyses/tracks` → `available: false`; `POST /analyses/analyze` → HTTP 422 `model_not_installed`).

The previous model (`EfficientNetB0_weighted_focal_finetuned_best.keras`, Roboflow "Skin-Problem-MultiLabel", 10 sigmoid outputs, reported macro-F1 0.67 without a leakage-free split) was removed.

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

## Results of v1 (test set: 756 held-out images)

| Metric | Value |
|---|---|
| Accuracy | 0.903 |
| Balanced accuracy | 0.911 |
| Macro F1 | 0.899 |
| Weighted F1 | 0.904 |
| Top-2 accuracy | 0.968 |
| Macro ROC-AUC (OvR) | 0.989 |

| Class | Support | Precision | Recall | F1 |
|---|---|---|---|---|
| Blackheads & Whiteheads | 100 | 0.811 | 0.900 | 0.853 |
| Acne | 247 | 0.969 | 0.895 | 0.931 |
| Dark Spots | 112 | 0.825 | 0.839 | 0.832 |
| Pores | 48 | 0.923 | 1.000 | 0.960 |
| Wrinkles | 97 | 0.945 | 0.887 | 0.915 |
| Skin Redness | 49 | 0.811 | 0.878 | 0.843 |
| Normal Skin | 103 | 0.944 | 0.981 | 0.962 |

Data: 5,291 unique images after cleaning (14,803 before), split 3,779 / 756 / 756.
* Skin Issues v2: 2,880
* Facial Skin 8-class: 1,686
* Normal (Oily, Dry and Normal Skin Types): 725

The best checkpoint was at fine-tuning epoch 18 (val macro-F1 0.921). Full tables, confidence intervals and per-source numbers: `ml/results/facial_v1/` and `facial_concerns_metadata.json`.

These are in-distribution numbers: the test images come from the same Kaggle sources. Accuracy on real phone selfies and per skin tone still has to be checked before release.

## Safety behaviour in the API

* Runs only after the input gate accepts the image (`docs/ML_INPUT_GATE.md`).
* Abstains (`model_uncertain`) when the model is not confident, instead of guessing.
* "Normal Skin" is shown as "No supported facial concern detected", which is not medical clearance.
* Labels are presented as appearance and skin-care concerns, not diseases.

## Known limitations

* Each training image has one label, so the model learns the *most visible* concern; secondary concerns depend on threshold tuning.
* Public facial datasets under-represent darker skin tones; the ITA subgroup table from the notebook is not recorded yet.
* Weakest classes in v1: Dark Spots (F1 0.83) and Skin Redness (0.84); Pores and Skin Redness have the fewest unique images (341 and 354).
* Phone photos in poor light remain harder than the curated training images.
