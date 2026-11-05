# Skyntri ML notebooks (train on Google Colab)

Three notebooks, **not executed**. Each contains all the code: dataset download, cleaning, preprocessing, augmentation, EfficientNet model, training, evaluation metrics, export and a prediction function that matches the backend. You upload the data and run them on Colab.

| Notebook | Model | Files it exports |
|---|---|---|
| [`notebooks/01_facial_skin_concerns_efficientnet.ipynb`](notebooks/01_facial_skin_concerns_efficientnet.ipynb) | **Model A**: facial skin concerns (Acne, Blackheads & Whiteheads, Dark Spots, Pores, Wrinkles, Skin Redness, optional Normal Skin) | `facial_concerns_efficientnet.keras`, `facial_concerns_metadata.json` |
| [`notebooks/02_skin_disease_screening_efficientnet.ipynb`](notebooks/02_skin_disease_screening_efficientnet.ipynb) | **Model B**: skin disease screening support (face and body) with a "see a doctor" referral flag | `skin_disease_efficientnet.keras`, `skin_disease_metadata.json` |
| [`notebooks/03_skin_gate_efficientnet.ipynb`](notebooks/03_skin_gate_efficientnet.ipynb) | **Skin gate**: "is this a skin photo?" (replaces the colour rules that rejected some real skin photos) | `skin_gate.keras`, `skin_gate_metadata.json` |

Run them in this order: **01 → 02 → 03**. Notebook 03 reuses the cleaned skin images from 01 and 02 as its positive examples.

Every code path was smoke-tested end to end on tiny synthetic images (no real data, 1 epoch, no pretrained weights). This checked that each cell runs and that the backend loads the exported files. Notebook 01 has been trained once (2026-11-05): test accuracy 0.903, macro-F1 0.899 on 756 held-out images. The results are in [`results/facial_v1/`](results/facial_v1/README.md). Notebooks 02 and 03 are not trained yet.

The old facial model (`EfficientNetB0_weighted_focal_finetuned_best.keras`, trained on the noisy Roboflow multi-label set) has been **removed**. Until you copy a new model into `backend/models/`, *Skin Analysis → Facial skin concerns* shows "Not available yet" instead of giving wrong results.

## 1. Datasets and download links

Check the licence on each dataset page. These datasets are for education and research. The notebooks write a dataset card next to the model.

### Model A: facial skin concerns (notebook 01)

| Role | Dataset | Link | Why |
|---|---|---|---|
| **Primary** | Skin Issues Dataset v2 (balanced), ~9.7k face images, one folder per class | https://www.kaggle.com/datasets/ahmedismaiil/skin-issues-version-2-dataset-balanced | Largest balanced set of facial concern photos (acne, blackheads, dark spots, pores, wrinkles) |
| **Second source** | Facial Skin: Acne, Pigmentation, Pores, Wrinkles (8 classes) | https://www.kaggle.com/datasets/shijo96john/facial-skin-acne-pigmentation-pores-wrinkles | Adds *redness*, and more acne and pigmentation images |
| Optional | Your own checked clear-skin faces, for a *Normal Skin* class. For example, pick spot-free photos from the `normal` folder of https://www.kaggle.com/datasets/shakyadissanayake/oily-dry-and-normal-skin-types-dataset | — | Without it, the model always picks some concern |

Not used: **killa92** "Facial Skin Analysis and Type Classification" (severity labels exist for only ~150 rows) and the **Roboflow Skin-Problem-MultiLabel** set the old model used (noisy labels, many augmented duplicates). The ISIC Archive is skin lesions, not facial concerns, so it is used in notebook 02.

### Model B: skin disease screening (notebook 02)

| Role | Dataset | Link | Licence / notes |
|---|---|---|---|
| **Primary** | Skin Diseases Image Dataset (Ismail Hossain), ~27k images, 10 classes | https://www.kaggle.com/datasets/ismailpromus/skin-diseases-image-dataset | Eczema, atopic dermatitis, psoriasis/lichen planus, fungal, warts/molluscum, nevi, BKL, BCC, melanoma |
| **Phone photos of lesions** | PAD-UFES-20, 2,298 smartphone images | https://data.mendeley.com/datasets/zr7vgbcyr2/1 | CC BY 4.0. Phone photos like the app's, so they are always kept |
| Optional, more lesions | ISIC 2019 (ISIC Archive challenge), 25,331 dermoscopy images | https://challenge.isic-archive.com/data/#2019 · images https://isic-challenge-data.s3.amazonaws.com/2019/ISIC_2019_Training_Input.zip · labels https://isic-challenge-data.s3.amazonaws.com/2019/ISIC_2019_Training_GroundTruth.csv | CC BY-NC. Set `USE_ISIC2019 = True`; ~9 GB |
| **External test only** | DDI (Stanford), biopsy-proven, all skin tones | https://aimi.stanford.edu/datasets/ddi-diverse-dermatology-images | Research agreement. Never trained on; used to check fairness across skin tones |

The 6 app classes: *Eczema / Atopic dermatitis*, *Psoriasis / Lichen planus*, *Fungal infection*, *Viral infection (warts / molluscum)*, *Benign-appearing lesion*, *Suspicious lesion* (melanoma, BCC, SCC, actinic keratosis → "see a dermatologist").

### Skin gate (notebook 03)

| Role | Dataset | Link |
|---|---|---|
| Skin (positive) | The cleaned images from notebooks 01 and 02 | read from `work/facial` and `work/disease` |
| Not skin | COCO 2017 validation photos **without people** (phones, laptops, food, rooms, animals…) | https://cocodataset.org/#download · http://images.cocodataset.org/zips/val2017.zip · http://images.cocodataset.org/annotations/annotations_trainval2017.zip |
| Not skin (textures) | DTD, Describable Textures Dataset | https://www.robots.ox.ac.uk/~vgg/data/dtd/download/dtd-r1.0.1.tar.gz |
| Not skin (optional) | Your own screenshots, documents, wrong uploads | folder `extra_negatives/` |

The notebooks download COCO, DTD, ISIC 2019 and both Kaggle sets themselves. For Kaggle, upload your `kaggle.json` (Kaggle → *Settings → API → Create New Token*) when the cell asks. PAD-UFES-20 and DDI must be downloaded by hand.

## 2. Google Drive layout

```
MyDrive/skyntri/
  datasets/
    facial/
      skin_issues/            <class>/*.jpg     (Kaggle ahmedismaiil, auto-download)
      facial_skin_8class/     <class>/*.jpg     (Kaggle shijo96john, auto-download)
      normal/                 *.jpg             (optional, your clear-skin faces)
    disease/
      skin_diseases_10class/  <class>/*.jpg     (Kaggle ismailpromus, auto-download)
      pad_ufes_20/            metadata.csv, imgs_part_*/   (manual download)
      isic2019/               (auto-download when USE_ISIC2019 = True)
      ddi/                    ddi_metadata.csv, images     (optional, external test)
    gate/
      coco/  dtd/             (auto-download)
      extra_negatives/        (optional)
  work/      (created: cleaned images, manifests, checkpoints, training logs)
  export/    (created: THE FILES YOU COPY INTO THE BACKEND)
```

In Colab: *File → Upload notebook*, then *Runtime → Change runtime type → T4 GPU* (A100/L4 is faster), then *Runtime → Run all*. Training resumes from the checkpoint in `work/` if Colab disconnects.

## 3. What the notebooks do (for the best results)

* **Cleaning:** removes unreadable, tiny, too dark, over-exposed and blurry images. Removes exact duplicates (MD5) and near duplicates (perceptual hash), including Roboflow `.rf.` copies, so the same photo cannot be in train and test. Images with conflicting labels are dropped.
* **Face crop (Model A):** each image is cropped to the largest face with a 35 % margin. The backend does the same crop, so a full selfie with background gets the same input the model was trained on.
* **Leakage-free split:** `StratifiedGroupKFold` keeps every copy of an image, and every patient (PAD-UFES-20), in one split.
* **Class balance:** per-class caps, class weights, and extra weight on *Suspicious lesion* so cancers are not missed.
* **Augmentation:** flips, rotation, zoom, translation, small contrast/brightness changes. There is no hue shift, because colour carries the label for redness and pigment.
* **Model:** EfficientNetB3 at 300 px by default (B0 or V2-S selectable), ImageNet weights, mixed precision. Two phases: train the head, then fine-tune with BatchNorm frozen. AdamW, cosine decay, label smoothing, early stopping, best checkpoint by macro-F1.
* **Decision rules tuned on validation data:** per-class thresholds, an *abstain* threshold (low confidence → the app asks for a better photo instead of guessing), and for Model B a referral threshold with ≥ 95 % sensitivity for *Suspicious lesion*.
* **Test-time augmentation:** the original and a flipped image are averaged, in the notebook and in the backend.
* **Evaluation metrics:** accuracy, balanced accuracy, macro and weighted F1, top-2 accuracy, one-vs-rest ROC-AUC, per-class precision, recall (sensitivity), specificity, F1 and AUC, confusion matrix, ROC curves, calibration (ECE) with reliability diagram, bootstrap 95 % confidence intervals, results by skin tone (ITA for Model A; Fitzpatrick and DDI for Model B), by source and by domain (phone/clinical/dermoscopy), and an error gallery. Model B also lists missed suspicious lesions for review. The gate reports false-accept and false-reject rates with Wilson CIs and per-category results.
* **Prediction:** `predict_concerns()`, `predict_disease()` and `is_skin()` at the end of each notebook use the same preprocessing and decision rules as the backend. Test your own photos there before copying the model.

## 4. Where to save the trained models (backend)

After training, each notebook writes its two files to **`MyDrive/skyntri/export/`**. Download them and copy them into the **`backend/models/`** folder of the project (for example `E:\Skyntri\backend\models\`), with these exact names:

```
backend/models/
  facial_concerns_efficientnet.keras     <- notebook 01
  facial_concerns_metadata.json          <- notebook 01
  skin_disease_efficientnet.keras        <- notebook 02
  skin_disease_metadata.json             <- notebook 02
  skin_gate.keras                        <- notebook 03
  skin_gate_metadata.json                <- notebook 03
```

These file names are already the defaults, so **no code change and no `.env` change is needed**. Always copy the `.keras` file together with its `_metadata.json`: the metadata holds the class names, image size, thresholds, face-crop and TTA settings.

The only switch: Model B stays **off** until a doctor has reviewed its evaluation. Then add this line to `.env` (root `.env` for Docker, `backend/.env` without Docker):

```env
DISEASE_SCREENING_ENABLED=true
```

### Docker

`docker-compose.yml` mounts `./backend/models` into the backend container. After copying the files, run:

```bash
docker compose restart backend
```

Check: open http://localhost:8000/health/ready. `facial_model.artifact_present` should be `true`, `input_gate.version` should start with `skin-gate-model` once the gate model is installed, and `disease_model` shows `enabled: true` after you switch it on.

### Where the paths are in the code (only if you use other file names)

| What | Setting (`.env`) | Default | Code that loads it |
|---|---|---|---|
| Model A file | `DATASET3_MODEL_PATH` | `models/facial_concerns_efficientnet.keras` | `backend/app/services/skin_analysis.py` → `load_dataset3_model()` |
| Model A metadata | `FACIAL_MODEL_METADATA_PATH` | `models/facial_concerns_metadata.json` | `backend/app/services/skin_analysis.py` → `facial_model_config()` |
| Model B file | `DISEASE_MODEL_PATH` | `models/skin_disease_efficientnet.keras` | `backend/app/services/disease_screening.py` → `load_model()` |
| Model B metadata | `DISEASE_MODEL_METADATA_PATH` | `models/skin_disease_metadata.json` | `backend/app/services/disease_screening.py` → `load_metadata()` |
| Model B on/off | `DISEASE_SCREENING_ENABLED` | `false` | `backend/app/routers/analyses.py` → `available_tracks()` |
| Skin gate file | `SKIN_GATE_MODEL_PATH` | `models/skin_gate.keras` | `backend/app/services/image_gate.py` (metadata is read from `skin_gate_metadata.json` in the same folder) |
| Shared preprocessing (face crop, resize, TTA) | — | — | `backend/app/services/model_io.py` → `prepare_batch()` |

All defaults are defined in `backend/app/core/config.py`. In `docker-compose.yml` the same variables are set under `backend → environment`.

**Model files are large.** `.gitignore` excludes `*.keras`, so models are not committed by accident. Keep them in Drive and copy them onto each machine or server.
