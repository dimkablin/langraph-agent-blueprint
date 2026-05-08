import { requestJson } from "./client.ts";
import type { RegistryMap } from "./schemas.ts";

export function fetchCommands(): Promise<RegistryMap> {
  return requestJson<RegistryMap>("/commands");
}

export function fetchSkills(): Promise<RegistryMap> {
  return requestJson<RegistryMap>("/skills");
}

export function fetchTools(): Promise<RegistryMap> {
  return requestJson<RegistryMap>("/tools");
}
