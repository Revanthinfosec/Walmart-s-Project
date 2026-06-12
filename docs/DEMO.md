# POC Demo — Verified End-to-End Run

This document reproduces a full working run of the app against the **real OpenAI
vision model** (`gpt-4o-mini`). Every output below was captured from a live run.

## Prerequisites

```bash
cd app/backend
python -m venv .venv && source .venv/bin/activate   # or use the repo .venv
pip install -r requirements.txt
cp .env.example .env        # then paste your OPENAI_API_KEY into .env
uvicorn main:app --reload   # serves on http://127.0.0.1:8000
```

`.env` is gitignored, so the key never enters version control. Without a key the
app falls back to a stub classifier and the same workflow still runs.

## 1. Health check

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

## 2. Upload + real AI classification

```bash
curl -s -X POST http://127.0.0.1:8000/images/upload \
  -F "file=@eval/images/fashion-002.jpg" \
  -F "designer=Revanth"
```

Real model response (abridged):

```json
{
  "id": 1,
  "filename": "fashion-002.jpg",
  "classification": {
    "garment_type": "dress",
    "style_tags": ["vintage", "floral", "swing"],
    "materials": ["cotton"],
    "colors": ["yellow", "black"],
    "patterns": ["floral"],
    "season": "spring",
    "occasion": ["casual", "evening"],
    "consumer_profile": "fashion-forward individuals who appreciate vintage styles",
    "trend_notes": ["bold colors", "retro aesthetics"],
    "location": {"continent": "unknown", "country": "unknown", "city": "unknown"},
    "description": "This vibrant dress features a striking floral pattern in yellow against a black background, perfect for making a statement. Its swing style adds a playful touch, making it suitable for both casual outings and evening events."
  },
  "designer": "Revanth",
  "designer_tags": [],
  "designer_notes": null,
  "created_at": "2026-06-12T04:50:36Z"
}
```

Two more images were uploaded to populate the library:

| id | file | garment_type | colors | season |
|----|------|--------------|--------|--------|
| 1 | fashion-002.jpg | dress | yellow, black | spring |
| 2 | fashion-003.jpg | outerwear | blue, orange, yellow, purple | spring |
| 3 | fashion-001.jpg | outerwear | gray | all_season |

## 3. Dynamic filter options (built from data, not hardcoded)

```bash
curl -s http://127.0.0.1:8000/filters
```

```
garment_type: ['dress', 'outerwear']
season:       ['all_season', 'spring']
colors:       ['black', 'blue', 'gray', 'orange', 'purple', 'yellow']
designers:    ['Revanth']
```

Only values that actually exist in the library appear.

## 4. Attribute filtering

```bash
curl -s "http://127.0.0.1:8000/images?garment_type=dress"
# -> id 1  fashion-002.jpg

curl -s "http://127.0.0.1:8000/images?garment_type=outerwear"
# -> id 3  fashion-001.jpg
# -> id 2  fashion-003.jpg
```

## 5. Full-text search across AI descriptions

```bash
curl -s "http://127.0.0.1:8000/images?query=denim"
# -> id 2  fashion-003.jpg   (the word "denim" appears only in the AI description)
```

Crash-safety: arbitrary FTS5 syntax characters do not break the query.

```bash
curl -s --get "http://127.0.0.1:8000/images" --data-urlencode 'query=floral" AND'
# -> returns results, HTTP 200 (no 500 syntax error)
```

## 6. Designer annotations (searchable, distinct from AI)

```bash
curl -s -X PATCH http://127.0.0.1:8000/images/1 \
  -H "Content-Type: application/json" \
  -d '{"designer_tags":["resort","SS26-reference"],
       "designer_notes":"Love the swing silhouette — revisit for the spring capsule."}'
```

Human-entered text is immediately searchable:

```bash
curl -s "http://127.0.0.1:8000/images?query=capsule"   # -> id 1 (matches notes)
curl -s "http://127.0.0.1:8000/images?query=resort"    # -> id 1 (matches a tag)
```

The annotations are stored in separate fields (`designer`, `designer_tags`,
`designer_notes`) from the AI `classification`, so the UI renders them as a
distinct "Designer input" block.

## 7. Combined contextual filter

```bash
curl -s "http://127.0.0.1:8000/images?designer=Revanth&season=spring"
# -> id 2  fashion-003.jpg  spring
# -> id 1  fashion-002.jpg  spring
```

## Result

Every requirement in the brief was exercised against the live model: upload + AI
classification (structured attributes + natural-language description), dynamic
filters, attribute + contextual filtering, natural-language full-text search over
both AI and human content, and designer annotations that are distinct yet
searchable.
