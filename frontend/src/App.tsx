import { useState } from "react";

import { ChatComposer } from "./components/chat/ChatComposer.tsx";
import { MessageList } from "./components/chat/MessageList.tsx";
import { WelcomePromptExamples, type WelcomePromptExample } from "./components/chat/WelcomePromptExamples.tsx";
import { RuntimeDrawer } from "./components/layout/RuntimeDrawer.tsx";
import { RuntimeSidebar } from "./components/layout/RuntimeSidebar.tsx";
import { StatusHeader } from "./components/layout/StatusHeader.tsx";
import { PermissionPanel } from "./components/permissions/PermissionPanel.tsx";
import { RegistryPanel } from "./components/registries/RegistryPanel.tsx";
import { RuntimeStatusPanel } from "./components/status/RuntimeStatusPanel.tsx";
import { useRuntimeChat } from "./hooks/useRuntimeChat.ts";
import { useRuntimeRegistries } from "./hooks/useRuntimeRegistries.ts";
import { useRuntimeSessions } from "./hooks/useRuntimeSessions.ts";
import { useRuntimeStatus } from "./hooks/useRuntimeStatus.ts";

export default function App() {
  const { commands, skills, tools, registryError } = useRuntimeRegistries();
  const { sessions, sessionError, refreshSessions, reportSessionError, clearSessionError } = useRuntimeSessions();
  const { runtimeStatus } = useRuntimeStatus();
  const {
    runtimeState,
    busy,
    modelIntelligenceLevel,
    setModelIntelligenceLevel,
    submitMessage,
    stopStream,
    startNewChat,
    resolvePermission,
    selectSession,
  } = useRuntimeChat({
    onSessionsChanged: refreshSessions,
    onSessionError: reportSessionError,
    clearSessionError,
  });
  const [activeDrawer, setActiveDrawer] = useState<"help" | "settings" | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const contextMaxTokens = numericConfigValue(runtimeStatus?.config?.values.context_max_tokens);
  const isNewChat = runtimeState.messages.length === 0 && !runtimeState.pendingPermission && !runtimeState.error;

  return (
    <main className={sidebarOpen ? "app-shell app-shell-sidebar-open" : "app-shell"}>
      <RuntimeSidebar
        open={sidebarOpen}
        sessions={sessions}
        activeSessionId={runtimeState.sessionId}
        error={sessionError}
        onNewChat={startNewChat}
        onOpenPlugins={() => setActiveDrawer("help")}
        onOpenSettings={() => setActiveDrawer("settings")}
        onSelectSession={(sessionId) => void selectSession(sessionId)}
      />
      <div className="app-main">
        <StatusHeader
          onNewChat={startNewChat}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          onOpenHelp={() => setActiveDrawer("help")}
        />
        <div className="app-body">
          <section className={isNewChat ? "chat-column chat-column-welcome" : "chat-column"}>
            {isNewChat ? (
              <div className="welcome-chat">
                <h1>Что нужно сделать?</h1>
                <ChatComposer
                  commands={commands}
                  context={runtimeState.context}
                  contextMaxTokens={contextMaxTokens}
                  disabled={busy && !runtimeState.isStreaming}
                  intelligenceLevel={modelIntelligenceLevel}
                  isStreaming={runtimeState.isStreaming || busy}
                  onIntelligenceChange={setModelIntelligenceLevel}
                  onSubmit={(value) => void submitMessage(value)}
                  onStop={stopStream}
                  variant="welcome"
                />
                <WelcomePromptExamples
                  disabled={busy}
                  examples={WELCOME_PROMPT_EXAMPLES}
                  onSelect={(prompt) => void submitMessage(prompt)}
                />
              </div>
            ) : (
              <>
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
                <ChatComposer
                  commands={commands}
                  context={runtimeState.context}
                  contextMaxTokens={contextMaxTokens}
                  disabled={busy && !runtimeState.isStreaming}
                  intelligenceLevel={modelIntelligenceLevel}
                  isStreaming={runtimeState.isStreaming || busy}
                  onIntelligenceChange={setModelIntelligenceLevel}
                  onSubmit={(value) => void submitMessage(value)}
                  onStop={stopStream}
                />
              </>
            )}
          </section>
        </div>
      </div>
      <RuntimeDrawer side="right" title="Commands / Skills / Tools" open={activeDrawer === "help"} onClose={() => setActiveDrawer(null)}>
        <RegistryPanel commands={commands} skills={skills} tools={tools} error={registryError} />
      </RuntimeDrawer>
      <RuntimeDrawer side="right" title="Настройки" open={activeDrawer === "settings"} onClose={() => setActiveDrawer(null)}>
        <RuntimeStatusPanel status={runtimeStatus} />
      </RuntimeDrawer>
    </main>
  );
}

const WELCOME_PROMPT_EXAMPLES: WelcomePromptExample[] = [
  {
    title: "Проверь последние изменения на риски корректности",
    prompt: "Проверь последние изменения проекта на риски корректности и поддерживаемости.",
    icon: "review",
  },
  {
    title: "Покажи, какие плагины и skills доступны",
    prompt: "/skills",
    icon: "plugin",
  },
  {
    title: "Составь план исправления frontend layout",
    prompt: "Составь короткий план исправления frontend layout без изменения backend runtime.",
    icon: "plan",
  },
];

function numericConfigValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
