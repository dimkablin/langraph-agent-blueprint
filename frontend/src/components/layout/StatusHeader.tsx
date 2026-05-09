import { IconHelpCircle, IconLayoutSidebarLeftExpand, IconPlus } from "../../icons.ts";

export function StatusHeader({
  onNewChat,
  onToggleSidebar,
  onOpenHelp,
}: {
  onNewChat: () => void;
  onToggleSidebar: () => void;
  onOpenHelp: () => void;
}) {
  return (
    <header className="app-header">
      <div className="header-leading" aria-label="Chat controls">
        <button
          type="button"
          className="icon-button"
          onClick={onToggleSidebar}
          aria-label="Боковая панель"
          data-tooltip="Боковая панель"
          data-tooltip-align="start"
        >
          <IconLayoutSidebarLeftExpand size={18} />
        </button>
        <button type="button" className="icon-button" onClick={onNewChat} aria-label="Новый чат" data-tooltip="Новый чат" data-tooltip-align="start">
          <IconPlus size={18} />
        </button>
      </div>
      <div className="header-status">
        <div className="header-actions" aria-label="Runtime panels">
          <button
            type="button"
            className="icon-button icon-button-square"
            onClick={onOpenHelp}
            aria-label="Справка"
            data-tooltip="Commands / Skills / Tools"
            data-tooltip-align="end"
          >
            <IconHelpCircle size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
