const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json();
}

export function sendChat({ message, sessionId, threadId }) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      session_id: sessionId || null,
      thread_id: threadId || null,
    }),
  });
}

export function sendApproval({ threadId, approved, reason }) {
  return request("/approval", {
    method: "POST",
    body: JSON.stringify({
      thread_id: threadId,
      decision: { approved, reason },
    }),
  });
}

export function fetchCommands() {
  return request("/commands");
}

export function fetchSkills() {
  return request("/skills");
}

export function fetchTools() {
  return request("/tools");
}

