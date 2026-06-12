# Model evaluation

## Dataset

Use 50–100 open-source street fashion or garment photos. Good sources:

- [Pexels fashion search](https://www.pexels.com/search/fashion/)
- [Unsplash fashion](https://unsplash.com/s/photos/fashion)

Save images to `eval/images/` and add one row per file in `labels.csv`.

## Run

```bash
python eval/download_images.py          # fetch 52 Pexels images
python eval/apply_manual_labels.py      # build labels.csv
export OPENAI_API_KEY=your_key          # required for meaningful eval
python eval/evaluate.py
```

Hand-reviewed rows live in `manual_labels.py`. Expand that file as you spot-check more images.

## Labeling tips

- `style_tags`, `materials`, `colors`, `patterns`, `occasion`, and `trend_notes` can be comma-separated.
- Location columns are plain strings (`continent`, `country`, `city`).
- Keep descriptions short — they help FTS search tests, not accuracy scoring.

## Sample workflow

1. Download 50+ images with varied garments and contexts.
2. Manually label expected attributes in `labels.csv`.
3. Run the script and paste results into the root `README.md` evaluation section.
