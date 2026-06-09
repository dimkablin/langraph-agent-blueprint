export type RuntimeEventSeverity = "info" | "warning" | "error";
export type AgentActivityStatus = "pending" | "running" | "success" | "error" | "blocked";

export type AgentActivitySource = {
  kind: string;
  name?: string | null;
  component?: string | null;
};

export type AgentActivityRef = {
  kind: string;
  path?: string | null;
  name?: string | null;
  id?: string | null;
};

export type AgentActivityEvent = {
  id: string;
  type: string;
  source: AgentActivitySource;
  category: string;
  status?: AgentActivityStatus | null;
  title: string;
  summary?: string | null;
  data: Record<string, unknown>;
  refs: AgentActivityRef[];
};

export type RuntimeStreamEvent =
  | { kind: "assistant_delta"; message_id: string; delta: string }
  | { kind: "assistant_final"; message_id: string; content: string }
  | { kind: "progress"; message: string; stage?: string | null; message_id?: string | null }
  | {
      kind: "tool_lifecycle";
      phase: "scheduled" | "started" | "completed" | "failed" | "blocked" | "permission_required";
      tool_call_id: string;
      tool_name: string;
      title?: string | null;
      args_summary?: string | null;
      result_summary?: string | null;
      command?: string | null;
      path?: string | null;
      exit_code?: number | null;
      duration_ms?: number | null;
      error?: { type: string; message: string } | null;
      details?: Record<string, unknown>;
    }
  | {
      kind: "permission_state";
      status: "required" | "approved" | "rejected" | "blocked";
      tool_call_id: string;
      tool_name: string;
      action?: string | null;
      risk?: string | null;
      args_summary?: string | null;
      reason?: string | null;
      args?: Record<string, unknown>;
      scope?: "tool" | "subagent";
      parent_session_id?: string | null;
      parent_thread_id?: string | null;
      child_session_id?: string | null;
      child_thread_id?: string | null;
      child_run_id?: string | null;
      subagent_name?: string | null;
    }
  | { kind: "error"; message: string; error_type?: string | null; recoverable?: boolean | null }
  | { kind: "artifact"; artifact_id: string; artifact_kind: string; uri?: string | null; title?: string | null; metadata?: Record<string, unknown> };

export type RuntimeEvent = {
  id: string;
  type: string;
  timestamp: string;
  session_id: string;
  node?: string | null;
  severity: RuntimeEventSeverity;
  data: Record<string, unknown>;
};

export type AttachmentRef = {
  id: string;
  kind: string;
  name?: string | null;
  uri?: string | null;
  path?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  trust?: string;
  metadata?: Record<string, unknown>;
};

export type PermissionRequest = {
  type?: string;
  tool_call_id: string;
  tool_name: string;
  action?: string | null;
  risk?: string | null;
  args_summary?: string | null;
  reason?: string | null;
  args?: Record<string, unknown>;
  scope?: "tool" | "subagent";
  parent_session_id?: string | null;
  parent_thread_id?: string | null;
  child_session_id?: string | null;
  child_thread_id?: string | null;
  child_run_id?: string | null;
  subagent_name?: string | null;
};

export type PermissionDecisionDTO = {
  tool_call_id: string;
  decision: "approved" | "rejected";
  reason?: string | null;
};

export type ModelIntelligenceLevel = "low" | "medium" | "high" | "very_high";
export type PermissionMode = "default" | "accept_edits" | "bypass_read_only" | "plan" | "strict";

export type ChatRequest = {
  message: string;
  project_id?: string | null;
  session_id?: string | null;
  thread_id?: string | null;
  model_intelligence?: ModelIntelligenceLevel | null;
  permission_mode?: PermissionMode | null;
  attachments?: AttachmentRef[];
};

export type GitStatusSummary = {
  staged: number;
  unstaged: number;
  untracked: number;
  conflicted: number;
};

export type WorkspaceInfo = {
  project_id: string;
  display_name: string;
  root_path: string;
  is_git_repo: boolean;
  current_branch?: string | null;
  branches: string[];
  git_status?: GitStatusSummary | null;
  dirty: boolean;
  created_at?: string | null;
  last_opened_at?: string | null;
};

export type WorkspaceCheckoutRequest = {
  branch: string;
  confirm_dirty?: boolean;
};

export type WorkspaceCheckoutResult = {
  ok: boolean;
  workspace: WorkspaceInfo;
  message: string;
};

export type ChatResponse = {
  session_id: string;
  thread_id: string;
  conversation_id?: string | null;
  final_response?: string | null;
  events: RuntimeEvent[];
  usage?: Record<string, unknown>;
  permission_required?: PermissionRequest | null;
};

export type ChatCancelRequest = {
  thread_id: string;
  session_id?: string | null;
  reason?: string | null;
};

export type ChatCancelResponse = {
  cancelled: boolean;
  thread_id: string;
  session_id?: string | null;
  reason?: string | null;
};

export type ConversationStatus = "active" | "archived" | "deleted";

export type ConversationRecordDTO = {
  conversation_id: string;
  session_id: string;
  thread_id: string;
  user_id: string;
  title?: string | null;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  schema_version: number;
};

export type ConversationListItemDTO = {
  conversation_id: string;
  session_id: string;
  thread_id: string;
  title?: string | null;
  status: ConversationStatus;
  message_count: number;
  event_count: number;
  tool_call_count: number;
  artifact_count: number;
  created_at: string;
  updated_at: string;
};

export type ConversationMessageDTO = {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
};

export type ConversationEventDTO = {
  event_id: string;
  conversation_id: string;
  type: string;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ConversationToolCallDTO = {
  tool_call_id: string;
  name: string;
  status: string;
  metadata: Record<string, unknown>;
};

export type ConversationArtifactDTO = {
  artifact_id: string;
  kind: string;
  uri?: string | null;
  metadata: Record<string, unknown>;
};

export type ConversationDetailDTO = {
  conversation: ConversationRecordDTO;
  messages: ConversationMessageDTO[];
  events: ConversationEventDTO[];
  tool_calls: ConversationToolCallDTO[];
  artifacts: ConversationArtifactDTO[];
};

export type StreamFrame =
  | { type: "event"; event: RuntimeEvent }
  | { type: "done"; session_id?: string | null; thread_id?: string | null; conversation_id?: string | null; final_response?: string | null }
  | { type: "error"; error: string };

export type ApprovalRequest = {
  thread_id: string;
  session_id?: string | null;
  decision: PermissionDecisionDTO;
};

export type RegistryItem = {
  name: string;
  description?: string;
  type?: string | null;
  status?: string | null;
  plugin_name?: string | null;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
};

export type RegistryMap = Record<string, RegistryItem>;

export type MessageDTO = {
  id: string;
  role: string;
  content: string;
  type?: string | null;
  tool_calls?: Record<string, unknown>[];
  tool_call_id?: string | null;
};

export type ToolCallRecordDTO = {
  id: string;
  name: string;
  status: string;
  content?: string;
  output_ref?: string | null;
  metadata?: Record<string, unknown>;
  error?: Record<string, unknown> | string | null;
};

export type ContextStateDTO = {
  references: Record<string, unknown>[];
  fragments: Record<string, unknown>[];
  attachments: Record<string, unknown>[];
  budget: Record<string, unknown>;
  model_context?: Record<string, unknown>;
  errors: Record<string, unknown>[];
};

export type SessionListItemDTO = {
  session_id: string;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  provider?: string | null;
  model?: string | null;
  message_count: number;
  event_count: number;
  tool_call_count: number;
  child_run_count: number;
  usage?: Record<string, unknown>;
};

export type ChildRunListItemDTO = {
  child_run_id: string;
  parent_session_id?: string | null;
  child_session_id?: string | null;
  child_thread_id?: string | null;
  name?: string | null;
  purpose?: string | null;
  status?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  summary?: string | null;
};

export type SessionDetailDTO = {
  session_id: string;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  provider?: string | null;
  model?: string | null;
  messages: MessageDTO[];
  events: RuntimeEvent[];
  tool_calls: ToolCallRecordDTO[];
  todos: Record<string, unknown>[];
  memory: Record<string, unknown>;
  usage: Record<string, unknown>;
  context: ContextStateDTO;
  child_runs: ChildRunListItemDTO[];
  metadata: Record<string, unknown>;
};

export type ConfigShowDTO = { values: Record<string, unknown> };
export type ConfigExplainDTO = {
  sources: Record<string, unknown>[];
  values: Record<string, unknown>[];
  diagnostics: Record<string, unknown>[];
};
export type ConfigValidateDTO = { ok: boolean; diagnostics: Record<string, unknown>[] };
export type PluginStatusDTO = {
  plugins: Record<string, unknown>[];
  contributions: Record<string, unknown>[];
  errors: Record<string, unknown>[];
  warnings: Record<string, unknown>[];
};
export type HookStatusDTO = { hooks: Record<string, unknown>[] };
export type MCPStatusDTO = {
  servers: Record<string, unknown>[];
  tools: Record<string, Record<string, unknown>>;
  resources: Record<string, Record<string, unknown>[]>;
  prompts: Record<string, Record<string, unknown>[]>;
  invalid_servers: Record<string, unknown>[];
  warnings: Record<string, unknown>[];
  errors: Record<string, unknown>[];
};
export type ObservabilityStatusDTO = {
  enabled: boolean;
  mode: string;
  sdk_installed?: boolean | null;
  base_url_configured?: boolean;
  public_key_present?: boolean;
  secret_key_present?: boolean;
  environment?: string | null;
  release?: string | null;
  capture_inputs?: boolean;
  capture_outputs?: boolean;
  runtime_events_mode?: string;
  last_error?: string | null;
};
