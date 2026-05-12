export type ActiveSessionStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem?(key: string): void;
};

type PersistedActiveSession = {
  sessionId: string;
};

export const ACTIVE_SESSION_STORAGE_KEY = "lg-agent-active-session";

export function loadActiveSessionId(storage: ActiveSessionStorage | null = browserStorage()): string | null {
  if (!storage) return null;
  const raw = safeGetItem(storage, ACTIVE_SESSION_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedActiveSession>;
    return normalizeSessionId(parsed.sessionId);
  } catch {
    return null;
  }
}

export function saveActiveSessionId(sessionId: string | null | undefined, storage: ActiveSessionStorage | null = browserStorage()): string | null {
  const normalized = normalizeSessionId(sessionId);
  if (!normalized) {
    clearActiveSessionId(storage);
    return null;
  }
  storage?.setItem(ACTIVE_SESSION_STORAGE_KEY, JSON.stringify({ sessionId: normalized } satisfies PersistedActiveSession));
  return normalized;
}

export function clearActiveSessionId(storage: ActiveSessionStorage | null = browserStorage()): void {
  storage?.removeItem?.(ACTIVE_SESSION_STORAGE_KEY);
}

function normalizeSessionId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 && trimmed.length <= 160 ? trimmed : null;
}

function safeGetItem(storage: ActiveSessionStorage, key: string): string | null {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function browserStorage(): ActiveSessionStorage | null {
  return typeof localStorage === "undefined" ? null : localStorage;
}
