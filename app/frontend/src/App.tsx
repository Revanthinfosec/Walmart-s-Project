import { useCallback, useEffect, useState } from "react";
import { fetchImages, uploadImage } from "./api";
import { AnnotationPanel } from "./components/AnnotationPanel";
import { ImageGrid } from "./components/ImageGrid";
import { SearchFilters } from "./components/SearchFilters";
import type { ImageRecord, SearchFilters as Filters } from "./types";
import "./App.css";

export default function App() {
  const [filters, setFilters] = useState<Filters>({});
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [selected, setSelected] = useState<ImageRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [designerName, setDesignerName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchImages(filters);
      setImages(data);
      setSelected((current) => data.find((img) => img.id === current?.id) ?? data[0] ?? null);
    } catch {
      setError("Can't reach the server — start the backend on port 8000.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const timer = window.setTimeout(load, 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const saved = await uploadImage(file, designerName || undefined);
      setImages((prev) => [saved, ...prev]);
      setSelected(saved);
    } catch {
      setError("Upload didn't work. Try again.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Fashion Inspiration</h1>
          <p>Upload field photos, auto-classify garments, filter your library, and layer on designer notes.</p>
        </div>
        <div className="upload-area">
          <input
            type="text"
            className="designer-input"
            placeholder="Your name (optional)"
            value={designerName}
            onChange={(e) => setDesignerName(e.target.value)}
          />
          <label className="upload-button">
            {uploading ? "Uploading..." : "Upload photo"}
            <input type="file" accept="image/*" onChange={onUpload} disabled={uploading} hidden />
          </label>
        </div>
      </header>

      <SearchFilters filters={filters} onChange={setFilters} refreshKey={images.length} />

      {error && <p className="error banner">{error}</p>}
      {loading && <p className="loading">Loading library...</p>}

      <main className="content-layout">
        <ImageGrid images={images} selectedId={selected?.id ?? null} onSelect={setSelected} />
        <AnnotationPanel
          image={selected}
          onSaved={(updated) => {
            setImages((prev) => prev.map((img) => (img.id === updated.id ? updated : img)));
            setSelected(updated);
          }}
        />
      </main>
    </div>
  );
}
