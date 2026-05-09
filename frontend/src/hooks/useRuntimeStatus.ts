import { useCallback, useEffect, useState } from "react";

import { fetchRuntimeStatus, type RuntimeStatus } from "../api/status.ts";

export function useRuntimeStatus() {
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);

  const refreshRuntimeStatus = useCallback(async () => {
    setRuntimeStatus(await fetchRuntimeStatus());
  }, []);

  useEffect(() => {
    void refreshRuntimeStatus();
  }, [refreshRuntimeStatus]);

  return { runtimeStatus, refreshRuntimeStatus };
}
