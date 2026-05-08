import { useEffect, useMemo, useRef, useState } from "react";

import { sendApproval } from "./api/approval.ts";
import { fetchCommands, fetchSkills, fetchTools } from "./api/registries.ts";
import { exportSession, fetchSessionContext, fetchSessionDetail, fetchSessions } from "./api/sessions.ts";
import { fetchRuntimeStatus, type RuntimeStatus } from "./api/status.ts";
import { streamChat } from "./api/stream.ts";
import type { RegistryMap, SessionDetailDTO, SessionListItemDTO } from "./api/schemas.ts";
import { ChatComposer } from "./components/chat/ChatComposer.tsx";
import { MessageList } from "./components/chat/MessageList.tsx";
import { ContextPanel } from "./components/context/ContextPanel.tsx";
import { EventTimeline } from "./components/events/EventTimeline.tsx";
import { StatusHeader } from "./components/layout/StatusHeader.tsx";
import { PermissionPanel } from "./components/permissions/PermissionPanel.tsx";
import { RegistryPanel } from "./components/registries/RegistryPanel.tsx";
import { SessionsPanel } from "./components/sessions/SessionsPanel.tsx";
import { RuntimeStatusPanel } from "./components/status/RuntimeStatusPanel.tsx";
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
} from "./runtime/reducer.ts";
import { statusText, visibleActivities } from "./runtime/selectors.ts";

export default function App() {
  const [runtimeState, setRuntimeState] = useState(createInitialRuntimeState);
  const [commands, setCommands] = useState<RegistryMap>({});
  const [skills, setSkills] = useState<RegistryMap>({});
  const [tools, setTools] = useState<RegistryMap>({});
  const [sessions, setSessions] = useState<SessionListItemDTO[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionDetailDTO | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [apiStatus, setApiStatus] = useState("api pending");
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    void refreshRegistries();
    void refreshSessions();
    void refreshRuntimeStatus();
    return () => abortRef.current?.abort();
  }, []);

  async function refreshRegistries() {
    try {
      const [commandData, skillData, toolData] = await Promise.all([fetchCommands(), fetchSkills(), fetchTools()]);
      setCommands(commandData);
      setSkills(skillData);
      setTools(toolData);
      setRegistryError(null);
      setApiStatus("api ready");
    } catch (error) {
      setRegistryError(error instanceof Error ? error.message : String(error));
      setApiStatus("api error");
    }
  }

  async function refreshSessions() {
    try {
      setSessions(await fetchSessions());
      setSessionError(null);
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : String(error));
    }
  }

  async function refreshRuntimeStatus() {
    setRuntimeStatus(await fetchRuntimeStatus());
  }

  async function submitMessage(message: string) {
    const threadId = runtimeState.threadId || newRuntimeId("thread");
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setBusy(true);
    setRuntimeState((state) => setThreadId(appendUserMessage(state, message), threadId));
    try {
      await streamChat(
        {
          message,
          session_id: runtimeState.sessionId,
          thread_id: threadId,
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
          error: error instanceof Error ? error.message : String(error),
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  function stopStream() {
    abortRef.current?.abort();
    setBusy(false);
    setRuntimeState((state) => markStreamingStopped(state));
  }

  async function resolvePermission(decision: "approved" | "rejected") {
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
          data: { error: error instanceof Error ? error.message : String(error) },
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function selectSession(sessionId: string) {
    try {
      const detail = await fetchSessionDetail(sessionId);
      const context = await fetchSessionContext(sessionId);
      setSelectedSession(detail);
      setRuntimeState((state) => applyContextState(applySessionDetail(state, detail), context));
      setSessionError(null);
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleExport(sessionId: string) {
    try {
      const result = await exportSession(sessionId);
      setSessionError(`Exported ${result.format}: ${result.path}`);
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : String(error));
    }
  }

  const activities = useMemo(() => visibleActivities(runtimeState), [runtimeState]);

  return (
    <main className="app-shell">
      <StatusHeader
        status={statusText(runtimeState)}
        apiStatus={apiStatus}
        sessionId={runtimeState.sessionId}
        threadId={runtimeState.threadId}
      />
      <div className="runtime-workspace">
        <section className="chat-column">
          <div className="chat-scroll">
            <MessageList messages={runtimeState.messages} isStreaming={runtimeState.isStreaming || busy} />
          </div>
          {runtimeState.error ? <div className="error-banner">{runtimeState.error}</div> : null}
          <PermissionPanel
            request={runtimeState.pendingPermission}
            busy={busy}
            onApprove={() => void resolvePermission("approved")}
            onReject={() => void resolvePermission("rejected")}
          />
          <ChatComposer disabled={busy && !runtimeState.isStreaming} isStreaming={runtimeState.isStreaming || busy} onSubmit={(value) => void submitMessage(value)} onStop={stopStream} />
        </section>
        <aside className="side-panel">
          <EventTimeline activities={activities} />
          <ContextPanel context={runtimeState.context} />
          <SessionsPanel
            sessions={sessions}
            selected={selectedSession}
            activeSessionId={runtimeState.sessionId}
            error={sessionError}
            onSelect={(sessionId) => void selectSession(sessionId)}
            onExport={(sessionId) => void handleExport(sessionId)}
          />
          <RegistryPanel commands={commands} skills={skills} tools={tools} error={registryError} />
          <RuntimeStatusPanel status={runtimeStatus} />
        </aside>
      </div>
    </main>
  );
}

function newRuntimeId(prefix: "thread"): string {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Date.now());
  return `${prefix}_${random.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 32)}`;
}
