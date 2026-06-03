const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8010";

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;

  constructor(status: number, statusText: string, body: string) {
    super(`${status} ${statusText}: ${body}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function currentUserId(): string {
  if (typeof globalThis.localStorage === "undefined") {
    return "dev-user";
  }
  return globalThis.localStorage.getItem("langgraph-agent-blueprint:user-id") || "dev-user";
}

export function userScopedHeaders(headers: HeadersInit = {}): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-User-Id": currentUserId(),
    ...(headers as Record<string, string>),
  };
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: userScopedHeaders(options.headers),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, response.statusText, body);
  }
  return (await response.json()) as T;
}
