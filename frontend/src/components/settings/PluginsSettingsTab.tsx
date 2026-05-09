import type { PluginStatusDTO } from "../../api/schemas.ts";
import { PluginSettingsSection } from "./PluginSettingsSection.tsx";
import { SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function PluginsSettingsTab({ status }: { status: PluginStatusDTO | null }) {
  return (
    <div className="settings-tab-panel" aria-label="Плагины">
      <SettingsSection title="Plugin safety" eyebrow="read-only">
        <div className="settings-inline-badges">
          <StatusBadge>install deferred</StatusBadge>
          <StatusBadge>update deferred</StatusBadge>
          <StatusBadge>remove deferred</StatusBadge>
        </div>
        <p className="settings-help">
          Plugin install/update/remove and trust changes stay out of the browser until the typed settings mutation API and trust UX are designed.
        </p>
      </SettingsSection>
      <PluginSettingsSection status={status} />
    </div>
  );
}
