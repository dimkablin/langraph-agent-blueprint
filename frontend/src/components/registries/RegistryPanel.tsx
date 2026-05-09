import { useMemo, useState } from "react";

import type { RegistryMap } from "../../api/schemas.ts";
import { IconCommand, IconSearch, IconShieldExclamation, IconSparkles } from "../../icons.ts";
import { registryItems } from "../../runtime/viewModels.ts";

export function RegistryPanel({
  commands,
  skills,
  tools,
  error,
}: {
  commands: RegistryMap;
  skills: RegistryMap;
  tools: RegistryMap;
  error: string | null;
}) {
  const [query, setQuery] = useState("");
  const groups = useMemo(
    () => [
      { title: "Commands", icon: <IconCommand size={17} />, items: registryItems(commands) },
      { title: "Skills", icon: <IconSparkles size={17} />, items: registryItems(skills) },
      { title: "Tools", icon: <IconShieldExclamation size={17} />, items: registryItems(tools) },
    ],
    [commands, skills, tools],
  );
  const normalized = query.trim().toLowerCase();

  return (
    <section className="panel-section" aria-label="Runtime registries">
      <div className="section-heading">
        <h2>Registries</h2>
        <span>{groups.reduce((total, group) => total + group.items.length, 0)}</span>
      </div>
      <label className="search-box">
        <IconSearch size={16} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter registries" />
      </label>
      {error ? <p className="error-text">{error}</p> : null}
      {groups.map((group) => (
        <div className="registry-group" key={group.title}>
          <h3>
            {group.icon}
            {group.title}
          </h3>
          {group.items
            .filter((item) => !normalized || item.name.toLowerCase().includes(normalized) || (item.description || "").toLowerCase().includes(normalized))
            .slice(0, 12)
            .map((item) => (
              <div className="registry-row" key={`${group.title}-${item.name}`}>
                <code>{item.name}</code>
                <span>{item.description || item.type || item.status || ""}</span>
              </div>
            ))}
        </div>
      ))}
    </section>
  );
}
