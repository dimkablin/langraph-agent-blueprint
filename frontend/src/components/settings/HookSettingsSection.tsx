import type { HookStatusDTO } from "../../api/schemas.ts";
import { EmptySettings, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function HookSettingsSection({ status }: { status: HookStatusDTO | null }) {
  const hooks = status?.hooks ?? [];
  return (
    <SettingsSection title="Hooks" eyebrow="read-only">
      {hooks.length ? (
        <div className="settings-card-list">
          {hooks.slice(0, 12).map((hook) => (
            <article className="settings-card" key={stringValue(hook.id, "hook")}>
              <div>
                <strong>{stringValue(hook.id, "unknown hook")}</strong>
                <span>{stringValue(hook.hook_point, "unknown point")}</span>
              </div>
              <div className="settings-inline-badges">
                <StatusBadge tone={hook.enabled === false ? "warning" : "ok"}>{hook.enabled === false ? "disabled" : "enabled"}</StatusBadge>
                <StatusBadge>{stringValue(hook.plugin_name, "core")}</StatusBadge>
                <StatusBadge>priority {numberValue(hook.priority, 100)}</StatusBadge>
                <StatusBadge tone={hook.trusted ? "ok" : "neutral"}>{hook.trusted ? "trusted" : "untrusted"}</StatusBadge>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptySettings>No hooks registered.</EmptySettings>
      )}
    </SettingsSection>
  );
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" ? value : fallback;
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
