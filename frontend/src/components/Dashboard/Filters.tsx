import { IMFilters } from "./IMFilters";
import type { FilterState } from "./IMFilters";

export type { FilterState } from "./IMFilters";

interface FiltersProps {
  onFilterChange: (filters: FilterState) => void;
}

export function Filters({ onFilterChange }: FiltersProps) {
  return <IMFilters onFilterChange={onFilterChange} />;
}
