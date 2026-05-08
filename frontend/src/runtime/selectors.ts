import type { ActivityItem, RuntimeState } from "./reducer.ts";
import { LOW_SIGNAL_EVENTS } from "./events.ts";

export function visibleActivities(state: RuntimeState, includeDebug = false): ActivityItem[] {
  if (includeDebug) {
    return state.activities;
  }
  return state.activities.filter((item) => !LOW_SIGNAL_EVENTS.has(item.eventType));
}

export function statusText(state: RuntimeState): string {
  if (state.isStreaming) return "running";
  if (state.pendingPermission) return "approval needed";
  if (state.error) return "error";
  return "idle";
}
