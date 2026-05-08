import { Bot, CircleAlert, CircleCheck, Radio } from "lucide-react";

import { compactId } from "../../runtime/viewModels.ts";

export function StatusHeader({
  status,
  apiStatus,
  sessionId,
  threadId,
}: {
  status: string;
  apiStatus: string;
  sessionId: string | null;
  threadId: string | null;
}) {
  const isError = apiStatus.startsWith("api error");
  return (
    <header className="app-header">
      <div className="brand-lockup">
        <div className="brand-mark">
          <Bot size={18} />
        </div>
        <div>
          <strong>langgraph-agent-blueprint</strong>
          <span>Thin runtime frontend</span>
        </div>
      </div>
      <div className="header-status">
        <span>
          <Radio size={14} />
          {status}
        </span>
        <span className={isError ? "status-bad" : "status-good"}>
          {isError ? <CircleAlert size={14} /> : <CircleCheck size={14} />}
          {apiStatus}
        </span>
        <span>session {compactId(sessionId)}</span>
        <span>thread {compactId(threadId)}</span>
      </div>
    </header>
  );
}

