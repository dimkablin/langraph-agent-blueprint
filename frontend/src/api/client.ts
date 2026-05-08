const viteEnv = typeof import.meta !== "undefined" && "env" in import.meta ? import.meta.env as Record<string, string | undefined> : {};
const API_BASE_URL = viteEnv.VITE_API_BASE_URL || "http://127.0.0.1:8000";

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

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, response.statusText, body);
  }
  return (await response.json()) as T;
}
