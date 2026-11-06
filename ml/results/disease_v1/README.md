# Skin disease screening — training run v1 (notebook 02)

These are the results of the first real training run of
[`ml/notebooks/02_skin_disease_screening_efficientnet.ipynb`](../../notebooks/02_skin_disease_screening_efficientnet.ipynb) (Model B, *Skin Analysis → Skin disease screening*).
The run was on Google Colab (L4 GPU) on 2026-11-05.
They cover **notebook 02 only**. Facial concerns (notebook 01) are in [`../facial_v1/`](../facial_v1/README.md). The skin gate (notebook 03) results are in [`../gate_v1/`](../gate_v1/README.md).

The model file (`skin_disease_efficientnet.keras`) is **not in git**. It lives in Google Drive under `MyDrive/skyntri/export/`. Copy it with `skin_disease_metadata.json` into `backend/models/` (see [`ml/README.md`](../../README.md#4-where-to-save-the-trained-models-backend)).

**Clinical review is pending.** Keep `DISEASE_SCREENING_ENABLED=false` until a dermatologist has reviewed these results and the missed suspicious lesions listed below.

| Setting | Value |
|---|---|
| Model version | `skin-disease-efficientnetb3-v2` |
| Backbone | EfficientNetB3, ImageNet weights, 300 × 300 input, softmax over 6 classes |
| Training | 6 epochs head only + 27 epochs fine-tuning (top 60 % unfrozen; early stopping with patience 7, limit 30), mixed precision, label smoothing 0.1, class weights (Suspicious lesion × 1.5) |
| Checkpoint rule | best `val_score` = mean of validation balanced accuracy and validation recall of *Suspicious lesion* |
| Best checkpoint | fine-tuning epoch 19 (counter starts at 0): val_score **0.863**, val balanced accuracy 0.771, val suspicious recall 0.955, val accuracy 0.805, val top-2 0.934 |
| Test-time augmentation | original + horizontal flip averaged |
| Export check | exported float32 file vs trained model: max probability difference 0.0064, same top class 100 % (exported with the fixed `build_model()`, see [`ml/README.md`](../../README.md#model-files-exported-before-the-fix-wrong-predictions)) |

## Data

| Source | Images used | Train | Val | Test |
|---|---|---|---|---|
| `skin_diseases_10class`: Kaggle *Skin Diseases Image Dataset* (10 classes, clinical and dermoscopy) | 12,144 | 8,672 | 1,737 | 1,735 |
| `pad_ufes_20`: PAD-UFES-20 (smartphone photos of skin lesions) | 1,868 | 1,331 | 257 | 280 |
| **Total** | **14,012** | **10,003** | **1,994** | **2,015** |

Cleaning steps:
1. Before cleaning there were 29,451 images: 27,153 Kaggle + 2,298 PAD-UFES-20.
2. Removed:
   * 7 for quality (too small, too dark, over-exposed or blurry);
   * 741 exact duplicate copies. Images whose identical copies carried different labels (104 hashes) were dropped completely;
   * near duplicates (the Kaggle set contains augmented copies), one image kept per group.
3. That left 21,810 unique images.
4. *Benign-appearing lesion* and *Suspicious lesion* were then capped at 4,000 each. All PAD-UFES-20 phone photos were kept. This gives 14,012 images in 13,342 groups.

The split is grouped: near duplicates and all photos of one PAD-UFES-20 patient stay in one split, and no group crosses splits.

| Class | Images | From (folder or PAD code) |
|---|---|---|
| Benign-appearing lesion | 4,000 | Melanocytic nevi 2,517 · BKL 581 · Seborrheic keratoses 555 · PAD NEV 181 · PAD SEK 166 |
| Suspicious lesion | 4,000 | BCC 1,537 · Melanoma 942 · PAD BCC 744 · PAD ACK 568 · PAD SCC 171 · PAD MEL 38 |
| Eczema / Atopic dermatitis | 1,864 | Eczema 1,193 · Atopic dermatitis 671 |
| Psoriasis / Lichen planus | 1,506 | Psoriasis, lichen planus and related |
| Viral infection (warts / molluscum) | 1,327 | Warts, molluscum and other viral infections |
| Fungal infection | 1,315 | Tinea, ringworm, candidiasis and other fungal infections |

Image type:
* clinical: 6,567
* dermoscopy: 5,577
* phone: 1,868

Fitzpatrick skin type is known only for 1,245 PAD-UFES-20 images:
* I–II: 857
* III–IV: 377
* V–VI: 11

## Test results (2,015 held-out images, never used for training or tuning)

| Metric | Value |
|---|---|
| Accuracy | **0.812** |
| Balanced accuracy | **0.778** |
| Macro F1 | **0.774** |
| Weighted F1 | 0.81 |
| Top-2 accuracy | 0.941 |
| Macro ROC-AUC (one-vs-rest) | 0.960 |
| **Referral sensitivity** (suspicious lesions flagged) | **0.961** (539 of 561) |
| Referral specificity | 0.935 |

| Class | Support | Sensitivity | Specificity | PPV | NPV | F1 | ROC-AUC |
|---|---|---|---|---|---|---|---|
| Eczema / Atopic dermatitis | 266 | 0.748 | 0.950 | 0.693 | 0.961 | 0.720 | 0.936 |
| Psoriasis / Lichen planus | 212 | 0.632 | 0.966 | 0.687 | 0.957 | 0.658 | 0.946 |
| Fungal infection | 193 | 0.725 | 0.970 | 0.718 | 0.971 | 0.722 | 0.945 |
| Viral infection (warts / molluscum) | 191 | 0.806 | 0.972 | 0.751 | 0.980 | 0.778 | 0.968 |
| Benign-appearing lesion | 592 | 0.791 | 0.982 | 0.947 | 0.918 | 0.862 | 0.978 |
| Suspicious lesion | 561 | 0.966 | 0.933 | 0.848 | 0.986 | 0.903 | 0.987 |

The metrics above use the top class for every test image (no abstention).

## Operating points (chosen on validation only)

| Setting | Value | Meaning |
|---|---|---|
| `referral_threshold` | 0.4505 | If *P(Suspicious lesion)* reaches this, the app recommends seeing a dermatologist, even when another class has the highest probability. Chosen for ≥ 95 % sensitivity on validation |
| `abstain_below` | 0.59 | Below this top probability the app asks for another photo. Chosen for ≥ 88 % accuracy on answered validation images with ≥ 75 % coverage (`TARGET_SELECTIVE_ACCURACY` was raised from 0.80 to 0.88 for this run; with 0.80 the model never abstained) |

The backend checks the referral flag **before** abstention, so a suspicious lesion is flagged even when the model is otherwise unsure.

Test coverage, accuracy on answered images, the 95 % bootstrap confidence intervals and the results by image type are in `skin_disease_metadata.json`, written by the notebook's export cell. That file is not in this folder yet.

## Missed suspicious lesions

The model did not flag 22 of the 561 suspicious test lesions (3.9 %). The notebook saved them to `MyDrive/skyntri/work/disease/missed_suspicious_for_review.csv`. **A clinician must look at these before release.**

The external test on DDI (Diverse Dermatology Images, more dark skin tones) was **not run**, because the dataset was not provided. It is recommended before release.

## Files in this folder

| File | Content |
|---|---|
| `training_log.csv` | Loss, accuracy, top-2, val balanced accuracy, val suspicious recall and val_score per epoch. Rows 1–6 are the head phase, rows 7–33 fine-tuning (the epoch counter restarts at 0) |
| `skin_disease_per_class_metrics.csv` | Per-class test metrics (table above) |
| `manifest_split.csv` | Every image that was used, with these columns. File names only, **no images**. |

`manifest_split.csv` columns:
* original path in Drive, source, original folder or PAD code, label and group
* image type and Fitzpatrick type
* MD5 and perceptual hash
* brightness and sharpness
* split

Not included:
* the images themselves: dataset licences, size;
* the `.keras` model file: keep it in Drive or a GitHub Release.

## Limitations

* **Not a diagnosis.** The model shows patterns that may be consistent with a condition and recommends a doctor for anything suspicious. It never gives an all-clear.
* **Same-source test.** The test images come from the same sources as the training images. Accuracy on real user photos (other cameras, lighting, body sites) has not been measured.
* **Inflammatory conditions are confused with each other.** Eczema, psoriasis and fungal infections have F1 0.66–0.72; psoriasis is the weakest (sensitivity 0.63). These classes have the fewest images (1.3k–1.9k).
* **Skin tone.** Fitzpatrick type is known for only 9 % of the images, and only 11 of them are type V–VI. Performance on darker skin is unknown. The DDI external test is needed.
* **Image type.** 40 % of the images are dermoscopy, which users cannot take with a phone. Only 13 % are smartphone photos (PAD-UFES-20).
* The licences of both datasets must be checked before any commercial use.
