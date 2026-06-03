import { useCallback, useEffect, useRef, useState } from "react";

import { sendApproval } from "../api/approval.ts";
import { cancelChat } from "../api/chat.ts";
import { fetchConversationDetail } from "../api/conversations.ts";
import { streamChat } from "../api/stream.ts";
import { clearActiveSessionId, loadActiveSessionId, saveActiveSessionId } from "../runtime/activeSession.ts";
import { DEFAULT_MODEL_INTELLIGENCE_LEVEL, type ModelIntelligenceLevel } from "../runtime/modelIntelligence.ts";
import { loadPermissionMode, savePermissionMode, type PermissionMode } from "../runtime/permissionMode.ts";
import {
  appendUserMessage,
  applyChatResponse,
  applyContextState,
  applyRuntimeEvent,
  applySessionDetail,
  applyStreamFrame,
  clearPendingPermission,
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
  const [permissionMode, setPermissionModeState] = useState<PermissionMode>(() => loadPermissionMode());
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const activeRunRef = useRef<{ threadId: string; sessionId: string | null } | null>(null);
  const sessionLoadVersionRef = useRef(0);

  useEffect(() => () => abortRef.current?.abort(), []);

  const refreshSessions = useCallback(async () => {
    await onSessionsChanged?.();
  }, [onSessionsChanged]);

  const loadSession = useCallback(
    async (sessionId: string) => {
      const loadVersion = ++sessionLoadVersionRef.current;
      try {
        const detail = await fetchConversationDetail(sessionId);
        if (sessionLoadVersionRef.current !== loadVersion) return;
        setRuntimeState((state) => applyContextState(applySessionDetail(state, detail), detail.context));
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
    savePermissionMode(permissionMode);
  }, [permissionMode]);

  const setPermissionMode = useCallback((mode: PermissionMode) => {
    setPermissionModeState(mode);
  }, []);

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
      activeRunRef.current = { threadId, sessionId: runtimeState.sessionId };
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
            permission_mode: permissionMode,
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
        activeRunRef.current = null;
        setBusy(false);
      }
    },
    [modelIntelligenceLevel, permissionMode, projectId, refreshSessions, runtimeState.sessionId, runtimeState.threadId],
  );

  const stopStream = useCallback(() => {
    const activeRun = activeRunRef.current || (runtimeState.threadId ? { threadId: runtimeState.threadId, sessionId: runtimeState.sessionId } : null);
    if (activeRun?.threadId) {
      void cancelChat({
        thread_id: activeRun.threadId,
        session_id: activeRun.sessionId,
        reason: "stop button",
      }).catch(() => undefined);
    }
    abortRef.current?.abort();
    activeRunRef.current = null;
    setBusy(false);
    setRuntimeState((state) => markStreamingStopped(state));
  }, [runtimeState.sessionId, runtimeState.threadId]);

  const startNewChat = useCallback(() => {
    sessionLoadVersionRef.current += 1;
    const activeRun = activeRunRef.current || (runtimeState.threadId ? { threadId: runtimeState.threadId, sessionId: runtimeState.sessionId } : null);
    if (activeRun?.threadId) {
      void cancelChat({
        thread_id: activeRun.threadId,
        session_id: activeRun.sessionId,
        reason: "new chat",
      }).catch(() => undefined);
    }
    abortRef.current?.abort();
    activeRunRef.current = null;
    setBusy(false);
    clearSessionError?.();
    clearActiveSessionId();
    setRuntimeState(createInitialRuntimeState());
  }, [clearSessionError, runtimeState.sessionId, runtimeState.threadId]);

  const resolvePermission = useCallback(
    async (decision: "approved" | "rejected") => {
      const permission = runtimeState.pendingPermission;
      if (!permission || !runtimeState.threadId) return;
      setBusy(true);
      setRuntimeState((state) => clearPendingPermission(state));
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
          applyRuntimeEvent(
            { ...state, pendingPermission: permission },
            {
              id: `approval-error-${Date.now()}`,
              type: "error",
              timestamp: new Date().toISOString(),
              session_id: state.sessionId || "unknown",
              severity: "error",
              data: { error: errorMessage(error) },
            },
          ),
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
    permissionMode,
    setPermissionMode,
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
