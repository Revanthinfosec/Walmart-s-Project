import { useEffect, useState } from "react";
import { fetchFilterOptions } from "../api";
import type { FilterOptions, SearchFilters as Filters } from "../types";

type Props = {
  filters: Filters;
  onChange: (filters: Filters) => void;
  refreshKey?: number;
};

type FieldConfig = {
  key: keyof Filters;
  label: string;
  optionKey: keyof FilterOptions;
};

const FIELDS: FieldConfig[] = [
  { key: "garment_type", label: "Garment", optionKey: "garment_type" },
  { key: "style", label: "Style", optionKey: "style_tags" },
  { key: "material", label: "Material", optionKey: "materials" },
  { key: "color", label: "Color", optionKey: "colors" },
  { key: "pattern", label: "Pattern", optionKey: "patterns" },
  { key: "occasion", label: "Occasion", optionKey: "occasions" },
  { key: "consumer_profile", label: "Consumer", optionKey: "consumer_profiles" },
  { key: "trend_note", label: "Trend", optionKey: "trend_notes" },
  { key: "continent", label: "Continent", optionKey: "continents" },
  { key: "country", label: "Country", optionKey: "countries" },
  { key: "city", label: "City", optionKey: "cities" },
  { key: "season", label: "Season", optionKey: "season" },
  { key: "year", label: "Year", optionKey: "years" },
  { key: "month", label: "Month", optionKey: "months" },
  { key: "designer", label: "Designer", optionKey: "designers" },
];

export function SearchFilters({ filters, onChange, refreshKey = 0 }: Props) {
  const [options, setOptions] = useState<FilterOptions | null>(null);

  useEffect(() => {
    fetchFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, [refreshKey]);

  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

  return (
    <section className="filters">
      <label className="search-wide">
        Search
        <input
          type="search"
          placeholder='Try "embroidered neckline" or "artisan market"'
          value={filters.query ?? ""}
          onChange={(e) => set({ query: e.target.value || undefined })}
        />
      </label>

      {FIELDS.map(({ key, label, optionKey }) => {
        const values = options?.[optionKey] ?? [];
        return (
          <label key={key}>
            {label}
            <select
              value={filters[key] ?? ""}
              onChange={(e) => set({ [key]: e.target.value || undefined })}
              disabled={!values.length}
            >
              <option value="">{values.length ? "All" : "No data yet"}</option>
              {values.map((value) => (
                <option key={value} value={value}>
                  {value.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
        );
      })}
    </section>
  );
}
