import { useEffect, useState } from "react";

import type { PermissionRequest } from "../../api/schemas.ts";
import { IconCheck, IconChevronRight, IconShieldExclamation, IconX } from "../../icons.ts";
import { safeJson } from "../../runtime/events.ts";

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
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setExpanded(false);
  }, [request?.tool_call_id]);

  if (!request) return null;

  const hasArgs = hasPermissionArgs(request.args);
  const argsPreview = request.args_summary || (hasArgs ? safeJson(request.args) : null);
  const permissionDetailsText = expanded && hasArgs ? safeJson(request.args) : argsPreview || "";
  const permissionDetailsCodeClassName = expanded ? "permission-details-code permission-details-expanded" : "permission-details-code";

  return (
    <section className="permission-panel" role="alert">
      <div className="permission-review-row">
        <div className="permission-copy">
          <IconShieldExclamation size={23} />
          <div>
            <strong>{request.tool_name}</strong>
            {request.reason ? <p>{request.reason}</p> : null}
          </div>
        </div>
      </div>
      {argsPreview || hasArgs ? (
        <div className="permission-command-description">
          {hasArgs ? (
            <button
              type="button"
              className="permission-details-block"
              aria-label="Toggle permission details"
              aria-expanded={expanded}
              onClick={() => setExpanded((value) => !value)}
            >
              <code className={permissionDetailsCodeClassName}>{permissionDetailsText}</code>
              <span className="permission-details-toggle" aria-hidden="true">
                <IconChevronRight size={14} className={expanded ? "rotated" : ""} />
              </span>
            </button>
          ) : (
            <code>{argsPreview}</code>
          )}
        </div>
      ) : null}
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
    </section>
  );
}

function hasPermissionArgs(args: PermissionRequest["args"]): args is Record<string, unknown> {
  return Boolean(args && Object.keys(args).length > 0);
}
