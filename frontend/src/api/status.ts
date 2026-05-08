import { requestJson } from "./client.ts";
import type {
  ConfigShowDTO,
  ConfigValidateDTO,
  HookStatusDTO,
  MCPStatusDTO,
  ObservabilityStatusDTO,
  PluginStatusDTO,
} from "./schemas.ts";

export type RuntimeStatus = {
  plugins: PluginStatusDTO | null;
  hooks: HookStatusDTO | null;
  config: ConfigShowDTO | null;
  configValidation: ConfigValidateDTO | null;
  observability: ObservabilityStatusDTO | null;
  mcp: MCPStatusDTO | null;
};

export async function fetchRuntimeStatus(): Promise<RuntimeStatus> {
  const [plugins, hooks, config, configValidation, observability, mcp] = await Promise.allSettled([
    requestJson<PluginStatusDTO>("/plugins"),
    requestJson<HookStatusDTO>("/hooks"),
    requestJson<ConfigShowDTO>("/config"),
    requestJson<ConfigValidateDTO>("/config/validate"),
    requestJson<ObservabilityStatusDTO>("/observability"),
    requestJson<MCPStatusDTO>("/mcp"),
  ]);
  return {
    plugins: settledValue(plugins),
    hooks: settledValue(hooks),
    config: settledValue(config),
    configValidation: settledValue(configValidation),
    observability: settledValue(observability),
    mcp: settledValue(mcp),
  };
}

function settledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}
