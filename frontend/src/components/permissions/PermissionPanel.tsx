import { safeJson } from "../../runtime/events.ts";
import type { PermissionRequest } from "../../api/schemas.ts";
import { IconCheck, IconShieldExclamation, IconX } from "../../icons.ts";

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
      <div className="permission-command-description">
        {request.args_summary ? <code>{request.args_summary}</code> : null}
        {request.args ? <pre>{safeJson(request.args)}</pre> : null}
      </div>
      <div className="permission-review-row">
        <div className="permission-copy">
          <IconShieldExclamation size={23} />
          <div>
            <strong>{request.tool_name}</strong>
            <span>
              {request.action || "action"} · {request.risk || "unknown risk"}
            </span>
            {request.reason ? <p>{request.reason}</p> : null}
          </div>
        </div>
        <div className="permission-actions">
          <button type="button" onClick={onApprove} disabled={busy}>
            <IconCheck size={18} />
            Approve
          </button>
          <button className="danger" type="button" onClick={onReject} disabled={busy}>
            <IconX size={18} />
            Reject
          </button>
        </div>
      </div>
    </section>
  );
}
