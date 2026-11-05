# backend/models/

Put the trained model files exported by the Colab notebooks (`ml/notebooks/`) here.
The backend finds them automatically by these default names:

| File | Exported by | Used for |
|---|---|---|
| `facial_concerns_efficientnet.keras` + `facial_concerns_metadata.json` | `01_facial_skin_concerns_efficientnet.ipynb` | Skin Analysis → "Facial skin concerns" |
| `skin_disease_efficientnet.keras` + `skin_disease_metadata.json` | `02_skin_disease_screening_efficientnet.ipynb` | Skin Analysis → "Skin disease screening" (also needs `DISEASE_SCREENING_ENABLED=true`) |
| `skin_gate.keras` + `skin_gate_metadata.json` | `03_skin_gate_efficientnet.ipynb` | Rejects non-skin photos before analysis (optional; a built-in rule-based check is used without it) |

Always copy the `.keras` file **and** its `_metadata.json` together.
`*.keras` files are git-ignored on purpose (they are large); keep them in Google Drive or a release.
With Docker, this folder is mounted into the container: copy the files, then run `docker compose restart backend`.
