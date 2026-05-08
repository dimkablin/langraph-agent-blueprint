import type { RegistryItem, RegistryMap } from "../api/schemas.ts";

export type RegistryGroupView = {
  title: string;
  items: RegistryItem[];
  emptyText: string;
};

export function registryItems(registry: RegistryMap): RegistryItem[] {
  return Object.entries(registry || {})
    .map(([name, item]) => ({ ...item, name: item.name || name }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function compactId(value: string | null | undefined): string {
  if (!value) return "new";
  return value.length > 18 ? `${value.slice(0, 18)}...` : value;
}
