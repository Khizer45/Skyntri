# Expanding the Ingredient Database Beyond the Seed Set

The database ships with **167 curated, commonly-used skincare ingredients**
(`app/services/ingredient_data.py`), each with an accurate function
description, safety status, skin-type suitability, and usage notes. That's
a solid working set for a demo/FYP, but it's intentionally *not* pretending
to be a 1000+-ingredient regulatory database — hand-authoring safety
verdicts for a thousand+ individual chemicals one-by-one risks getting some
wrong, which isn't acceptable for anything health-adjacent.

If you want to grow the database toward (or past) 1000 entries for a fuller
FYP demo, here's the safe way to do it — bulk import from an existing,
vetted public source, rather than typing out one-off entries by hand.

## Option 1 — Bulk import from a public ingredient database (recommended)

Public cosmetic-ingredient databases already contain structured data for
thousands of INCI ingredients:

- **CosIng** (EU Commission's Cosmetic Ingredient Database) — free, official,
  downloadable. Has INCI names, functions, and restrictions.
  https://ec.europa.eu/growth/tools-databases/cosing/
- **INCI Beauty** / **INCIDecoder** — community-run ingredient databases with
  simplified safety/function summaries (check their terms before bulk-using
  data commercially; fine for an academic project with attribution).
- **PubChem** — for chemical/safety data on individual compounds.

**Workflow:**

1. Download/export the source data as CSV (most of these offer a CSV/API export).
2. Write a one-off script (`scripts/import_from_csv.py`) that reads the CSV
   and maps its columns to our `Ingredient` model fields:
   - `name`, `inci_name`, `aliases_json`
   - `category` — you'll need a mapping table from the source's categories
     to ours (see `CATEGORY_DEFAULTS` in `ingredient_data.py`)
   - `function`, `uses_json`
   - `safety_status`, `safety_score` — CosIng doesn't give a safety verdict
     directly; you'll need to derive this from restriction/annex flags, or
     keep a manual review pass for anything you plan to mark "Potential
     Irritant" or worse.
   - `suitable_skin_types_json` / `avoid_skin_types_json` / `when_to_use` /
     `precautions` — these usually need to be inferred from the ingredient's
     *category* (reuse `CATEGORY_DEFAULTS` as your starting point), since
     most public databases don't track this per-ingredient.
3. Insert rows the same way `ingredient_seed.py` does — check for existing
   names first so re-running the import doesn't duplicate rows.
4. Spot-check a random sample of ~30-50 imported rows by hand before trusting
   the full set — bulk imports from category-mapping logic can produce
   plausible-looking but wrong entries at the edges (e.g. an ingredient that's
   both a preservative *and* an active).

## Option 2 — Expand the curated set incrementally

Just keep adding `_entry(...)` calls to `INGREDIENTS` in
`ingredient_data.py`, following the existing pattern. This keeps quality
high (each entry gets a human look) but is slower — probably realistic for
another 100-200 ingredients in a focused afternoon, not straight to 1000+.

## Whichever option you pick

- Keep the `CATEGORY_DEFAULTS` pattern — assigning safety/skin-type defaults
  by *category* rather than repeating them per-ingredient keeps the dataset
  consistent and easy to audit.
- Never mark something "Beneficial" or assign `avoid_skin_types: []` (no
  cautions at all) unless you're confident in that call — when in doubt,
  default to "Caution" and note that it needs review; that's a safer failure
  mode than false reassurance.
- Re-run `seed_ingredients()` (happens automatically on every backend
  startup) — it only inserts new names, so it's safe to run repeatedly as
  you grow the dataset.
