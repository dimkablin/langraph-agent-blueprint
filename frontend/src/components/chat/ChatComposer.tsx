import { useEffect, useMemo, useRef, useState } from "react";

import { ComposerContextMeter } from "./ComposerContextMeter.tsx";
import { ComposerIntelligencePicker } from "./ComposerIntelligencePicker.tsx";
import { ComposerSuggestions } from "./ComposerSuggestions.tsx";
import type { RegistryMap } from "../../api/schemas.ts";
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
  onIntelligenceChange,
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
  onIntelligenceChange: (level: ModelIntelligenceLevel) => void;
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
            <ComposerContextMeter context={context} configuredMaxTokens={contextMaxTokens} />
            <ComposerIntelligencePicker
              level={intelligenceLevel}
              open={intelligenceOpen}
              onToggle={() => setIntelligenceOpen((value) => !value)}
              onChange={onIntelligenceChange}
              onClose={() => setIntelligenceOpen(false)}
            />
            {isStreaming ? (
              <button className="send-button stop" type="button" onClick={onStop} aria-label="Stop stream">
                <span className="stop-icon" aria-hidden="true" />
              </button>
            ) : (
              <button className="send-button" type="button" onClick={submit} disabled={disabled || !input.trim()} aria-label="Send message">
                <IconArrowUp size={19} />
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
