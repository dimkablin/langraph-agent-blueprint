import { useState, type CSSProperties } from "react";

import { ChatComposer } from "./components/chat/ChatComposer.tsx";
import { MessageList } from "./components/chat/MessageList.tsx";
import { WelcomePromptExamples, type WelcomePromptExample } from "./components/chat/WelcomePromptExamples.tsx";
import { LiquidGlassFilterDefs } from "./components/common/LiquidGlassFilterDefs.tsx";
import { ContextWindowOverlay } from "./components/context/ContextWindowOverlay.tsx";
import { RuntimeDrawer } from "./components/layout/RuntimeDrawer.tsx";
import { RuntimeSidebar } from "./components/layout/RuntimeSidebar.tsx";
import { StatusHeader } from "./components/layout/StatusHeader.tsx";
import { PermissionPanel } from "./components/permissions/PermissionPanel.tsx";
import { RegistryPanel } from "./components/registries/RegistryPanel.tsx";
import { SettingsPage } from "./components/settings/SettingsPage.tsx";
import { useRuntimeChat } from "./hooks/useRuntimeChat.ts";
import { useRuntimeRegistries } from "./hooks/useRuntimeRegistries.ts";
import { useRuntimeSessions } from "./hooks/useRuntimeSessions.ts";
import { useRuntimeStatus } from "./hooks/useRuntimeStatus.ts";
import { useUIPreferences } from "./hooks/useUIPreferences.ts";
import { useWorkspaces } from "./hooks/useWorkspaces.ts";
import { effectiveModelName } from "./runtime/modelConfig.ts";
import { DEFAULT_SETTINGS_TAB, type SettingsTab } from "./runtime/settingsPage.ts";
import { filterTimelineByPreferences, themeConfigForPreferences, themeCSSVariables } from "./runtime/uiPreferences.ts";

type AppView = "chat" | "settings";

export default function App() {
  const { commands, skills, tools, registryError } = useRuntimeRegistries();
  const { sessions, sessionError, refreshSessions, reportSessionError, clearSessionError } = useRuntimeSessions();
  const { runtimeStatus } = useRuntimeStatus();
  const { workspaces, activeWorkspace, workspaceError, addLocalWorkspace, pickLocalWorkspace, setActiveProject, checkoutBranch } = useWorkspaces();
  const { preferences, updatePreferences } = useUIPreferences();
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
    projectId: activeWorkspace?.project_id,
    onSessionsChanged: refreshSessions,
    onSessionError: reportSessionError,
    clearSessionError,
  });
  const [activeDrawer, setActiveDrawer] = useState<"help" | null>(null);
  const [appView, setAppView] = useState<AppView>("chat");
  const [activeSettingsTab, setActiveSettingsTab] = useState<SettingsTab>(DEFAULT_SETTINGS_TAB);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [contextWindowOpen, setContextWindowOpen] = useState(false);

  const contextMaxTokens = numericConfigValue(runtimeStatus?.config?.values.context_max_tokens);
  const modelName = effectiveModelName(runtimeStatus?.config);
  const isNewChat = runtimeState.messages.length === 0 && !runtimeState.pendingPermission && !runtimeState.error;
  const sidebarIsTranslucent = !themeConfigForPreferences(preferences).opaqueWindows;
  const shellBaseClassName = sidebarOpen ? "app-shell app-shell-sidebar-open" : "app-shell";
  const shellClassName = [
    shellBaseClassName,
    `app-density-${preferences.density}`,
    `app-theme-${preferences.theme}`,
    sidebarIsTranslucent ? "app-shell-sidebar-glass" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const shellStyle = themeCSSVariables(preferences) as CSSProperties;
  const visibleTimeline = filterTimelineByPreferences(runtimeState.timeline, preferences);

  const openChatView = () => setAppView("chat");
  const handleNewChat = () => {
    startNewChat();
    setContextWindowOpen(false);
    openChatView();
  };
  const handleSelectSession = (sessionId: string) => {
    setContextWindowOpen(false);
    openChatView();
    void selectSession(sessionId);
  };
  const handleOpenSettings = () => {
    setActiveDrawer(null);
    setSidebarOpen(true);
    setAppView("settings");
  };
  const handlePickWorkspace = () => {
    void pickLocalWorkspace();
  };
  const handleAddWorkspace = (rootPath: string) => {
    void addLocalWorkspace(rootPath);
  };

  return (
    <main className={shellClassName} style={shellStyle}>
      <LiquidGlassFilterDefs />
      <RuntimeSidebar
        open={sidebarOpen}
        mode={appView}
        sessions={sessions}
        activeSessionId={runtimeState.sessionId}
        error={sessionError}
        settingsActiveTab={activeSettingsTab}
        onNewChat={handleNewChat}
        onOpenChat={openChatView}
        onOpenPlugins={() => setActiveDrawer("help")}
        onOpenSettings={handleOpenSettings}
        onSettingsTabChange={setActiveSettingsTab}
        onSelectSession={handleSelectSession}
      />
      <div className="app-main">
        <StatusHeader
          onNewChat={handleNewChat}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          onOpenHelp={() => setActiveDrawer("help")}
        />
        <div className="app-body">
          {appView === "settings" ? (
            <SettingsPage
              activeTab={activeSettingsTab}
              status={runtimeStatus}
              skills={skills}
              context={runtimeState.context}
              contextMaxTokens={contextMaxTokens}
              modelIntelligenceLevel={modelIntelligenceLevel}
              preferences={preferences}
              sessionId={runtimeState.sessionId}
              threadId={runtimeState.threadId}
              onPreferencesChange={updatePreferences}
            />
          ) : (
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
                    workspace={activeWorkspace}
                    workspaces={workspaces}
                    workspaceError={workspaceError}
                    onIntelligenceChange={setModelIntelligenceLevel}
                    onAddWorkspace={handleAddWorkspace}
                    onPickWorkspace={handlePickWorkspace}
                    onSelectWorkspace={(projectId) => void setActiveProject(projectId)}
                    onCheckoutBranch={(branch) => void checkoutBranch(branch)}
                    onOpenContextWindow={() => setContextWindowOpen(true)}
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
                    <MessageList
                      messages={runtimeState.messages}
                      items={visibleTimeline}
                      isStreaming={runtimeState.isStreaming || busy}
                      autoScroll={preferences.autoScroll}
                    />
                  </div>
                  {runtimeState.error ? <div className="error-banner">{runtimeState.error}</div> : null}
                  <div className="chat-input-stack">
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
                      workspace={activeWorkspace}
                      workspaces={workspaces}
                      workspaceError={workspaceError}
                      onIntelligenceChange={setModelIntelligenceLevel}
                      onAddWorkspace={handleAddWorkspace}
                      onPickWorkspace={handlePickWorkspace}
                      onSelectWorkspace={(projectId) => void setActiveProject(projectId)}
                      onCheckoutBranch={(branch) => void checkoutBranch(branch)}
                      onOpenContextWindow={() => setContextWindowOpen(true)}
                      onSubmit={(value) => void submitMessage(value)}
                      onStop={stopStream}
                    />
                  </div>
                </>
              )}
            </section>
          )}
        </div>
      </div>
      <RuntimeDrawer side="right" title="Commands / Skills / Tools" open={activeDrawer === "help"} onClose={() => setActiveDrawer(null)}>
        <RegistryPanel commands={commands} skills={skills} tools={tools} error={registryError} />
      </RuntimeDrawer>
      <ContextWindowOverlay
        open={contextWindowOpen}
        context={runtimeState.context}
        modelName={modelName}
        configuredMaxTokens={contextMaxTokens}
        onClose={() => setContextWindowOpen(false)}
      />
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
