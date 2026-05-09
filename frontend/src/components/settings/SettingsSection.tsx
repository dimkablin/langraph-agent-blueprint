import type { ReactNode } from "react";

export type SettingRow = {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  locked?: boolean;
};

export function SettingsSection({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
}) {
  return (
    <section className="settings-section">
      <div className="settings-section-heading">
        <h3>{title}</h3>
        {eyebrow ? <span>{eyebrow}</span> : null}
      </div>
      {children}
    </section>
  );
}

export function SettingsRows({ rows }: { rows: SettingRow[] }) {
  return (
    <div className="settings-rows">
      {rows.map((row) => (
        <div className={row.locked ? "settings-row settings-row-locked" : "settings-row"} key={row.label}>
          <span>{row.label}</span>
          <strong>{row.value}</strong>
          {row.note ? <small>{row.note}</small> : null}
        </div>
      ))}
    </div>
  );
}

export function StatusBadge({ tone = "neutral", children }: { tone?: "neutral" | "ok" | "warning" | "danger"; children: ReactNode }) {
  return <span className={`settings-badge settings-badge-${tone}`}>{children}</span>;
}

export function EmptySettings({ children }: { children: ReactNode }) {
  return <p className="settings-empty">{children}</p>;
}
