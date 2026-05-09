import { useMemo, useState } from "react";

import type { RegistryItem, RegistryMap } from "../../api/schemas.ts";
import { registryItems } from "../../runtime/viewModels.ts";
import { EmptySettings, SettingsSection, StatusBadge } from "./SettingsSection.tsx";

export function SkillsSettingsTab({ skills }: { skills: RegistryMap }) {
  const [query, setQuery] = useState("");
  const items = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const all = registryItems(skills);
    if (!normalized) return all;
    return all.filter((skill) => skillMatches(skill, normalized));
  }, [query, skills]);

  return (
    <div className="settings-tab-panel" aria-label="Скилы">
      <SettingsSection title="Skill registry" eyebrow="read-only">
        <label className="settings-search">
          <span>Search skills</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="remember, superpowers, debug..." />
        </label>
        {items.length ? (
          <div className="settings-card-list settings-card-list-spacious">
            {items.map((skill) => (
              <article className="settings-card" key={skill.name}>
                <div>
                  <strong>{skill.name}</strong>
                  <span>{stringValue(skill.source_type, "builtin")}</span>
                </div>
                <p>{skill.description || "No description."}</p>
                <div className="settings-inline-badges">
                  <StatusBadge tone={skill.enabled === false ? "warning" : "ok"}>{skill.enabled === false ? "disabled" : "enabled"}</StatusBadge>
                  <StatusBadge>{allowedTools(skill.allowed_tools)}</StatusBadge>
                  {skill.plugin_name ? <StatusBadge>{String(skill.plugin_name)}</StatusBadge> : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptySettings>No skills match this filter.</EmptySettings>
        )}
      </SettingsSection>
    </div>
  );
}

function skillMatches(skill: RegistryItem, query: string): boolean {
  return [skill.name, skill.description, skill.source_type, skill.plugin_name].some((value) => String(value || "").toLowerCase().includes(query));
}

function allowedTools(value: unknown): string {
  return Array.isArray(value) && value.length ? `${value.length} allowed tools` : "no allowed tools";
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}
