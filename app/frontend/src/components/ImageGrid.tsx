import { imageUrl } from "../api";
import type { ImageRecord } from "../types";

type Props = {
  images: ImageRecord[];
  selectedId: number | null;
  onSelect: (image: ImageRecord) => void;
};

export function ImageGrid({ images, selectedId, onSelect }: Props) {
  if (!images.length) {
    return <p className="empty-state">Nothing here yet — upload field photos to start your library.</p>;
  }

  return (
    <div className="image-grid">
      {images.map((image) => {
        const c = image.classification;
        return (
          <button
            key={image.id}
            type="button"
            className={`image-card ${selectedId === image.id ? "selected" : ""}`}
            onClick={() => onSelect(image)}
          >
            <img src={imageUrl(image)} alt={c.description || image.filename} />
            <div className="image-card-meta">
              <strong>{c.garment_type}</strong>
              <span>{c.style_tags[0] ?? c.materials[0] ?? c.colors[0] ?? "untagged"}</span>
              {image.designer_tags.length > 0 && (
                <span className="designer-pill">{image.designer_tags[0]}</span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
