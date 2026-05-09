import type { MCPStatusDTO } from "../../api/schemas.ts";
import { MCPSettingsSection } from "./MCPSettingsSection.tsx";
import { SettingsSection } from "./SettingsSection.tsx";

export function MCPServersSettingsTab({ status }: { status: MCPStatusDTO | null }) {
  return (
    <div className="settings-tab-panel" aria-label="Серверы MCP">
      <SettingsSection title="Passive status" eyebrow="safe snapshot">
        <p className="settings-help">
          Discovery is explicit; opening Settings does not start MCP servers. This page reads the passive <code>/mcp/snapshot</code> endpoint only.
        </p>
      </SettingsSection>
      <MCPSettingsSection status={status} />
    </div>
  );
}
