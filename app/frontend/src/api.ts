import type { DesignerUpdate, FilterOptions, ImageRecord, SearchFilters } from "./types";

const API = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

function queryString(filters: SearchFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchFilterOptions() {
  const res = await fetch(`${API}/filters`);
  if (!res.ok) throw new Error("filters failed");
  return res.json() as Promise<FilterOptions>;
}

export async function fetchImages(filters: SearchFilters = {}) {
  const res = await fetch(`${API}/images${queryString(filters)}`);
  if (!res.ok) throw new Error("fetch failed");
  return res.json() as Promise<ImageRecord[]>;
}

export async function uploadImage(file: File, designer?: string) {
  const body = new FormData();
  body.append("file", file);
  if (designer) body.append("designer", designer);

  const res = await fetch(`${API}/images/upload`, { method: "POST", body });
  if (!res.ok) throw new Error("upload failed");
  return res.json() as Promise<ImageRecord>;
}

export async function updateDesignerFields(id: number, payload: DesignerUpdate) {
  const res = await fetch(`${API}/images/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("save failed");
  return res.json() as Promise<ImageRecord>;
}

export function imageUrl(image: ImageRecord) {
  const name = image.file_path.split("/").pop() ?? image.filename;
  return `${API}/uploads/${name}`;
}
