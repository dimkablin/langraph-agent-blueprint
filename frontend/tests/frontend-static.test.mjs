import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test("React CLI frontend exposes terminal shell and all hint surfaces", () => {
  const app = readFileSync(join(root, "frontend", "src", "App.jsx"), "utf8");
  const hints = readFileSync(join(root, "frontend", "src", "commandHints.js"), "utf8");

  assert.match(app, /function App/);
  assert.match(app, /TerminalShell/);
  assert.match(app, /HintPanel/);
  assert.match(app, /PermissionPrompt/);
  assert.match(hints, /\/help/);
  assert.match(hints, /\/skills/);
  assert.match(hints, /read_file/);
  assert.match(hints, /debug/);
});

test("API client calls graph-facing backend endpoints only", () => {
  const api = readFileSync(join(root, "frontend", "src", "api.js"), "utf8");

  assert.match(api, /\/chat/);
  assert.match(api, /\/approval/);
  assert.doesNotMatch(api, /\/tools\/execute/);
});

test("backend frontend contract exposes typed streaming, sessions, and status routes", () => {
  const schemas = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "schemas.py"), "utf8");
  const server = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "server.py"), "utf8");
  const chatRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_chat.py"), "utf8");
  const sessionRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_sessions.py"), "utf8");
  const statusRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_status.py"), "utf8");

  assert.match(schemas, /class RuntimeEventDTO/);
  assert.match(schemas, /class StreamFrame/);
  assert.match(schemas, /class PermissionDecisionDTO/);
  assert.match(schemas, /class SessionDetailDTO/);
  assert.match(schemas, /class ContextStateDTO/);
  assert.match(chatRoutes, /text\/event-stream/);
  assert.match(sessionRoutes, /\/sessions\/\{session_id\}\/context/);
  assert.match(sessionRoutes, /\/sessions\/\{session_id\}\/child-runs/);
  assert.match(statusRoutes, /\/config\/explain/);
  assert.match(statusRoutes, /\/observability/);
  assert.doesNotMatch(server, /@api\.get\("\/(commands|skills|tools)"\)/);
});

test("JSX modules import React for Vite classic JSX runtime", () => {
  const app = readFileSync(join(root, "frontend", "src", "App.jsx"), "utf8");
  const components = readFileSync(join(root, "frontend", "src", "components.jsx"), "utf8");

  assert.match(app, /import React,\s*\{/);
  assert.match(components, /import React from "react"/);
});
