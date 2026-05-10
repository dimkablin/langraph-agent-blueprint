import type { MCPStatusDTO } from "../api/schemas.ts";

export type MCPSettingsTransport = "stdio" | "streamable_http";

export type MCPKeyValue = {
  key: string;
  value: string;
};

export type MCPSettingsServer = {
  name: string;
  enabled: boolean;
  transport: MCPSettingsTransport;
  status: string;
  trustLevel: string;
  error: string | null;
  stdio: {
    command: string;
    args: string[];
    env: MCPKeyValue[];
    envPassthrough: string[];
    cwd: string;
  };
  http: {
    url: string;
    bearerTokenEnv: string;
    headers: MCPKeyValue[];
    headerEnv: MCPKeyValue[];
  };
  counts: {
    tools: number;
    resources: number;
    prompts: number;
  };
};

export type MCPSettingsSnapshot = {
  servers: MCPSettingsServer[];
  warnings: string[];
  invalidServers: string[];
};

export function normalizeMCPSettingsSnapshot(status: MCPStatusDTO | null, config: unknown): MCPSettingsSnapshot {
  const states = Array.isArray(status?.servers) ? status.servers.filter(isRecord) : [];
  const configServers = serverConfigRecords(config);
  const names = new Set<string>();
  for (const state of states) {
    const name = stringValue(state.name);
    if (name) names.add(name);
  }
  for (const name of Object.keys(configServers)) {
    names.add(name);
  }

  return {
    servers: [...names].map((name) => normalizeServer(name, states.find((state) => state.name === name), configServers[name], status)),
    warnings: rowsToMessages(status?.warnings),
    invalidServers: rowsToMessages(status?.invalid_servers),
  };
}

export function emptyMCPServerDraft(transport: MCPSettingsTransport): MCPSettingsServer {
  return {
    name: "",
    enabled: true,
    transport,
    status: "draft",
    trustLevel: "untrusted",
    error: null,
    stdio: {
      command: "",
      args: [""],
      env: [{ key: "", value: "" }],
      envPassthrough: [""],
      cwd: "",
    },
    http: {
      url: "",
      bearerTokenEnv: "MCP_BEARER_TOKEN",
      headers: [{ key: "", value: "" }],
      headerEnv: [{ key: "", value: "" }],
    },
    counts: {
      tools: 0,
      resources: 0,
      prompts: 0,
    },
  };
}

export function mcpServerEditorTitle(server: MCPSettingsServer): string {
  const name = server.name ? `${server.name[0].toUpperCase()}${server.name.slice(1)}` : "Custom";
  return `Обновление ${name} MCP`;
}

function normalizeServer(
  name: string,
  state: Record<string, unknown> | undefined,
  config: Record<string, unknown> | undefined,
  status: MCPStatusDTO | null,
): MCPSettingsServer {
  const transport = transportValue(config?.transport ?? state?.transport);
  const stdio = isRecord(config?.stdio) ? config.stdio : {};
  const http = isRecord(config?.http) ? config.http : {};
  return {
    name,
    enabled: typeof config?.enabled === "boolean" ? config.enabled : state?.status !== "disabled",
    transport,
    status: stringValue(state?.status) || "configured",
    trustLevel: stringValue(config?.trust_level) || "untrusted",
    error: stringValue(state?.error) || null,
    stdio: {
      command: stringValue(stdio.command),
      args: stringArray(stdio.args),
      env: keyValueRows(stdio.env),
      envPassthrough: stringArray(stdio.env_passthrough ?? stdio.env_passthrough_keys ?? config?.env_passthrough),
      cwd: stringValue(stdio.cwd),
    },
    http: {
      url: stringValue(http.url),
      bearerTokenEnv: stringValue(http.bearer_token_env) || "MCP_BEARER_TOKEN",
      headers: keyValueRows(http.headers),
      headerEnv: keyValueRows(http.header_env ?? http.headers_from_env),
    },
    counts: {
      tools: countTools(status?.tools, name),
      resources: countList(status?.resources?.[name]),
      prompts: countList(status?.prompts?.[name]),
    },
  };
}

function serverConfigRecords(config: unknown): Record<string, Record<string, unknown>> {
  const root = isRecord(config) ? config : {};
  const rawServers = isRecord(root.servers) ? root.servers : root;
  const servers: Record<string, Record<string, unknown>> = {};
  for (const [name, value] of Object.entries(rawServers)) {
    if (isRecord(value)) servers[name] = value;
  }
  return servers;
}

function countTools(tools: MCPStatusDTO["tools"] | undefined, serverName: string): number {
  if (!tools) return 0;
  return Object.values(tools).filter((tool) => isRecord(tool) && tool.server_name === serverName).length;
}

function countList(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

function rowsToMessages(rows: unknown): string[] {
  if (!Array.isArray(rows)) return [];
  return rows.map((row) => {
    if (!isRecord(row)) return String(row);
    return stringValue(row.message) || stringValue(row.error) || JSON.stringify(row);
  });
}

function keyValueRows(value: unknown): MCPKeyValue[] {
  if (!isRecord(value)) return [];
  return Object.entries(value).map(([key, raw]) => ({ key, value: String(raw ?? "") }));
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? ""));
}

function transportValue(value: unknown): MCPSettingsTransport {
  return value === "streamable_http" ? "streamable_http" : "stdio";
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
