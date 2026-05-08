import type { RuntimeStatus } from "../../api/status.ts";

export function RuntimeStatusPanel({ status }: { status: RuntimeStatus | null }) {
  return (
    <section className="panel-section" aria-label="Runtime status">
      <div className="section-heading">
        <h2>Status</h2>
        <span>read-only</span>
      </div>
      {!status ? (
        <p className="muted">Status endpoints pending.</p>
      ) : (
        <div className="status-grid">
          <StatusMetric label="Plugins" value={status.plugins?.plugins.length ?? null} />
          <StatusMetric label="Hooks" value={status.hooks?.hooks.length ?? null} />
          <StatusMetric label="MCP servers" value={status.mcp?.servers.length ?? null} />
          <StatusMetric label="Config" value={status.configValidation?.ok === false ? "warnings" : "ok"} />
          <StatusMetric label="Observability" value={status.observability?.mode || "unknown"} />
        </div>
      )}
    </section>
  );
}

function StatusMetric({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="status-metric">
      <span>{label}</span>
      <strong>{value ?? "n/a"}</strong>
    </div>
  );
}

