import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const srcRoot = join(root, "frontend", "src");

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function sourceFiles(dir = srcRoot) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (/\.(ts|tsx|css)$/.test(entry.name)) return [path];
    return [];
  });
}

function sourceText() {
  return sourceFiles()
    .map((path) => `\n// ${relative(srcRoot, path)}\n${readFileSync(path, "utf8")}`)
    .join("\n");
}

test("TypeScript runtime frontend entrypoint is active", () => {
  const index = readFileSync(join(root, "frontend", "index.html"), "utf8");
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");

  assert.match(index, /\/src\/main\.tsx/);
  assert.match(app, /streamChat/);
  assert.match(app, /PermissionPanel/);
  assert.match(app, /SessionsPanel/);
  assert.match(app, /ContextPanel/);
});

test("frontend uses graph-facing backend endpoints only", () => {
  const text = sourceText();

  assert.match(text, /\/chat\/stream/);
  assert.match(text, /\/approval/);
  assert.match(text, /\/sessions/);
  assert.match(text, /\/commands/);
  assert.match(text, /\/skills/);
  assert.match(text, /\/tools/);
  assert.doesNotMatch(text, /\/tools\/execute/);
  assert.doesNotMatch(text, /query\/stream/);
  assert.doesNotMatch(text, /luxms|otp-login|login_as/i);
});

test("runtime API and reducer layers are separated from components", () => {
  const api = readFileSync(join(srcRoot, "api", "stream.ts"), "utf8");
  const reducer = readFileSync(join(srcRoot, "runtime", "reducer.ts"), "utf8");
  const componentFiles = sourceFiles(join(srcRoot, "components"));
  const components = componentFiles.map((path) => readFileSync(path, "utf8")).join("\n");

  assert.match(api, /fetch\(apiUrl\("\/chat\/stream"\)/);
  assert.match(reducer, /applyRuntimeEvent/);
  assert.doesNotMatch(components, /fetch\(/);
  assert.doesNotMatch(components, /\/chat|\/approval|\/tools/);
});

test("backend frontend contract still exposes typed streaming, sessions, and status routes", () => {
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
