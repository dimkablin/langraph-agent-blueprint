import { useEffect, useRef } from "react";

import { IconCheck, IconChevronDown } from "../../icons.ts";
import {
  MODEL_INTELLIGENCE_OPTIONS,
  modelIntelligenceOptionById,
  type ModelIntelligenceLevel,
} from "../../runtime/modelIntelligence.ts";

export function ComposerIntelligencePicker({
  level,
  open,
  onToggle,
  onChange,
  onClose,
}: {
  level: ModelIntelligenceLevel;
  open: boolean;
  onToggle: () => void;
  onChange: (level: ModelIntelligenceLevel) => void;
  onClose: () => void;
}) {
  const controlRef = useRef<HTMLDivElement | null>(null);
  const selected = modelIntelligenceOptionById(level);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!controlRef.current?.contains(event.target as Node)) {
        onClose();
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  return (
    <div className="composer-intelligence-control" ref={controlRef}>
      <button
        type="button"
        className="composer-intelligence-button"
        onClick={onToggle}
        aria-label={`Уровень интеллекта модели: ${selected.label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        title={`Интеллект: ${selected.label}`}
      >
        <span>{selected.label}</span>
        <IconChevronDown size={13} />
      </button>
      {open ? (
        <div className="composer-intelligence-popover" role="menu" aria-label="Интеллект модели">
          <div className="intelligence-menu-title">Интеллект</div>
          {MODEL_INTELLIGENCE_OPTIONS.map((option) => {
            const isSelected = option.id === level;
            return (
              <button
                key={option.id}
                type="button"
                className={isSelected ? "intelligence-option intelligence-option-selected" : "intelligence-option"}
                role="menuitemradio"
                aria-checked={isSelected}
                onClick={() => {
                  onChange(option.id);
                  onClose();
                }}
              >
                <span>{option.label}</span>
                {isSelected ? <IconCheck size={16} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
