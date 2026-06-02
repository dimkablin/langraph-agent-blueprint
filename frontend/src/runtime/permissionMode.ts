import type { PermissionMode } from "../api/schemas.ts";

export type { PermissionMode };

export type PermissionModeOption = {
  id: PermissionMode;
  label: string;
  description: string;
  risk?: "default" | "elevated";
};

export const DEFAULT_PERMISSION_MODE: PermissionMode = "default";
export const FULL_ACCESS_PERMISSION_MODE: PermissionMode = "bypass_read_only";

export const PERMISSION_MODE_STORAGE_KEY = "lgab.permissionMode";

export const PERMISSION_MODE_OPTIONS: PermissionModeOption[] = [
  {
    id: DEFAULT_PERMISSION_MODE,
    label: "Разрешение по умолчанию",
    description: "Агент запрашивает подтверждение для действий с побочными эффектами.",
    risk: "default",
  },
  {
    id: FULL_ACCESS_PERMISSION_MODE,
    label: "Полный доступ",
    description: "Расширяет доступ инструментов для следующего запуска. Используйте только в доверенном workspace.",
    risk: "elevated",
  },
];

export function permissionModeOptionById(mode: PermissionMode): PermissionModeOption {
  return PERMISSION_MODE_OPTIONS.find((option) => option.id === mode) ?? PERMISSION_MODE_OPTIONS[0];
}

export type PermissionModeStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export function loadPermissionMode(storage: PermissionModeStorage | null = browserStorage()): PermissionMode {
  if (!storage) return DEFAULT_PERMISSION_MODE;
  try {
    const value = storage.getItem(PERMISSION_MODE_STORAGE_KEY);
    return isSupportedPermissionMode(value) ? value : DEFAULT_PERMISSION_MODE;
  } catch {
    return DEFAULT_PERMISSION_MODE;
  }
}

export function savePermissionMode(mode: PermissionMode, storage: PermissionModeStorage | null = browserStorage()): void {
  if (!storage) return;
  try {
    if (mode === DEFAULT_PERMISSION_MODE) {
      storage.removeItem(PERMISSION_MODE_STORAGE_KEY);
    } else {
      storage.setItem(PERMISSION_MODE_STORAGE_KEY, mode);
    }
  } catch {
    // Ignore unavailable or quota-limited browser storage.
  }
}

function isSupportedPermissionMode(value: string | null): value is PermissionMode {
  return value === DEFAULT_PERMISSION_MODE || value === FULL_ACCESS_PERMISSION_MODE;
}

function browserStorage(): PermissionModeStorage | null {
  return typeof localStorage === "undefined" ? null : localStorage;
}
