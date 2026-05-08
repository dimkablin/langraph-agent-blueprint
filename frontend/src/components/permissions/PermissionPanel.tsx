import { Check, ShieldAlert, X } from "lucide-react";

import { safeJson } from "../../runtime/events.ts";
import type { PermissionRequest } from "../../api/schemas.ts";

export function PermissionPanel({
  request,
  busy,
  onApprove,
  onReject,
}: {
  request: PermissionRequest | null;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!request) return null;
  return (
    <section className="permission-panel" role="alert">
      <ShieldAlert size={20} />
      <div className="permission-copy">
        <strong>{request.tool_name}</strong>
        <span>
          {request.action || "action"} · {request.risk || "unknown risk"}
        </span>
        {request.reason ? <p>{request.reason}</p> : null}
        {request.args_summary ? <code>{request.args_summary}</code> : null}
        {request.args ? <pre>{safeJson(request.args)}</pre> : null}
      </div>
      <div className="permission-actions">
        <button type="button" onClick={onApprove} disabled={busy}>
          <Check size={16} />
          Approve
        </button>
        <button className="danger" type="button" onClick={onReject} disabled={busy}>
          <X size={16} />
          Reject
        </button>
      </div>
    </section>
  );
}

