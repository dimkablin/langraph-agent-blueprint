import { useCallback, useEffect, useState } from "react";

import { fetchSessions } from "../api/sessions.ts";
import type { SessionListItemDTO } from "../api/schemas.ts";

export function useRuntimeSessions() {
  const [sessions, setSessions] = useState<SessionListItemDTO[]>([]);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await fetchSessions());
      setSessionError(null);
    } catch (error) {
      setSessionError(errorMessage(error));
    }
  }, []);

  const reportSessionError = useCallback((error: unknown) => {
    setSessionError(errorMessage(error));
  }, []);

  const clearSessionError = useCallback(() => {
    setSessionError(null);
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  return { sessions, sessionError, refreshSessions, reportSessionError, clearSessionError };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
