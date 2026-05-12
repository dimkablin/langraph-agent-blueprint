import { useEffect, useMemo, useRef, useState } from "react";

import { ComposerActionMenu } from "./ComposerActionMenu.tsx";
import { ComposerContextMeter } from "./ComposerContextMeter.tsx";
import { ComposerIntelligencePicker } from "./ComposerIntelligencePicker.tsx";
import { ComposerSuggestions } from "./ComposerSuggestions.tsx";
import { WorkspaceControl } from "../workspaces/WorkspaceControl.tsx";
import type { RegistryMap, WorkspaceInfo } from "../../api/schemas.ts";
import { IconArrowUp } from "../../icons.ts";
import {
  applyComposerSuggestion,
  buildCommandSuggestions,
  CONTEXT_SUGGESTIONS,
  detectComposerSuggestionTrigger,
  filterComposerSuggestions,
} from "../../runtime/composerSuggestions.ts";
import type { ModelIntelligenceLevel } from "../../runtime/modelIntelligence.ts";
import type { RuntimeContextState } from "../../runtime/reducer.ts";

const COMPOSER_TEXTAREA_MIN_HEIGHT = 56;
const COMPOSER_TEXTAREA_MAX_HEIGHT = 180;

export function ChatComposer({
  commands,
  context,
  contextMaxTokens,
  disabled,
  intelligenceLevel,
  isStreaming,
  workspace,
  workspaces,
  workspaceError,
  onIntelligenceChange,
  onAddWorkspace,
  onSelectWorkspace,
  onCheckoutBranch,
  onOpenContextWindow,
  onSubmit,
  onStop,
  variant = "dock",
}: {
  commands: RegistryMap;
  context: RuntimeContextState;
  contextMaxTokens?: number | null;
  disabled?: boolean;
  intelligenceLevel: ModelIntelligenceLevel;
  isStreaming: boolean;
  workspace: WorkspaceInfo | null;
  workspaces: WorkspaceInfo[];
  workspaceError: string | null;
  onIntelligenceChange: (level: ModelIntelligenceLevel) => void;
  onAddWorkspace: () => void;
  onSelectWorkspace: (projectId: string) => void;
  onCheckoutBranch: (branch: string) => void;
  onOpenContextWindow?: () => void;
  onSubmit: (value: string) => void;
  onStop: () => void;
  variant?: "dock" | "welcome";
}) {
  const [input, setInput] = useState("");
  const [intelligenceOpen, setIntelligenceOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const trigger = detectComposerSuggestionTrigger(input);
  const commandSuggestions = useMemo(() => buildCommandSuggestions(commands), [commands]);
  const suggestions = trigger
    ? filterComposerSuggestions(trigger.kind === "context" ? CONTEXT_SUGGESTIONS : commandSuggestions, trigger)
    : [];

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const nextHeight = Math.min(
      Math.max(textarea.scrollHeight, COMPOSER_TEXTAREA_MIN_HEIGHT),
      COMPOSER_TEXTAREA_MAX_HEIGHT,
    );
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > COMPOSER_TEXTAREA_MAX_HEIGHT ? "auto" : "hidden";
  }, [input]);

  function submit() {
    const value = input.trim();
    if (!value || disabled || isStreaming) return;
    setInput("");
    onSubmit(value);
  }

  function selectSuggestion(suggestion: (typeof suggestions)[number]) {
    if (!trigger) return;
    setInput((value) => applyComposerSuggestion(value, trigger, suggestion));
  }

  return (
    <section className={variant === "welcome" ? "composer composer-welcome" : "composer"} aria-label="Chat composer">
      <div className="composer-surface">
        <div className="composer-box">
          <ComposerSuggestions trigger={trigger} suggestions={suggestions} onSelect={selectSuggestion} />
          <textarea
            id={variant === "welcome" ? "welcome-chat-composer" : "chat-composer"}
            name={variant === "welcome" ? "welcome-chat-composer" : "chat-composer"}
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={
              variant === "welcome"
                ? "Спросите у агента о чем угодно. Используйте @ для плагинов или / для комманд"
                : "Напишите агенту еще что-нибудь"
            }
            disabled={disabled}
            rows={1}
          />
          <div className="composer-footer">
            <div className="composer-footer-left">
              <ComposerActionMenu />
            </div>
            <div className="composer-footer-right">
              <ComposerContextMeter context={context} configuredMaxTokens={contextMaxTokens} onOpenContextWindow={onOpenContextWindow} />
              <ComposerIntelligencePicker
                level={intelligenceLevel}
                open={intelligenceOpen}
                onToggle={() => setIntelligenceOpen((value) => !value)}
                onChange={onIntelligenceChange}
                onClose={() => setIntelligenceOpen(false)}
              />
              {isStreaming ? (
                <button
                  className="send-button stop"
                  type="button"
                  onClick={onStop}
                  aria-label="Stop stream"
                  data-tooltip="Остановить"
                  data-tooltip-placement="top"
                  data-tooltip-align="end"
                >
                  <span className="stop-icon" aria-hidden="true" />
                </button>
              ) : (
                <button
                  className="send-button"
                  type="button"
                  onClick={submit}
                  disabled={disabled || !input.trim()}
                  aria-label="Send message"
                  data-tooltip="Отправить"
                  data-tooltip-placement="top"
                  data-tooltip-align="end"
                >
                  <IconArrowUp size={19} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="composer-workspace-row">
        <WorkspaceControl
          workspace={workspace}
          workspaces={workspaces}
          workspaceError={workspaceError}
          onAddWorkspace={onAddWorkspace}
          onSelectWorkspace={onSelectWorkspace}
          onCheckoutBranch={onCheckoutBranch}
        />
      </div>
    </section>
  );
}
