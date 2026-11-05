# Skyntri documentation

| Document | What it covers |
|---|---|
| [01_Security_Audit_Report.md](01_Security_Audit_Report.md) | Findings, verified status, fixes and test evidence |
| [02_Security_Requirements_Specification.md](02_Security_Requirements_Specification.md) | Security requirements + verification status appendix |
| [03_Product_Requirements_Specification.md](03_Product_Requirements_Specification.md) | Product scope, the two model tracks, implementation status |
| [04_Master_Implementation_Prompt.md](04_Master_Implementation_Prompt.md) | The original implementation brief |
| [ML_INPUT_GATE.md](ML_INPUT_GATE.md) | Non-skin rejection and abstention design, sample evaluation, how to plug in a trained gate |
| [MODEL_CARD_FACIAL_CONCERNS.md](MODEL_CARD_FACIAL_CONCERNS.md) | Model A card (version, checksum, limitations) |
| [API_AUTHORIZATION_MATRIX.md](API_AUTHORIZATION_MATRIX.md) | Who can call what, ownership rules and rate limits |
| [THREAT_MODEL.md](THREAT_MODEL.md) | Assets, trust boundaries, attacker scenarios |
| [DEPLOY_VPS.md](DEPLOY_VPS.md) | **Go live:** put Skyntri on a server with HTTPS, step by step |
| [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md) | Docker deployment, backup/restore, release and rollback |
| [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Every backend setting |
| [TEST_PLAN_AND_RELEASE_CHECKLIST.md](TEST_PLAN_AND_RELEASE_CHECKLIST.md) | Automated tests, manual checks, release gate |
| [../ml/README.md](../ml/README.md) | Colab training notebooks, dataset download links, where to put trained models |

Architecture and data flow (current):

```
Browser (React/Vite, CSP)
   │  HTTPS, Bearer JWT
   ▼
FastAPI ──► rate limits (DB) ──► routers (owner-scoped queries)
   │                                 │
   │                                 ├─► upload validation ─► private storage (UPLOAD_DIR)
   │                                 │                          ▲
   │                                 │        signed /files/... URLs (15 min)
   │                                 ├─► input gate ─► Model A (EfficientNetB3) ─► abstain / result
   │                                 ├─► OCR (Tesseract) ─► ingredient DB
   │                                 ├─► OpenCV progress comparison
   │                                 └─► PDF reports (owner-only download)
   ▼
PostgreSQL / SQLite (Alembic migrations)
```
