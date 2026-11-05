# Dataset card - Skyntri facial concerns

Version: 2026-11-05

| Source | Images | Licence | Notes |
|---|---|---|---|
| skin_issues | 2880 | check on Kaggle page | |
| facial_skin_8class | 1686 | check on Kaggle page | |
| normal | 725 | check on Kaggle page | |

Cleaning: unreadable/small/dark/blurry removed, exact + near duplicates removed, contradicting labels removed,
face crop, per-class cap. Split: StratifiedGroupKFold ~70/15/15 (groups never cross splits).