import { useCallback, useEffect, useState } from "react";

import { archiveConversation, deleteConversation, fetchConversations, renameConversation } from "../api/conversations.ts";
import type { SessionListItemDTO } from "../api/schemas.ts";

export function useRuntimeSessions() {
  const [sessions, setSessions] = useState<SessionListItemDTO[]>([]);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await fetchConversations());
      setSessionError(null);
    } catch (error) {
      setSessionError(errorMessage(error));
    }
  }, []);

  const renameSession = useCallback(
    async (sessionId: string, title: string) => {
      try {
        await renameConversation(sessionId, title);
        await refreshSessions();
        setSessionError(null);
      } catch (error) {
        setSessionError(errorMessage(error));
      }
    },
    [refreshSessions],
  );

  const archiveSession = useCallback(
    async (sessionId: string) => {
      try {
        await archiveConversation(sessionId);
        await refreshSessions();
        setSessionError(null);
      } catch (error) {
        setSessionError(errorMessage(error));
      }
    },
    [refreshSessions],
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await deleteConversation(sessionId);
        await refreshSessions();
        setSessionError(null);
      } catch (error) {
        setSessionError(errorMessage(error));
      }
    },
    [refreshSessions],
  );

  const reportSessionError = useCallback((error: unknown) => {
    setSessionError(errorMessage(error));
  }, []);

  const clearSessionError = useCallback(() => {
    setSessionError(null);
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  return { sessions, sessionError, refreshSessions, reportSessionError, clearSessionError, renameSession, archiveSession, deleteSession };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
