import assert from "node:assert/strict";
import test from "node:test";

import { mcpServerEditorTitle, normalizeMCPSettingsSnapshot } from "../src/runtime/mcpSettings.ts";

test("normalizes MCP snapshot with redacted config details for settings editor", () => {
  const state = normalizeMCPSettingsSnapshot(
    {
      servers: [{ name: "chrome_devtools", status: "configured", transport: "stdio" }],
      tools: {
        "mcp.chrome_devtools.inspect": { server_name: "chrome_devtools" },
      },
      resources: {
        chrome_devtools: [{ uri: "browser://tabs" }],
      },
      prompts: {
        chrome_devtools: [{ prompt_name: "debug" }],
      },
      invalid_servers: [],
      warnings: [{ message: "Discovery has not been run" }],
      errors: [],
    },
    {
      servers: {
        chrome_devtools: {
          enabled: true,
          transport: "stdio",
          trust_level: "trusted",
          stdio: {
            command: "cmd",
            args: ["/c", "npx", "-y", "chrome-devtools-mcp@latest"],
            env: { SystemRoot: "C:\\Windows" },
            cwd: "~/code",
          },
        },
      },
    },
  );

  assert.equal(state.servers.length, 1);
  assert.equal(state.servers[0].name, "chrome_devtools");
  assert.equal(state.servers[0].transport, "stdio");
  assert.equal(state.servers[0].enabled, true);
  assert.equal(state.servers[0].trustLevel, "trusted");
  assert.equal(state.servers[0].stdio.command, "cmd");
  assert.deepEqual(state.servers[0].stdio.args, ["/c", "npx", "-y", "chrome-devtools-mcp@latest"]);
  assert.deepEqual(state.servers[0].stdio.env, [{ key: "SystemRoot", value: "C:\\Windows" }]);
  assert.equal(state.servers[0].stdio.cwd, "~/code");
  assert.equal(state.servers[0].counts.tools, 1);
  assert.equal(state.servers[0].counts.resources, 1);
  assert.equal(state.servers[0].counts.prompts, 1);
  assert.equal(state.warnings.length, 1);
  assert.equal(mcpServerEditorTitle(state.servers[0]), "Обновление Chrome_devtools MCP");
});

test("normalizes streamable HTTP MCP config for future safe editing UI", () => {
  const state = normalizeMCPSettingsSnapshot(
    {
      servers: [{ name: "remote_docs", status: "disabled", transport: "streamable_http" }],
      tools: {},
      resources: {},
      prompts: {},
      invalid_servers: [],
      warnings: [],
      errors: [],
    },
    {
      servers: {
        remote_docs: {
          enabled: false,
          transport: "streamable_http",
          trust_level: "untrusted",
          http: {
            url: "https://mcp.example.com/mcp",
            headers: { Authorization: "***", "X-Team": "runtime" },
            timeout_seconds: 30,
          },
        },
      },
    },
  );

  assert.equal(state.servers[0].transport, "streamable_http");
  assert.equal(state.servers[0].enabled, false);
  assert.equal(state.servers[0].http.url, "https://mcp.example.com/mcp");
  assert.deepEqual(state.servers[0].http.headers, [
    { key: "Authorization", value: "***" },
    { key: "X-Team", value: "runtime" },
  ]);
});
