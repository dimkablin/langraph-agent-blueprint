import { useEffect, useRef } from "react";

import { IconCheck, IconChevronDown, IconShieldExclamation } from "../../icons.ts";
import {
  PERMISSION_MODE_OPTIONS,
  permissionModeOptionById,
  type PermissionMode,
} from "../../runtime/permissionMode.ts";

export function ComposerPermissionModePicker({
  mode,
  open,
  onToggle,
  onChange,
  onClose,
}: {
  mode: PermissionMode;
  open: boolean;
  onToggle: () => void;
  onChange: (mode: PermissionMode) => void;
  onClose: () => void;
}) {
  const controlRef = useRef<HTMLDivElement | null>(null);
  const selected = permissionModeOptionById(mode);
  const elevated = selected.risk === "elevated";

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
    <div className="composer-permission-control" ref={controlRef}>
      <button
        type="button"
        className={elevated ? "composer-permission-button composer-permission-button-elevated" : "composer-permission-button"}
        onClick={onToggle}
        aria-label={`Режим разрешений: ${selected.label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        data-permission-mode={mode}
        data-tooltip={`Разрешения: ${selected.label}`}
        data-tooltip-placement="top"
        data-tooltip-align="start"
      >
        {elevated ? <IconShieldExclamation size={14} /> : null}
        <span>{selected.label}</span>
        <IconChevronDown size={13} />
      </button>
      {open ? (
        <div className="composer-permission-popover" role="menu" aria-label="Режим разрешений">
          <div className="permission-mode-menu-title">Разрешения</div>
          {PERMISSION_MODE_OPTIONS.map((option) => {
            const isSelected = option.id === mode;
            const isElevated = option.risk === "elevated";
            return (
              <button
                key={option.id}
                type="button"
                className={isSelected ? "permission-mode-option permission-mode-option-selected" : "permission-mode-option"}
                role="menuitemradio"
                aria-checked={isSelected}
                data-permission-mode-option={option.id}
                onClick={() => {
                  onChange(option.id);
                  onClose();
                }}
              >
                <span className="permission-mode-option-copy">
                  <span className="permission-mode-option-label">
                    {isElevated ? <IconShieldExclamation size={14} /> : null}
                    {option.label}
                  </span>
                  <span className="permission-mode-option-description">{option.description}</span>
                </span>
                {isSelected ? <IconCheck size={16} /> : null}
              </button>
            );
          })}
          <p className="permission-mode-warning">Полный доступ не включается по умолчанию и сохраняется только после вашего выбора.</p>
        </div>
      ) : null}
    </div>
  );
}
