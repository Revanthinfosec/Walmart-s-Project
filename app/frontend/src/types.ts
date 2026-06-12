export type GarmentType =
  | "dress"
  | "top"
  | "bottom"
  | "outerwear"
  | "footwear"
  | "accessory"
  | "other";

export type Season = "spring" | "summer" | "fall" | "winter" | "all_season";

export interface LocationContext {
  continent: string;
  country: string;
  city: string;
}

export interface ClassificationResult {
  garment_type: GarmentType;
  style_tags: string[];
  materials: string[];
  colors: string[];
  patterns: string[];
  season: Season;
  occasion: string[];
  consumer_profile: string;
  trend_notes: string[];
  location: LocationContext;
  description: string;
}

export interface ImageRecord {
  id: number;
  filename: string;
  file_path: string;
  classification: ClassificationResult;
  designer: string | null;
  designer_tags: string[];
  designer_notes: string | null;
  created_at: string;
}

export interface SearchFilters {
  query?: string;
  garment_type?: string;
  season?: string;
  color?: string;
  style?: string;
  material?: string;
  pattern?: string;
  occasion?: string;
  consumer_profile?: string;
  trend_note?: string;
  continent?: string;
  country?: string;
  city?: string;
  year?: string;
  month?: string;
  designer?: string;
}

export interface FilterOptions {
  garment_type: string[];
  season: string[];
  colors: string[];
  style_tags: string[];
  materials: string[];
  patterns: string[];
  occasions: string[];
  consumer_profiles: string[];
  trend_notes: string[];
  continents: string[];
  countries: string[];
  cities: string[];
  years: string[];
  months: string[];
  designers: string[];
}

export interface DesignerUpdate {
  designer?: string;
  designer_tags?: string[];
  designer_notes?: string;
}
