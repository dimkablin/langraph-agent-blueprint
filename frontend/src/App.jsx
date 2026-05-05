import React, { useEffect, useMemo, useState } from "react";
import { fetchCommands, fetchSkills, fetchTools, sendApproval, sendChat } from "./api.js";
import { EmptyState, HintPanel, PermissionPrompt, StatusBar, TerminalShell } from "./components.jsx";

let lineId = 0;

function appendLine(role, text) {
  const prompt = role === "user" ? "you" : role === "assistant" ? "assistant" : role;
  return { id: `${Date.now()}-${lineId++}`, role, prompt: `${prompt}>`, text };
}

function eventsToLines(events = []) {
  return events
    .filter((event) => ["tool_call_started", "tool_call_finished", "tool_call_error", "permission_required", "skill_started", "skill_finished", "subagent_started", "subagent_finished", "compact_finished", "error"].includes(event.type))
    .map((event) => appendLine("event", `${event.type} ${JSON.stringify(event.data || {})}`));
}

export default function App() {
  const [input, setInput] = useState("");
  const [transcript, setTranscript] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [threadId, setThreadId] = useState(null);
  const [permissionRequest, setPermissionRequest] = useState(null);
  const [busy, setBusy] = useState(false);
  const [apiStatus, setApiStatus] = useState("api pending");
  const [commands, setCommands] = useState({});
  const [skills, setSkills] = useState({});
  const [tools, setTools] = useState({});

  useEffect(() => {
    Promise.all([fetchCommands(), fetchSkills(), fetchTools()])
      .then(([commandData, skillData, toolData]) => {
        setCommands(commandData);
        setSkills(skillData);
        setTools(toolData);
        setApiStatus("api ready");
      })
      .catch((error) => {
        setApiStatus(`api error: ${error.message}`);
      });
  }, []);

  async function submit() {
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setTranscript((items) => [...items, appendLine("user", message)]);
    try {
      const result = await sendChat({ message, sessionId, threadId });
      applyGraphResult(result);
    } catch (error) {
      setTranscript((items) => [...items, appendLine("error", error.message)]);
    } finally {
      setBusy(false);
    }
  }

  async function resolvePermission(approved) {
    if (!permissionRequest || !threadId) return;
    setBusy(true);
    try {
      const result = await sendApproval({
        threadId,
        approved,
        reason: approved ? "approved in React CLI" : "rejected in React CLI",
      });
      setPermissionRequest(null);
      applyGraphResult(result);
    } catch (error) {
      setTranscript((items) => [...items, appendLine("error", error.message)]);
    } finally {
      setBusy(false);
    }
  }

  function applyGraphResult(result) {
    setSessionId(result.session_id);
    setThreadId(result.thread_id);
    if (result.permission_required) {
      setPermissionRequest(result.permission_required);
    }
    const lines = eventsToLines(result.events);
    if (result.final_response) {
      lines.push(appendLine("assistant", result.final_response));
    }
    setTranscript((items) => [...items, ...lines]);
  }

  const visibleTranscript = useMemo(() => (transcript.length ? transcript : [appendLine("system", "React CLI frontend connected to LangGraph API. No tools run directly in the browser.")]), [transcript]);

  return (
    <main className="app-shell">
      <StatusBar sessionId={sessionId} threadId={threadId} busy={busy} apiStatus={apiStatus} />
      <div className="workspace">
        <div className="terminal-column">
          <TerminalShell transcript={visibleTranscript} input={input} setInput={setInput} onSubmit={submit} busy={busy} />
          {!transcript.length && <EmptyState />}
          <PermissionPrompt request={permissionRequest} busy={busy} onApprove={() => resolvePermission(true)} onReject={() => resolvePermission(false)} />
        </div>
        <HintPanel input={input} liveCommands={commands} liveTools={tools} liveSkills={skills} />
      </div>
    </main>
  );
}
