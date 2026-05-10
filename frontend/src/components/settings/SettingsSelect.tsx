import { useEffect, useId, useRef, useState } from "react";

import { IconCheck, IconChevronDown } from "../../icons.ts";

export type SettingsSelectOption<T extends string> = {
  value: T;
  label: string;
  description?: string;
};

export function SettingsSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly SettingsSelectOption<T>[];
  onChange: (value: T) => void;
}) {
  const [open, setOpen] = useState(false);
  const controlRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!controlRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="settings-select" ref={controlRef}>
      <button
        type="button"
        className="settings-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selected?.label ?? "Select"}</span>
        <IconChevronDown size={14} />
      </button>
      {open ? (
        <div className="settings-select-popover" role="listbox" id={listboxId} aria-label={label}>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                type="button"
                className={isSelected ? "settings-select-option settings-select-option-selected" : "settings-select-option"}
                role="option"
                aria-selected={isSelected}
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
              >
                <span className="settings-select-option-text">
                  <strong>{option.label}</strong>
                  {option.description ? <small>{option.description}</small> : null}
                </span>
                {isSelected ? <IconCheck size={16} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
