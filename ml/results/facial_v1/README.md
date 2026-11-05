# Facial skin concerns — training run v1 (notebook 01)

These are the results of the first real training run of
[`ml/notebooks/01_facial_skin_concerns_efficientnet.ipynb`](../../notebooks/01_facial_skin_concerns_efficientnet.ipynb) (Model A, *Skin Analysis → Facial skin concerns*).
The run was on Google Colab (L4 GPU) on 2026-11-05.
They cover **notebook 01 only**. The disease model (notebook 02) and the skin gate (notebook 03) are not trained yet.

The model file (`facial_concerns_efficientnet.keras`, ~45 MB) is **not in git**. It lives in Google Drive under `MyDrive/skyntri/export/`. Copy it with `facial_concerns_metadata.json` into `backend/models/` (see [`ml/README.md`](../../README.md#4-where-to-save-the-trained-models-backend)).

| Setting | Value |
|---|---|
| Model version | `facial-concerns-efficientnetb3-v2` |
| Backbone | EfficientNetB3, ImageNet weights, 300 × 300 input, softmax over 7 classes |
| Training | 6 epochs head only + 25 epochs fine-tuning (top 60 % unfrozen; early stopping, limit 30), batch 64, mixed precision, label smoothing 0.1, class weights |
| Best checkpoint | fine-tuning epoch 18: val macro-F1 **0.921**, val accuracy 0.927, val top-2 0.968 |
| Test-time augmentation | original + horizontal flip averaged |

## Data

| Source (Kaggle) | Images after cleaning | Train | Val | Test |
|---|---|---|---|---|
| `skin_issues`: Skin Issues v2 (balanced) | 2,880 | 2,053 | 414 | 413 |
| `facial_skin_8class`: Facial Skin (acne, pigmentation, pores, wrinkles) | 1,686 | 1,208 | 238 | 240 |
| `normal`: Oily, Dry and Normal Skin Types (`normal` folders) | 725 | 518 | 104 | 103 |
| **Total** | **5,291** | **3,779** | **756** | **756** |

Before cleaning there were 14,803 labelled images. Removed:
* 3 too small;
* 67 too dark, over-exposed or blurry;
* 2,032 exact duplicate copies;
* the rest as near duplicates (re-encoded, brightened or zoomed copies), so that no photo appears in two splits.

A face was detected in 34 % of the images. The rest are skin close-ups and were kept uncropped, which is the same rule the backend uses.

| Class | Images | Class weight |
|---|---|---|
| Acne | 1,745 | 0.43 |
| Dark Spots (incl. pigmentation) | 789 | 0.96 |
| Normal Skin | 725 | 1.04 |
| Wrinkles | 675 | 1.12 |
| Blackheads & Whiteheads | 662 | 1.17 |
| Skin Redness | 354 | 2.11 |
| Pores | 341 | 2.22 |

## Test results (756 held-out images, never used for training or tuning)

| Metric | Value |
|---|---|
| Accuracy | **0.903** (without TTA 0.902) |
| Balanced accuracy | **0.911** |
| Macro F1 | **0.899** |
| Weighted F1 | 0.904 |
| Top-2 accuracy | 0.968 |
| Macro ROC-AUC (one-vs-rest) | 0.989 |
| Coverage after abstention | 1.00 (no test image was abstained on in this run) |

| Class | Support | Precision | Recall | Specificity | F1 | ROC-AUC | Threshold |
|---|---|---|---|---|---|---|---|
| Blackheads & Whiteheads | 100 | 0.811 | 0.900 | 0.968 | 0.853 | 0.987 | 0.588 |
| Acne | 247 | 0.969 | 0.895 | 0.986 | 0.931 | 0.983 | 0.409 |
| Dark Spots | 112 | 0.825 | 0.839 | 0.969 | 0.832 | 0.974 | 0.314 |
| Pores | 48 | 0.923 | 1.000 | 0.994 | 0.960 | 1.000 | 0.471 |
| Wrinkles | 97 | 0.945 | 0.887 | 0.992 | 0.915 | 0.993 | 0.305 |
| Skin Redness | 49 | 0.811 | 0.878 | 0.986 | 0.843 | 0.986 | 0.695 |
| Normal Skin | 103 | 0.944 | 0.981 | 0.991 | 0.962 | 0.998 | 0.404 |

*Threshold* is the per-class probability above which a class is also reported as a second or third concern. It was tuned on validation, with precision ≥ 0.55.

The summary metrics were copied from the notebook's section 10 output. The per-class table is `facial_concerns_per_class_metrics.csv`. The full metrics with 95 % bootstrap confidence intervals are stored in `facial_concerns_metadata.json`, next to the model.

## Files in this folder

| File | Content |
|---|---|
| `training_log.csv` | Loss, accuracy, top-2 and val macro-F1 per epoch. Rows 1–6 are the head phase, rows 7–31 fine-tuning (the epoch counter restarts at 0) |
| `facial_concerns_per_class_metrics.csv` | Per-class test metrics (table above) |
| `facial_concerns_dataset_card.md` | Dataset card written by the notebook |
| `manifest_split.csv` | Every image that was used: original path in Drive, source, label, duplicate group, MD5, perceptual hash, brightness, sharpness, face found, split. File names only, **no images** |

Not included:
* the images themselves: Kaggle licences, size;
* `manifest_clean.pkl`: binary, and the same data as `manifest_split.csv`;
* the `.keras` model file.

## Limitations

* The test images come from the same Kaggle sources as the training images. Accuracy on real phone selfies (other lighting, cameras, skin tones) has not been measured yet; check it in the app before relying on it.
* Each training image has one label, so the model names the most visible concern. Secondary concerns depend on the thresholds above.
* Weakest classes: Dark Spots (F1 0.83) and Skin Redness (0.84). Skin Redness and Pores have the fewest unique images.
* The skin-tone (ITA) subgroup results printed by the notebook are not recorded here.
* The licences of the three Kaggle datasets must be checked before any commercial use.
* AI estimate of visible skin-care concerns, not a medical diagnosis.
