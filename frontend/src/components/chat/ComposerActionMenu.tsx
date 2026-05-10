import { useEffect, useRef, useState } from "react";

import { IconBlocks, IconChevronRight, IconListCheck, IconPaperclip, IconPlus } from "../../icons.ts";

export function ComposerActionMenu() {
  const [open, setOpen] = useState(false);
  const [planningMode, setPlanningMode] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="composer-action-menu" ref={menuRef}>
      <button
        className="composer-action-trigger"
        type="button"
        aria-label="Открыть действия"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        data-tooltip="Действия"
        data-tooltip-placement="top"
        data-tooltip-align="start"
      >
        <IconPlus size={18} />
      </button>
      {open ? (
        <div className="composer-action-popover" role="menu" aria-label="Действия composer">
          <button className="composer-action-row" type="button" role="menuitem">
            <IconPaperclip size={16} />
            <span>Добавить фотографии и файлы</span>
          </button>
          <button
            className="composer-action-row"
            type="button"
            role="menuitemcheckbox"
            aria-checked={planningMode}
            onClick={() => setPlanningMode((value) => !value)}
          >
            <IconListCheck size={16} />
            <span>Режим Планирования</span>
            <span className={planningMode ? "composer-action-switch composer-action-switch-on" : "composer-action-switch"}>
              <span />
            </span>
          </button>
          <button className="composer-action-row composer-action-row-submenu" type="button" role="menuitem">
            <IconBlocks size={16} />
            <span>Плагины</span>
            <IconChevronRight size={15} />
          </button>
        </div>
      ) : null}
    </div>
  );
}
