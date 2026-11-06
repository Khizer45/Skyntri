# Skin gate — training run v1 (notebook 03)

These are the results of the first training run of
[`ml/notebooks/03_skin_gate_efficientnet.ipynb`](../../notebooks/03_skin_gate_efficientnet.ipynb). The gate answers "is this a skin photo?" before any analysis runs.
The run was on Google Colab (GPU) on 2026-11-06. Facial concerns and disease screening are in [`../facial_v1/`](../facial_v1/README.md) and [`../disease_v1/`](../disease_v1/README.md).

The model file (`skin_gate.keras`) is **not in git**. It lives in Google Drive under `MyDrive/skyntri/export/`. Copy it with `skin_gate_metadata.json` (also in this folder) into `backend/models/`. The backend then uses it instead of the rule-based check: `gate_version` becomes `skin-gate-model:skin_gate.keras`, and the thresholds are read from the metadata.

| Setting | Value |
|---|---|
| Backbone | EfficientNetB0, ImageNet weights, 224 × 224 input, one sigmoid output = P(skin) |
| Training | head only (up to 3 epochs), then fine-tuning (up to 8 epochs, early stopping on validation AUC), label smoothing 0.05 |
| Augmentation | flips, rotation, zoom, and strong contrast and brightness changes, so that skin is recognised in poor light |
| Export check | exported file vs trained model: max probability difference 0.0000 |

## Data

| Class | Source | Images |
|---|---|---|
| Skin | Facial photos: the cleaned and face-cropped cache of notebook 01 | 5,306 |
| Skin | Face and body skin conditions: original downloads of notebook 02 (all PAD-UFES-20 smartphone photos plus a random sample of the Kaggle skin-disease images) | 8,000 |
| Not skin | DTD, Describable Textures Dataset (bumpy, porous, wrinkled, fibrous …) | 5,640 |
| Not skin | COCO 2017 validation photos **with no person in them**, sorted by the largest object | 2,307 |
| **Total** | | **21,253** |

COCO categories:
* animal 560
* furniture 446
* vehicle 346
* food 188
* indoor 173
* outdoor 163
* appliance 157
* electronic 100
* kitchen 75
* scene 48
* accessory 33
* sports 18

The split is grouped (`StratifiedGroupKFold`, about 70 / 15 / 15): near-duplicate groups of notebook 01 and all photos of one PAD-UFES-20 patient stay in one split.

## Decision thresholds (chosen on validation only)

| Setting | Value | Meaning |
|---|---|---|
| `accept_threshold` | 0.6732 | At or above: skin, analysis runs. Chosen so that at most 1 % of non-skin validation photos are accepted |
| `reject_threshold` | 0.6060 | Below: "not a skin photo". Chosen so that at most 1 % of skin validation photos are rejected |
| In between | | "Uncertain, please upload another photo" |

## Test results (3,035 held-out images: 1,899 skin, 1,136 not skin)

| Metric | Value | 95 % CI |
|---|---|---|
| ROC-AUC | **0.9996** | |
| Non-skin photos accepted as skin | **0.62 %** (7 of 1,136) | 0.30–1.27 % |
| Skin photos rejected | **0.58 %** (11 of 1,899) | 0.32–1.03 % |
| Skin photos accepted | **99.37 %** | |
| Answered "uncertain" (all test photos) | 0.10 % | |

| Category | Test images | Accepted as skin | Uncertain |
|---|---|---|---|
| skin: disease (face and body) | 1,142 | 99.6 % | 0.0 % |
| skin: facial | 757 | 99.1 % | 0.1 % |
| coco: furniture | 66 | 1.5 % | 0.0 % |
| dtd: texture | 807 | 0.7 % | 0.2 % |
| coco: animal, vehicle, food, electronic, kitchen, appliance, indoor, outdoor, scene, accessory, sports | 263 | 0.0 % | 0.0 % |

## Files in this folder

| File | Content |
|---|---|
| `skin_gate_metadata.json` | Exactly as exported by the notebook: thresholds, image size, SHA-256 of `skin_gate.keras`, test metrics and the per-category table. The backend needs it next to the `.keras` file |

## Limitations

* **Disease photos were not de-duplicated for this run.** The Kaggle set contains augmented copies, so a few near copies may sit in both the training and the test split. The skin acceptance on *skin: disease* may therefore be slightly optimistic. The facial photos and the non-skin photos were de-duplicated.
* **Hard negatives are missing:**
  * screenshots and documents (the optional `extra_negatives/` folder was empty);
  * photos of people with little skin visible, because COCO photos with people were left out on purpose.
* **Real use not measured yet.** Accuracy on real phone uploads (dim light, blur, other cameras) has not been measured. Check it in the app and keep the uploads it gets wrong as `extra_negatives/` or new skin examples for the next run.
* For *Skin Analysis → Facial concerns* the backend still requires a detected face after the gate accepts the photo (`facial_scope`).
