import { useEffect, useRef } from "react";

import { IconCheck, IconChevronDown, IconShield, IconShieldExclamation } from "../../icons.ts";
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
  const SelectedModeIcon = elevated ? IconShieldExclamation : IconShield;

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
        className="composer-permission-button"
        onClick={onToggle}
        aria-label={`Режим разрешений: ${selected.label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        data-permission-mode={mode}
      >
        <SelectedModeIcon size={14} />
        <span>{selected.label}</span>
        <IconChevronDown size={13} />
      </button>
      {open ? (
        <div className="composer-permission-popover" role="menu" aria-label="Режим разрешений">
          <div className="permission-mode-menu-title">Разрешения</div>
          {PERMISSION_MODE_OPTIONS.map((option) => {
            const isSelected = option.id === mode;
            const isElevated = option.risk === "elevated";
            const PermissionModeIcon = isElevated ? IconShieldExclamation : IconShield;
            return (
              <button
                key={option.id}
                type="button"
                className="permission-mode-option"
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
                    <PermissionModeIcon size={14} />
                    {option.label}
                  </span>
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
