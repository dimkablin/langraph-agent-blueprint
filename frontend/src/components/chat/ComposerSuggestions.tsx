import { IconAt, IconCommand, IconFileText } from "../../icons.ts";
import type { ComposerSuggestion, ComposerSuggestionTrigger } from "../../runtime/composerSuggestions.ts";

export function ComposerSuggestions({
  trigger,
  suggestions,
  onSelect,
}: {
  trigger: ComposerSuggestionTrigger | null;
  suggestions: ComposerSuggestion[];
  onSelect: (suggestion: ComposerSuggestion) => void;
}) {
  if (!trigger) return null;

  return (
    <div className="composer-suggestions" role="listbox" aria-label={trigger.kind === "context" ? "Context suggestions" : "Command suggestions"}>
      <div className="suggestion-group-label">{trigger.kind === "context" ? "Контекст" : "Команды"}</div>
      {suggestions.length ? (
        suggestions.map((suggestion, index) => (
          <button
            key={`${suggestion.kind}-${suggestion.value}`}
            type="button"
            className={index === 0 ? "suggestion-row suggestion-row-active" : "suggestion-row"}
            onMouseDown={(event) => {
              event.preventDefault();
              onSelect(suggestion);
            }}
            role="option"
            aria-selected={index === 0}
          >
            <span className="suggestion-icon">{iconForSuggestion(suggestion)}</span>
            <span className="suggestion-copy">
              <strong>{suggestion.value}</strong>
              <span>{suggestion.description}</span>
            </span>
          </button>
        ))
      ) : (
        <div className="suggestion-empty">{trigger.kind === "context" ? "Нет context-подсказок" : "Нет команд"}</div>
      )}
      <div className="suggestion-footer">
        {trigger.kind === "context" ? "Введите путь, glob, notebook, MCP, plugin или URL reference" : "Введите имя slash-команды"}
      </div>
    </div>
  );
}

function iconForSuggestion(suggestion: ComposerSuggestion) {
  if (suggestion.kind === "command") return <IconCommand size={16} />;
  if (suggestion.value.startsWith("@")) return <IconAt size={16} />;
  return <IconFileText size={16} />;
}
