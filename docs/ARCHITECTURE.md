# Architecture & Design

Full architecture, UML, dataflow, and end-to-end implementation notes for the
Fashion Garment Classification & Inspiration web app. Diagrams use Mermaid and
render on GitHub.

## 1. System / Component Architecture

Three-tier app: a React SPA, a FastAPI service, and SQLite. The only external
dependency is OpenAI Vision, and it is optional (stub fallback when no API key).

```mermaid
flowchart TB
  subgraph Browser["Browser — Designer"]
    UI["React + TypeScript SPA<br/>(Vite dev server :5173)"]
  end

  subgraph Backend["FastAPI service :8000"]
    API["main.py<br/>REST endpoints + CORS"]
    CLS["classifier.py<br/>vision call / stub"]
    DBL["db.py<br/>data access + search"]
    MODELS["models.py<br/>Pydantic schemas"]
    STATIC["/uploads<br/>StaticFiles mount"]
  end

  subgraph Storage["Persistence"]
    SQLITE[("SQLite — fashion.db<br/>images + images_fts (FTS5)")]
    FILES[("uploads/ — image files")]
  end

  EXT["OpenAI Vision API<br/>gpt-4o-mini"]

  UI -- "HTTP / JSON" --> API
  UI -- "img src → GET /uploads/*" --> STATIC
  API --> CLS
  API --> DBL
  API -. validates with .-> MODELS
  DBL -. validates with .-> MODELS
  CLS -. validates with .-> MODELS
  CLS -- "only if OPENAI_API_KEY" --> EXT
  DBL --> SQLITE
  STATIC --> FILES
  API -- "writes file" --> FILES
```

| Module | Owns |
|---|---|
| `main.py` | HTTP routing, request/response shaping, file persistence, CORS |
| `classifier.py` | Turning an image into a `ClassificationResult` (real or stub), parsing model JSON |
| `db.py` | All SQL: schema, insert/update, search, filter-option aggregation, FTS sync |
| `models.py` | Single source of truth for data shapes (shared by all three above) |
| Frontend `api.ts` | The only place that knows backend URLs |
| Frontend components | Pure view + local form state |

## 2. Domain Model — Class UML

Pydantic models in `models.py`. They flow unchanged from classifier -> DB -> API
-> frontend, which is why TypeScript `types.ts` mirrors them 1:1.

```mermaid
classDiagram
  class GarmentType {
    <<enum>>
    dress
    top
    bottom
    outerwear
    footwear
    accessory
    other
  }
  class Season {
    <<enum>>
    spring
    summer
    fall
    winter
    all_season
  }
  class LocationContext {
    +str continent
    +str country
    +str city
  }
  class ClassificationResult {
    +GarmentType garment_type
    +list~str~ style_tags
    +list~str~ materials
    +list~str~ colors
    +list~str~ patterns
    +Season season
    +list~str~ occasion
    +str consumer_profile
    +list~str~ trend_notes
    +LocationContext location
    +str description
  }
  class ImageRecord {
    +int id
    +str filename
    +str file_path
    +ClassificationResult classification
    +str designer
    +list~str~ designer_tags
    +str designer_notes
    +datetime created_at
  }
  class ImageUpdate {
    +str designer
    +list~str~ designer_tags
    +str designer_notes
  }
  class SearchFilters {
    +str query
    +GarmentType garment_type
    +Season season
    +str color/style/material/pattern
    +str occasion/consumer_profile/trend_note
    +str continent/country/city
    +str year/month/designer
  }
  class FilterOptions {
    +list~str~ per-attribute option lists
  }

  ClassificationResult --> GarmentType
  ClassificationResult --> Season
  ClassificationResult *-- LocationContext
  ImageRecord *-- ClassificationResult
  SearchFilters --> GarmentType
  SearchFilters --> Season
```

Key decision: AI output (`ClassificationResult`) and human input (`designer*`
fields) are separate attributes on `ImageRecord`, never merged. This is what lets
the UI render an "AI-generated" block distinct from a "Designer input" block.

## 3. Persistence — ER / Storage Model

Two tables. `images` is the system of record; `images_fts` is a denormalized FTS5
mirror kept in sync on every write, keyed by `rowid = images.id`.

```mermaid
erDiagram
  images {
    INTEGER id PK
    TEXT    filename
    TEXT    file_path UK
    TEXT    classification_json "full ClassificationResult as JSON"
    TEXT    designer
    TEXT    designer_tags_json  "JSON array"
    TEXT    designer_notes
    TEXT    created_at "ISO-8601, drives year/month filters"
  }
  images_fts {
    INTEGER rowid FK "= images.id"
    TEXT    description
    TEXT    colors_patterns_styles_materials "tokenized AI fields"
    TEXT    continent_country_city
    TEXT    garment_type_season
    TEXT    designer_tags_notes "human fields, also searchable"
  }
  images ||--|| images_fts : "mirrored on insert/update"
```

Why this shape:
- Structured attributes live as a JSON blob in `classification_json`, queried with
  SQLite `json_extract` — flexible schema, no migration when the model gains a field.
- Full-text search needs flat tokenized columns, so the same data is also flattened
  into `images_fts`. Both AI text and designer text are indexed, so one query box
  hits both.
- `_sync_fts()` does delete-then-insert on every write so the index never drifts.

## 4. Behavioral UML — Sequence Diagrams

### 4a. Upload + Classify (`POST /images/upload`)

```mermaid
sequenceDiagram
  actor D as Designer
  participant UI as App.tsx
  participant API as FastAPI /images/upload
  participant C as classifier.py
  participant O as OpenAI Vision
  participant DB as db.py
  participant S as SQLite + uploads/

  D->>UI: pick file (+ optional name)
  UI->>API: POST multipart {file, designer}
  API->>API: safe_name = Path(filename).name
  API->>S: write bytes to uploads/safe_name
  API->>C: classify_image(path)
  alt OPENAI_API_KEY present
    C->>O: chat.completions(prompt + base64 image)
    O-->>C: raw JSON text
    C->>C: parse_model_json() then to_classification()
  else no key (POC default)
    C->>C: stub_result() — filename heuristic
  end
  C-->>API: ClassificationResult
  API->>DB: insert_image(safe_name, path, result, designer)
  DB->>S: INSERT images + sync images_fts
  DB-->>API: ImageRecord
  API-->>UI: ImageRecord (JSON)
  UI->>UI: prepend to grid, auto-select
```

### 4b. Search / Filter (`GET /images`)

```mermaid
sequenceDiagram
  actor D as Designer
  participant UI as SearchFilters + App.tsx
  participant API as FastAPI /images
  participant DB as db.py
  participant S as SQLite

  D->>UI: change dropdown / type query
  UI->>UI: debounce 250 ms (useEffect)
  UI->>API: GET /images?garment_type=...&query=...
  API->>API: _build_filters() -> SearchFilters
  alt any(vars(filters).values())
    API->>DB: search_images(filters)
    DB->>DB: build WHERE clauses
    Note right of DB: query -> FTS MATCH (quoted/safe)<br/>garment/season -> json_extract =<br/>list fields -> json_extract LIKE<br/>year/month -> strftime(created_at)<br/>designer/location -> lower() =
    DB->>S: SELECT i.* [JOIN images_fts] WHERE ... ORDER BY created_at DESC
  else no filters
    API->>DB: list_images()
    DB->>S: SELECT * ORDER BY created_at DESC
  end
  S-->>DB: rows
  DB-->>API: list[ImageRecord]
  API-->>UI: JSON array
  UI->>UI: re-render ImageGrid
```

### 4c. Annotate (`PATCH /images/{id}`)

```mermaid
sequenceDiagram
  actor D as Designer
  participant AP as AnnotationPanel
  participant API as FastAPI PATCH /images/{id}
  participant DB as db.py
  participant S as SQLite

  D->>AP: edit tags / notes -> Save
  AP->>AP: split tags on comma, trim, drop blanks
  AP->>API: PATCH {designer, designer_tags, designer_notes}
  API->>DB: update_image(id, ...)
  DB->>DB: merge non-null fields onto existing record
  DB->>S: UPDATE images + re-sync images_fts
  DB-->>API: refreshed ImageRecord
  API-->>AP: updated record
  AP->>AP: onSaved -> patch grid + selection
```

## 5. Dataflow Diagram (DFD, level 1)

```mermaid
flowchart TB
  D(("Designer"))

  D -- "photo + name" --> P1["P1: Upload & Classify"]
  P1 -- "image bytes" --> DS1[("uploads/")]
  P1 -- "structured + description JSON" --> DS2[("images")]
  P1 -. "tokenized mirror" .-> DS3[("images_fts")]

  D -- "filters / natural query" --> P2["P2: Search & Filter"]
  DS2 --> P2
  DS3 -- "FTS MATCH" --> P2
  P2 -- "matching ImageRecords" --> D
  DS1 -- "image URLs" --> D

  D -- "tags / notes" --> P3["P3: Annotate"]
  P3 --> DS2
  P3 -. "re-sync" .-> DS3

  DS2 --> P4["P4: Build Filter Options"]
  P4 -- "dynamic dropdown values" --> D
```

Dropdown options are derived from existing rows (`get_filter_options` scans
`list_images()` and dedupes), never hardcoded.

## 6. Frontend Component & State Architecture

`App.tsx` is the single state owner; children are controlled and communicate
upward via callbacks.

```mermaid
flowchart TB
  subgraph App["App.tsx — owns all state"]
    ST["filters, images, selected,<br/>loading, error, uploading, designerName"]
  end

  App --> SF["SearchFilters<br/>(dropdowns from /filters)"]
  App --> IG["ImageGrid<br/>(visual grid of cards)"]
  App --> AP["AnnotationPanel<br/>(AI block + designer form)"]
  App --> API["api.ts<br/>(fetch wrappers)"]

  SF -- "onChange(filters)" --> App
  IG -- "onSelect(image)" --> App
  AP -- "onSaved(updated)" --> App
  API -- "HTTP" --> BE[("FastAPI :8000")]
```

- Debounced loading: `load()` is wrapped in a 250 ms timeout so typing does not
  fire a request per keystroke.
- Optimistic selection: after upload the new record is prepended and auto-selected;
  after a filter reload, selection is preserved by id or falls back to the first item.
- `refreshKey`: `SearchFilters` re-fetches dropdown options whenever
  `images.length` changes, so new attribute values appear after an upload.

## 7. End-to-End Implementation Reference

```mermaid
flowchart LR
  subgraph API["FastAPI routes"]
    H["GET /health"]
    F["GET /filters"]
    L["GET /images (+15 filter params)"]
    G["GET /images/{id}"]
    U["POST /images/upload"]
    R["POST /images/{id}/classify"]
    P["PATCH /images/{id}"]
    PV["POST /classify/preview"]
  end
  F --> dbF["db.get_filter_options"]
  L --> dbL["db.search_images / db.list_images"]
  G --> dbG["db.get_image"]
  U --> clsU["classifier.classify_image"] --> dbU["db.insert_image"]
  R --> clsR["classifier.classify_image"] --> dbR["db.update_image"]
  P --> dbP["db.update_image"]
  PV --> clsP["classifier.classify_image"]
```

| Method & path | Purpose | Calls |
|---|---|---|
| `GET /health` | liveness | — |
| `GET /filters` | dynamic dropdown options | `get_filter_options` |
| `GET /images` | list or filtered search | `search_images` / `list_images` |
| `GET /images/{id}` | single record | `get_image` |
| `POST /images/upload` | upload -> classify -> store | `classify_image` + `insert_image` |
| `POST /images/{id}/classify` | re-run AI on stored image | `classify_image` + `update_image` |
| `PATCH /images/{id}` | save designer tags/notes | `update_image` |
| `POST /classify/preview` | classify without saving a record | `classify_image` |

### Classification subsystem (`classifier.py`)

```mermaid
flowchart TB
  A["classify_image(path)"] --> B{"OPENAI_API_KEY set?"}
  B -- no --> S["stub_result()<br/>garment from filename,<br/>fixed placeholder attrs"]
  B -- yes --> C["OpenAI chat.completions<br/>gpt-4o-mini, temp 0.2,<br/>text prompt + base64 image"]
  C --> D["parse_model_json()<br/>strip json fences, json.loads"]
  D --> E["to_classification()"]
  E --> F["clean_list(): split strings / dedupe<br/>safe enum coercion -> OTHER / ALL_SEASON<br/>location dict -> LocationContext"]
  S --> R["ClassificationResult"]
  F --> R
```

The parse/normalize split (`parse_model_json` -> `to_classification`) is
deliberate: parsing is what the unit test targets, and normalization is where
every "model returned something weird" case is defended (unknown garment type ->
`other`, string instead of list -> split on commas, missing location -> empty
`LocationContext`).

## 8. Model Evaluation Pipeline (`eval/`)

```mermaid
flowchart LR
  IMG[("eval/images/*.jpg<br/>~52 Pexels photos")] --> EV["evaluate.py"]
  LBL[("eval/labels.csv<br/>expected attributes")] --> EV
  EV -- "per image" --> CLS["classifier.classify_image"]
  CLS -- "ClassificationResult.model_dump()" --> EV
  EV --> M{"per-field match?"}
  M -- "scalar fields" --> EX["exact (case-insensitive) =="]
  M -- "list fields" --> OV["set overlap >= 0.5"]
  EX --> RPT["Per-attribute accuracy table"]
  OV --> RPT
```

Two scoring strategies, chosen per field type: scalar fields require an exact match;
list fields count as correct if at least 50% of expected tags overlap — a sensible
tolerance for multi-label fashion attributes where model and human will not list
identical sets.

## 9. Known Limitations (POC scope)

- Per-request SQLite connections (`get_db()` opens/closes each call) — fine for a
  single-user POC; would be pooled under real load.
- `get_filter_options` loads all rows into memory to dedupe — O(n) per call,
  acceptable at POC scale, would become `SELECT DISTINCT` / an index at scale.
- AI-inferred location is a best guess, not capture GPS.
- No pagination, deduplication, or multi-user workspaces yet.
