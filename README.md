# Skyntri Backend

FastAPI backend for **Skyntri — AI-Based Skin Health Assistant** (FYP, MUST,
Dept. of Software Engineering).

## What's implemented here

- **Auth**: register, login (JWT), forgot/reset password, change password,
  delete account, brute-force lockout after 5 failed attempts (REQ-6.x)
- **Profile**: view/update profile, skin type, notification settings, avatar
  upload
- **Contact**: contact form submission + listing (for an admin view later)
- **Progress Checker**: before/after image upload, storage, and a computed
  improvement score (placeholder metric — see note below)
- **Reports**: real PDF generation (via ReportLab) pulling in the latest
  analysis/progress data, with the required medical disclaimer, download
  endpoint
- **History**: aggregated view across analyses, ingredient scans, progress
  checks, and reports
- **AI Assistant chat**: persisted conversation history, with a stubbed
  reply generator (see note below)

## What's intentionally NOT implemented

Per your instructions, the following are left out because you're training/
building them yourself:

- **Skin disease classification** (CNN/PyTorch model) — `POST /analyses`
  only *stores* a result you give it (condition, confidence, severity...).
  Once your model is ready, run inference client-side or in a separate
  service, then POST the result here.
- **Ingredient OCR + safety analysis** — same pattern, see
  `POST /ingredient-scans`.

Two smaller pieces are stubbed with clearly-marked placeholder logic so the
app works end-to-end in the meantime, even though they weren't the ones you
named:

- `app/services/progress.py` — `compute_progress_score()` currently returns
  a randomized-but-plausible score instead of real OpenCV image comparison.
- `app/services/chat.py` — `get_assistant_reply()` currently returns a
  random canned reply instead of calling OpenAI/Gemini. Swap in a real API
  call when you're ready (see comments in that file).

## Setup

```bash
cd skyntri-backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit SECRET_KEY etc. as needed
uvicorn app.main:app --reload
```

The API will be live at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

Set your frontend's `VITE_API_URL` to `http://localhost:8000` and swap the
mock functions in `src/services/api.js` for real `fetch` calls to these
endpoints — the request/response shapes were designed to match what the
frontend already expects.

## Database

Uses SQLite by default (`skyntri.db`, created automatically on first run).
Swap `DATABASE_URL` in `.env` for a PostgreSQL connection string for
production, per the SRS. Tables are created automatically via
`Base.metadata.create_all` — for real migrations later, introduce Alembic.

## Project structure

```
app/
  core/         settings, JWT + password hashing
  db/           SQLAlchemy engine/session, ORM models
  routers/      one file per feature area (auth, profile, contact, ...)
  services/     PDF generation, upload handling, progress + chat stubs
  schemas.py    Pydantic request/response models
  dependencies.py  current-user auth guard
  main.py       app entrypoint, router wiring, CORS, static file serving
```
