# Skyntri ML notebooks (train on Google Colab)

Two notebooks, **not executed**. They contain all the code: dataset loading, cleaning, augmentation, EfficientNet model, training, evaluation metrics, export and prediction. You upload the data and run them on Colab.

| Notebook | Model | Output files |
|---|---|---|
| [`notebooks/01_facial_skin_concerns_efficientnet.ipynb`](notebooks/01_facial_skin_concerns_efficientnet.ipynb) | **Model A**: facial skin concerns, multi-label (10 labels) | `facial_concerns_efficientnet.keras`, `facial_concerns_metadata.json` |
| [`notebooks/02_skin_disease_screening_efficientnet.ipynb`](notebooks/02_skin_disease_screening_efficientnet.ipynb) | **Model B**: skin disease screening support (face and body), softmax + referral flag | `skin_disease_efficientnet.keras`, `skin_disease_metadata.json` |

Every code path was smoke-tested end to end on tiny synthetic images (no real data, 1 epoch, no pretrained weights) to check that each cell runs, and that the backend loads the exported files. No real model was trained.

## 1. Datasets (download links)

Always read the licence on the dataset page and record it in the dataset card the notebook writes.

### Model A — facial skin concerns

| Use | Dataset | Download | Licence / notes |
|---|---|---|---|
| **Primary** (same 10 labels as Skyntri) | Roboflow *Skin-Problem-MultiLabel* | https://universe.roboflow.com/yolov10-kuvz2/skin-problem-multilabel-di2c7 · https://universe.roboflow.com/annisa-nadila-nasya-frarx/skin-problem-multilabel-rkbfr | Export format **"Multi-Label Classification (CSV)"**. Licence is shown under "Cite this project". |
| Extra (CC BY 4.0) | Roboflow *facial* (dark circles, pores, pimples, wrinkles, hyperpigmentation) | https://universe.roboflow.com/facial-zfrfm/facial-ngz7q | CC BY 4.0 |
| Extra (CC BY 4.0) | Roboflow *skin_multilabel* (acne, eye bags, wrinkles) | https://universe.roboflow.com/skin-condition-detection/skin_multilabel | CC BY 4.0 |
| Extra (severity 0–5) | Kaggle *Facial Skin Analysis and Type Classification* | https://www.kaggle.com/datasets/killa92/facial-skin-analysis-and-type-classification | Check licence; Kaggle login needed |
| Extra (one folder per class) | Kaggle *Skin Issues* | https://www.kaggle.com/datasets/ahmedismaiil/skin-issues-version-2-dataset-balanced | Check licence |
| Acne only | ACNE04 v2 labels | https://github.com/AIpourlapeau/acne04v2 | Research use; cite Wu et al., ICCV 2019 |

Recommendation: start with the primary Roboflow set. Add the CC BY sets to get more acne, pores, wrinkles and eye-bag examples. The notebook's **masked loss** handles sources that label only some classes.

### Model B — skin disease screening

| Role | Dataset | Download | Licence |
|---|---|---|---|
| **Primary** | SCIN (Google + Stanford) | https://github.com/google-research-datasets/scin · data in `gs://dx-scin-public-data/dataset` (the notebook has the download cell) | SCIN Data Use License |
| Extra | Fitzpatrick17k | https://github.com/mattgroh/fitzpatrick17k (CSV; images through the form in its README) | CC BY-NC-SA 3.0 (non-commercial) |
| Referral flag (skin cancer and precancer) | PAD-UFES-20 | https://data.mendeley.com/datasets/zr7vgbcyr2/1 | CC BY 4.0 |
| **External test only** | DDI (Stanford) | https://aimi.stanford.edu/datasets/ddi-diverse-dermatology-images | Research use agreement; never train on it |

## 2. Google Drive layout expected by the notebooks

```
MyDrive/skyntri/
  datasets/
    facial/
      skin_problem_multilabel/   train/ valid/ test/  (+ _classes.csv in each)
      rf_facial/                 (optional, same Roboflow CSV format)
      kaggle_skin_issues/        <class name>/*.jpg   (optional)
    disease/
      scin/dataset/              scin_cases.csv, scin_labels.csv, images/
      fitzpatrick17k/            fitzpatrick17k.csv, images/<md5hash>.jpg
      pad_ufes_20/               metadata.csv, imgs_part_*/...
      ddi/                       ddi_metadata.csv, images
  work/      (created: cleaned images, manifests, checkpoints, logs)
  export/    (created: the files you copy into the backend)
```

Open a notebook in Colab (*File → Upload notebook*), select *Runtime → Change runtime type → T4 GPU*, enable the datasets you uploaded in the `SOURCES` cell, and run all cells.

## 3. What the notebooks do

**Cleaning:** removes unreadable, tiny, too dark, over-exposed and blurry images. Merges exact duplicates (MD5) and groups near duplicates with a perceptual hash, which also catches Roboflow's augmented copies. Resolves contradictory labels. Optional face crop. Caches resized images.

**Leakage-free split:** an original image and all its copies, or a patient/case, always stay in one split. Model A uses grouped multi-label stratification; Model B uses `StratifiedGroupKFold`.

**Augmentation:** colour-safe flips, rotation, zoom, translation, and small contrast/brightness changes. There is no hue shift, because colour carries the label for redness and pigment.

**Model:** Keras `EfficientNetB0` (or B3), ImageNet weights. Two phases: frozen head, then fine-tuning with BatchNorm frozen, AdamW with cosine decay, early stopping and checkpointing.
* Model A loss: masked, class-weighted focal binary cross-entropy. Thresholds are tuned per class on validation.
* Model B loss: class-weighted cross-entropy with label smoothing. A referral threshold for *Suspicious lesion* is chosen on validation for ≥ 95 % sensitivity, plus an abstention threshold.

**Evaluation metrics:**
* **Model A:** per-class precision, recall, specificity, F1, ROC-AUC, PR-AUC; micro/macro/weighted F1; subset accuracy; Hamming loss; Jaccard; multilabel confusion matrices; ROC and PR curves; calibration (ECE) and reliability diagram; bootstrap 95 % CIs; approximate skin-tone (ITA) subgroups; per-source results; error gallery.
* **Model B:** per-class sensitivity, specificity, PPV, NPV, F1, AUC; balanced accuracy; top-2 accuracy; normalised confusion matrix; ECE; group-bootstrap CIs; Fitzpatrick subgroup results; review list of missed suspicious lesions; external DDI test by skin tone.

**Prediction:** `predict_concerns()` and `predict_disease()` use exactly the backend's preprocessing and decision rules.

## 4. Where to put the trained model (backend)

Copy the files from `MyDrive/skyntri/export/` into **`backend/models/`**, then set these in **`backend/.env`**:

```env
# Model A - facial concerns
DATASET3_MODEL_PATH=models/facial_concerns_efficientnet.keras
FACIAL_MODEL_METADATA_PATH=models/facial_concerns_metadata.json

# Model B - disease screening (stays OFF until a dermatologist has reviewed the evaluation)
DISEASE_MODEL_PATH=models/skin_disease_efficientnet.keras
DISEASE_MODEL_METADATA_PATH=models/skin_disease_metadata.json
DISEASE_SCREENING_ENABLED=false
```

No code change is needed:

| What | Code that loads it |
|---|---|
| Model A file | `backend/app/services/skin_analysis.py` → `load_dataset3_model()` reads `DATASET3_MODEL_PATH` |
| Model A classes, thresholds, image size, version | `backend/app/services/skin_analysis.py` → `facial_model_config()` reads `FACIAL_MODEL_METADATA_PATH` |
| Model B file + metadata | `backend/app/services/disease_screening.py` → `load_model()` / `load_metadata()` |
| Model B availability in the app | `backend/app/routers/analyses.py` → `available_tracks()`; the frontend reads `GET /analyses/tracks` |
| Path settings and defaults | `backend/app/core/config.py` (`dataset3_model_path`, `facial_model_metadata_path`, `disease_model_path`, `disease_model_metadata_path`, `disease_screening_enabled`) |

If you keep the default file names in `backend/models/`, you can leave the paths out; they are already the defaults (except `DATASET3_MODEL_PATH`, whose default is the old model).

Check after restarting: `GET http://localhost:8000/health/ready` shows `facial_model.version` (and `disease_model` when it is enabled).

**Model files are large.** `.gitignore` excludes `*.keras`, so new models are not committed by accident. Keep them in Drive or a release asset and copy them onto the server, or `git add -f` them deliberately.
