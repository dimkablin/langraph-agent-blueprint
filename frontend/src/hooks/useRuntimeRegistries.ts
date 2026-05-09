import { useCallback, useEffect, useState } from "react";

import { fetchCommands, fetchSkills, fetchTools } from "../api/registries.ts";
import type { RegistryMap } from "../api/schemas.ts";

export function useRuntimeRegistries() {
  const [commands, setCommands] = useState<RegistryMap>({});
  const [skills, setSkills] = useState<RegistryMap>({});
  const [tools, setTools] = useState<RegistryMap>({});
  const [registryError, setRegistryError] = useState<string | null>(null);

  const refreshRegistries = useCallback(async () => {
    try {
      const [commandData, skillData, toolData] = await Promise.all([fetchCommands(), fetchSkills(), fetchTools()]);
      setCommands(commandData);
      setSkills(skillData);
      setTools(toolData);
      setRegistryError(null);
    } catch (error) {
      setRegistryError(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void refreshRegistries();
  }, [refreshRegistries]);

  return { commands, skills, tools, registryError, refreshRegistries };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
