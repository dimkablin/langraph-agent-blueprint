import type { RegistryMap } from "../../api/schemas.ts";
import { registryItems } from "../../runtime/viewModels.ts";
import { EmptySettings, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function SkillSettingsSection({ skills }: { skills: RegistryMap }) {
  const items = registryItems(skills);
  return (
    <SettingsSection title="Skills" eyebrow="read-only">
      {items.length ? (
        <div className="settings-card-list">
          {items.slice(0, 12).map((skill) => (
            <article className="settings-card" key={skill.name}>
              <div>
                <strong>{skill.name}</strong>
                <span>{stringValue(skill.source_type, "builtin")}</span>
              </div>
              <p>{skill.description || "No description."}</p>
              <div className="settings-inline-badges">
                <StatusBadge tone={skill.enabled === false ? "warning" : "ok"}>{skill.enabled === false ? "disabled" : "enabled"}</StatusBadge>
                <StatusBadge>{allowedTools(skill.allowed_tools)}</StatusBadge>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptySettings>No skills registered.</EmptySettings>
      )}
    </SettingsSection>
  );
}

function allowedTools(value: unknown): string {
  return Array.isArray(value) && value.length ? `${value.length} allowed tools` : "no allowed tools";
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
