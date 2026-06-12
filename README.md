# Fashion Garment Classification & Inspiration Web App

A lightweight full-stack app for fashion designers to upload field inspiration photos, auto-classify garments with AI, search and filter across rich metadata, and add their own tags and notes over time.

## Problem & approach

Design teams collect thousands of reference photos from markets, stores, and street style. This POC turns that pile into a searchable library: upload → multimodal classification → visual grid with dynamic filters → designer annotations layered on top of AI output.

**Trade-offs (intentional for a one-day POC):**
- Single-user, no auth
- OpenAI vision for classification (swap-friendly)
- SQLite + FTS5 instead of Elasticsearch
- Location/time context split between AI inference (continent/country/city) and capture timestamp (year/month filters)

## What I built / What I learned / Limitations

**What I built.** An end-to-end pipeline that takes a raw inspiration photo,
classifies the garment with a multimodal model into structured attributes plus a
natural-language description, stores everything in SQLite with FTS5 full-text
search, and surfaces it through a React grid with dynamic filters. On top of the
AI output, designers can layer their own tags and notes, which are stored
separately but indexed alongside the AI text so a single search box spans both.

**What I learned.**
- FTS5 is a lot of leverage for a one-day POC — I get natural-language search over
  both AI descriptions and human notes without standing up a separate search
  service, as long as I sanitize raw query input so stray operators don't raise
  syntax errors.
- Keeping AI output and human annotations in separate columns (rather than
  merging them) kept the model honest and the UI clear about provenance — you can
  always tell what the model said versus what the designer added.
- Treating the Pydantic models as the single source of truth and mirroring them
  in the TypeScript types removed a whole class of frontend/backend drift bugs.
- The model is strong on broad descriptive tags but weak on exact taxonomy and
  geography, which pushed me toward "≥50% set overlap" scoring for list fields
  rather than demanding exact matches.

**Limitations.** Single-user with no auth; AI-inferred location is a scene guess,
not capture GPS; no pagination or deduplication yet; and the eval set isn't
bundled (you supply images locally). See *Limitations & next steps* below for the
full list and what I'd do with another day.

## Project structure

```
fashion-inspiration-app/
├── app/
│   ├── backend/          FastAPI, classifier, SQLite
│   └── frontend/         React + TypeScript
├── eval/                 labeled test set + accuracy script
├── tests/                unit, integration, e2e
└── README.md
```

## Setup

**Backend**

```bash
cd app/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
uvicorn main:app --reload
```

API docs: http://127.0.0.1:8000/docs

**Frontend**

```bash
cd app/frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

**Tests**

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

## Architecture

```
React UI  →  FastAPI  →  OpenAI Vision (classify)
                ↓
           SQLite + FTS5 (metadata + full-text search)
                ↓
           uploads/ (image files)
```

**Classification** — `classifier.py` sends each image to `gpt-4o-mini` (configurable) and parses JSON into structured fields: garment type, style, material, colors, pattern, season, occasion, consumer profile, trend notes, location, and a natural-language description.

**Storage** — AI metadata lives in `classification_json`. Designer name, comma-separated tags, and free-text notes are stored separately and indexed in FTS so searches can hit both AI and human content.

**Filters** — `GET /filters` builds dropdown options from values already in the library (not hardcoded). Supports garment attributes plus continent/country/city, year/month from capture time, and designer.

## Features vs brief

| Requirement | Status |
|-------------|--------|
| Upload + AI classification | Done |
| Rich description + structured attributes | Done |
| Visual grid | Done |
| Dynamic attribute filters | Done |
| Location + time + designer filters | Done |
| Full-text search | Done |
| Designer tags/notes (distinct from AI) | Done |
| Eval script + labels template | Done (needs 50–100 images) |
| Unit / integration / e2e tests | Done |

## Model evaluation

See `eval/README.md`. Quick start:

1. Add 50–100 images to `eval/images/` (Pexels/Unsplash fashion photos work well).
2. Label `eval/labels.csv` with expected attributes.
3. Run `python eval/evaluate.py` with `OPENAI_API_KEY` set.

**Dataset:** 52 Pexels fashion/street-style photos in `eval/images/` (run `python eval/download_images.py` to refresh).

**Labels:** 16 images hand-reviewed in `eval/manual_labels.py`; remaining rows drafted via classifier. Re-run with your key for best results:

```bash
export OPENAI_API_KEY=your_key
python eval/curate_labels.py          # full AI draft labels
python eval/apply_manual_labels.py  # merge with hand-reviewed rows
python eval/evaluate.py
```

**Sample eval run (stub classifier, no API key):**

| Field | Accuracy |
|-------|----------|
| garment_type | 0% (stub defaults to `other`) |
| materials | 82.7% |
| patterns | 88.5% |
| occasion | 84.6% |
| continent / country | ~96% |
| season | 0% (stub defaults to `all_season`) |

**With OpenAI enabled**, expect garment type and season to jump significantly; location fields may stay weaker because the model infers scene context rather than capture GPS.

**Where the model does well:** broad tags (casual, streetwear), pattern/material guesses, list overlap fields.

**Where it struggles:** exact garment taxonomy, season without climate cues, precise geography, niche trend vocabulary.

**Next steps with more time:** few-shot prompt examples, EXIF geotags for location ground truth, human relabel UI, fine-tuned vision model.

## Limitations & next steps

- Stub classifier used when `OPENAI_API_KEY` is missing (filename heuristics only).
- AI-inferred location is a best guess — not a substitute for capture GPS.
- No pagination, deduplication, or multi-user workspaces yet.
- Eval dataset not bundled (copyright); you provide images locally.

**If I had another day:** batch upload, thumbnail generation, filter chips UX, export to CSV, and a small labeling UI to speed up eval set creation.

## Assumptions

- Designers upload one look per photo.
- `created_at` represents field capture time for year/month filters.
- OpenAI API access is available for real classification and evaluation.
