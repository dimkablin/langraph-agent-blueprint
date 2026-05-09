import type { ReactNode } from "react";

import { IconX } from "../../icons.ts";

export function RuntimeDrawer({
  side,
  title,
  open,
  onClose,
  children,
}: {
  side: "left" | "right";
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <>
      <button type="button" className="drawer-backdrop" aria-label="Close panel" onClick={onClose} />
      <aside className={`runtime-drawer runtime-drawer-${side}`} aria-label={title}>
        <div className="drawer-header">
          <h2>{title}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть">
            <IconX size={18} />
          </button>
        </div>
        <div className="drawer-content">{children}</div>
      </aside>
    </>
  );
}
