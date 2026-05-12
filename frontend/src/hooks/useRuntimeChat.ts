import { useCallback, useEffect, useRef, useState } from "react";

import { sendApproval } from "../api/approval.ts";
import { fetchSessionContext, fetchSessionDetail } from "../api/sessions.ts";
import { streamChat } from "../api/stream.ts";
import { clearActiveSessionId, loadActiveSessionId, saveActiveSessionId } from "../runtime/activeSession.ts";
import { DEFAULT_MODEL_INTELLIGENCE_LEVEL, type ModelIntelligenceLevel } from "../runtime/modelIntelligence.ts";
import {
  appendUserMessage,
  applyChatResponse,
  applyContextState,
  applyRuntimeEvent,
  applySessionDetail,
  applyStreamFrame,
  createInitialRuntimeState,
  markStreamingStopped,
  setThreadId,
} from "../runtime/reducer.ts";

type UseRuntimeChatOptions = {
  projectId?: string | null;
  onSessionsChanged?: () => Promise<void> | void;
  onSessionError?: (error: unknown) => void;
  clearSessionError?: () => void;
};

export function useRuntimeChat({ projectId, onSessionsChanged, onSessionError, clearSessionError }: UseRuntimeChatOptions = {}) {
  const [runtimeState, setRuntimeState] = useState(createInitialRuntimeState);
  const [modelIntelligenceLevel, setModelIntelligenceLevel] = useState<ModelIntelligenceLevel>(DEFAULT_MODEL_INTELLIGENCE_LEVEL);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const sessionLoadVersionRef = useRef(0);

  useEffect(() => () => abortRef.current?.abort(), []);

  const refreshSessions = useCallback(async () => {
    await onSessionsChanged?.();
  }, [onSessionsChanged]);

  const loadSession = useCallback(
    async (sessionId: string) => {
      const loadVersion = ++sessionLoadVersionRef.current;
      try {
        const detail = await fetchSessionDetail(sessionId);
        const context = await fetchSessionContext(sessionId);
        if (sessionLoadVersionRef.current !== loadVersion) return;
        setRuntimeState((state) => applyContextState(applySessionDetail(state, detail), context));
        clearSessionError?.();
      } catch (error) {
        if (sessionLoadVersionRef.current === loadVersion) {
          onSessionError?.(error);
        }
      }
    },
    [clearSessionError, onSessionError],
  );

  useEffect(() => {
    const restoredSessionId = loadActiveSessionId();
    if (!restoredSessionId) return;
    void loadSession(restoredSessionId);
  }, [loadSession]);

  useEffect(() => {
    if (runtimeState.sessionId) {
      saveActiveSessionId(runtimeState.sessionId);
    }
  }, [runtimeState.sessionId]);

  const submitMessage = useCallback(
    async (message: string) => {
      const threadId = runtimeState.threadId || newRuntimeId("thread");
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      setBusy(true);
      setRuntimeState((state) => setThreadId(appendUserMessage(state, message), threadId));
      try {
        await streamChat(
          {
            message,
            project_id: projectId,
            session_id: runtimeState.sessionId,
            thread_id: threadId,
            model_intelligence: modelIntelligenceLevel,
          },
          {
            signal: abortRef.current.signal,
            onFrame(frame) {
              setRuntimeState((state) => applyStreamFrame(state, frame));
            },
          },
        );
        await refreshSessions();
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setRuntimeState((state) =>
          applyStreamFrame(state, {
            type: "error",
            error: errorMessage(error),
          }),
        );
      } finally {
        setBusy(false);
      }
    },
    [modelIntelligenceLevel, projectId, refreshSessions, runtimeState.sessionId, runtimeState.threadId],
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setBusy(false);
    setRuntimeState((state) => markStreamingStopped(state));
  }, []);

  const startNewChat = useCallback(() => {
    sessionLoadVersionRef.current += 1;
    abortRef.current?.abort();
    setBusy(false);
    clearSessionError?.();
    clearActiveSessionId();
    setRuntimeState(createInitialRuntimeState());
  }, [clearSessionError]);

  const resolvePermission = useCallback(
    async (decision: "approved" | "rejected") => {
      const permission = runtimeState.pendingPermission;
      if (!permission || !runtimeState.threadId) return;
      setBusy(true);
      try {
        const response = await sendApproval({
          thread_id: runtimeState.threadId,
          session_id: runtimeState.sessionId,
          decision: {
            tool_call_id: permission.tool_call_id,
            decision,
            reason: decision === "approved" ? "approved in frontend" : "rejected in frontend",
          },
        });
        setRuntimeState((state) => applyChatResponse(state, response));
        await refreshSessions();
      } catch (error) {
        setRuntimeState((state) =>
          applyRuntimeEvent(state, {
            id: `approval-error-${Date.now()}`,
            type: "error",
            timestamp: new Date().toISOString(),
            session_id: state.sessionId || "unknown",
            severity: "error",
            data: { error: errorMessage(error) },
          }),
        );
      } finally {
        setBusy(false);
      }
    },
    [refreshSessions, runtimeState.pendingPermission, runtimeState.sessionId, runtimeState.threadId],
  );

  const selectSession = useCallback((sessionId: string) => loadSession(sessionId), [loadSession]);

  return {
    runtimeState,
    busy,
    modelIntelligenceLevel,
    setModelIntelligenceLevel,
    submitMessage,
    stopStream,
    startNewChat,
    resolvePermission,
    selectSession,
  };
}

function newRuntimeId(prefix: "thread"): string {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Date.now());
  return `${prefix}_${random.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 32)}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
