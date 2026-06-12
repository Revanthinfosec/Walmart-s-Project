import { useEffect, useState } from "react";
import { updateDesignerFields } from "../api";
import type { ImageRecord } from "../types";

type Props = {
  image: ImageRecord | null;
  onSaved: (image: ImageRecord) => void;
};

function joinList(items: string[]) {
  return items.length ? items.join(", ") : "—";
}

export function AnnotationPanel({ image, onSaved }: Props) {
  const [designer, setDesigner] = useState("");
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDesigner(image?.designer ?? "");
    setTags(image?.designer_tags.join(", ") ?? "");
    setNotes(image?.designer_notes ?? "");
    setError(null);
  }, [image]);

  if (!image) {
    return <aside className="annotation-panel empty">Pick a look to see AI tags and add your own notes.</aside>;
  }

  async function save() {
    if (!image) return;
    setSaving(true);
    setError(null);
    try {
      const designer_tags = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      onSaved(
        await updateDesignerFields(image.id, {
          designer: designer || undefined,
          designer_tags,
          designer_notes: notes,
        }),
      );
    } catch {
      setError("Couldn't save your edits.");
    } finally {
      setSaving(false);
    }
  }

  const c = image.classification;
  const captured = new Date(image.created_at);

  return (
    <aside className="annotation-panel">
      <h2>{image.filename}</h2>

      <section className="meta-block ai-block">
        <h3>AI-generated</h3>
        <p className="ai-description">{c.description}</p>
        <dl className="classification-details">
          <div><dt>Type</dt><dd>{c.garment_type}</dd></div>
          <div><dt>Style</dt><dd>{joinList(c.style_tags)}</dd></div>
          <div><dt>Material</dt><dd>{joinList(c.materials)}</dd></div>
          <div><dt>Colors</dt><dd>{joinList(c.colors)}</dd></div>
          <div><dt>Pattern</dt><dd>{joinList(c.patterns)}</dd></div>
          <div><dt>Season</dt><dd>{c.season.replace("_", " ")}</dd></div>
          <div><dt>Occasion</dt><dd>{joinList(c.occasion)}</dd></div>
          <div><dt>Consumer</dt><dd>{c.consumer_profile || "—"}</dd></div>
          <div><dt>Trends</dt><dd>{joinList(c.trend_notes)}</dd></div>
          <div><dt>Location</dt><dd>{[c.location.city, c.location.country, c.location.continent].filter(Boolean).join(", ") || "—"}</dd></div>
        </dl>
      </section>

      <section className="meta-block designer-block">
        <h3>Designer input</h3>
        <p className="hint">Captured {captured.toLocaleDateString()} — filters use this date for year/month.</p>

        <label>
          Designer name
          <input value={designer} onChange={(e) => setDesigner(e.target.value)} placeholder="Who captured this look?" />
        </label>

        <label>
          Your tags
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="resort, pleating, reference for SS26"
          />
        </label>

        <label>
          Notes & observations
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Market stall in Marrakech — love the sleeve detail..."
          />
        </label>
      </section>

      {error && <p className="error">{error}</p>}

      <button type="button" onClick={save} disabled={saving}>
        {saving ? "Saving..." : "Save designer edits"}
      </button>
    </aside>
  );
}
