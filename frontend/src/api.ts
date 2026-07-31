export type Project = {
  id: string;
  code: string;
  name: string;
  default_branch: string;
  default_runtime_profile: string;
  allowed_runtime_profiles: string[];
};

export type Conversation = {
  id: string;
  project_id: string;
  project_code: string;
  title: string | null;
  codex_thread_id: string | null;
  created_at: string;
};

export type ValidationResult = {
  command: string;
  status: string;
};

export type FinalReport = {
  status: string;
  summary: string;
  root_cause: string | null;
  changes: Array<{ file?: string; summary?: string }>;
  validation: ValidationResult[];
  approvals: unknown[];
  warnings: string[];
  next_actions: string[];
};

export type Task = {
  id: string;
  trace_id: string;
  project_id: string;
  project_code: string;
  conversation_id: string | null;
  trigger_source: string;
  client_id: string;
  client_request_id: string;
  request_hash: string;
  events_url: string;
  audit_url: string;
  prompt: string;
  runtime_profile: string;
  knowledge_mode: string;
  harness_profile: string;
  learning_mode: string;
  knowledge_usage: {
    status?: string;
    citation_count?: number;
    citations?: Array<Record<string, unknown>>;
  } | null;
  status: string;
  final_report: FinalReport | null;
  error: string | null;
  workspace_id: string | null;
  workspace_commit: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type KnowledgeStatus = {
  enabled: boolean;
  ready: boolean;
  scheduler_enabled: boolean;
  scheduler_running: boolean;
  scheduler_poll_seconds: number;
  reason?: string;
  version?: string;
  models?: string[];
  embedding_model?: string;
  memory_model?: string;
  dimensions?: number;
};

export type QueueStatus = {
  running: boolean;
  configured_workers: Record<string, number>;
  redis: {
    enabled: boolean;
    connected: boolean;
    last_error?: string | null;
  };
  queues: Array<{
    name: string;
    counts: Record<string, number>;
    oldest_queued_at: string | null;
    oldest_wait_seconds: number;
  }>;
  workers: Array<{
    id: string;
    worker_key: string;
    queue_name: string;
    status: string;
    current_item_id: string | null;
    heartbeat_at: string;
  }>;
};

export type OperationalIssueArtifact = {
  id: string;
  artifact_type: "plan" | "review" | "implementation" | "evaluation";
  revision: number;
  content: Record<string, unknown>;
  created_by: string;
  created_at: string;
};

export type OperationalIssueEvent = {
  id: string;
  sequence: number;
  type: string;
  data: Record<string, unknown>;
  created_at: string;
};

export type OperationalIssueOccurrence = {
  id: string;
  external_event_id: string | null;
  event_type: string;
  error_type: string | null;
  error_message: string;
  evidence: Record<string, unknown>;
  occurred_at: string;
};

export type OperationalResolutionMode =
  | "agent_self_improvement"
  | "human_code_change"
  | "external_operator_action"
  | "mixed"
  | "out_of_scope"
  | "undetermined";

export type OperationalDecisionBrief = {
  administrator_language?: "zh-CN";
  problem_summary?: string;
  impact_summary?: string;
  root_cause_summary?: string;
  root_cause_confidence?: number;
  improvement_goal?: string;
  resolution_mode?: OperationalResolutionMode;
  resolution_mode_reason?: string;
  resolution_mode_confidence?: number;
  recommended_changes?: Array<{
    area?: string;
    change?: string;
    reason?: string;
  }>;
  validation_plan?: string[];
  rollback_plan?: string[];
  administrator_actions?: string[];
  review_summary?: string;
  review_recommendation?: "approve" | "revise" | "reject";
  blocking_findings?: Array<{
    code?: string;
    severity?: string;
    title?: string;
    finding?: string;
    required_change?: string;
  }>;
  approval_conditions?: string[];
  approval_ready?: boolean;
};

export type OperationalIssue = {
  id: string;
  project_id: string;
  parent_issue_id: string | null;
  implementation_task_id: string | null;
  code: string;
  source_type: string;
  source_id: string | null;
  title: string;
  summary: string;
  severity: "low" | "medium" | "high" | "critical";
  boundary: string | null;
  boundary_confidence: number | null;
  resolution_mode: OperationalResolutionMode | null;
  resolution_mode_confidence: number | null;
  resolution_mode_reason: string | null;
  decision_brief: OperationalDecisionBrief;
  review_recommendation: "approve" | "revise" | "reject" | null;
  blocking_finding_count: number;
  status: string;
  occurrence_count: number;
  evidence: Record<string, unknown>;
  allowed_actions: string[];
  required_human_input: string | null;
  approval_status: string;
  approved_by: string | null;
  approval_note: string | null;
  approved_at: string | null;
  improvement_branch: string | null;
  evaluation_status: string;
  resolution: string | null;
  closed_by: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  occurrences?: OperationalIssueOccurrence[];
  artifacts?: OperationalIssueArtifact[];
  events?: OperationalIssueEvent[];
};

export type OperationalDashboard = {
  total: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  by_boundary: Record<string, number>;
  by_resolution_mode: Record<string, number>;
};

export type OperationsAdminCredentials = {
  identity: string;
  token: string;
};

export type KnowledgeSource = {
  id: string;
  project_id: string;
  name: string;
  source_type:
    | "local_directory"
    | "network_share"
    | "git"
    | "gitlab"
    | "svn";
  location: string;
  root_path: string;
  reference: string | null;
  subpath: string | null;
  credential_username: string | null;
  credential_configured: boolean;
  enabled: boolean;
  scope: "tenant" | "product";
  status: string;
  source_commit: string | null;
  index_fingerprint: string | null;
  active_generation_id: string | null;
  approved_for_codex: boolean;
  error: string | null;
  last_validated_at: string | null;
  last_collected_at: string | null;
  sync_mode: "manual" | "scheduled";
  sync_interval_minutes: number;
  next_sync_at: string | null;
  last_sync_attempt_at: string | null;
  last_content_change_at: string | null;
  consecutive_failures: number;
  scheduler_claimed: boolean;
  entry_summary: KnowledgeSourceEntrySummary;
  retrieval_health: KnowledgeRetrievalHealth;
  last_ingestion: KnowledgeIngestion | null;
};

export type KnowledgeRetrievalHealth = {
  status:
    | "searchable"
    | "refreshing"
    | "degraded"
    | "indexing"
    | "scope_mismatch"
    | "approval_required"
    | "disabled"
    | "empty";
  total_chunks: number;
  accessible_chunks: number;
  legacy_documents: number;
  active_generation_id: string | null;
};

export type KnowledgeIngestion = {
  id: string;
  source_id: string;
  status: string;
  files_seen: number;
  chunks_written: number;
  rejected_files: number;
  skipped_files: number;
  duplicate_files: number;
  unchanged_files: number;
  vectors_reused: number;
  changed_files: number;
  removed_files: number;
  trigger: "manual" | "scheduled";
  error: string | null;
  error_summary: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  rejection_archive_name: string | null;
  rejection_archive_sha256: string | null;
  rejection_archive_created_at: string | null;
};

export type KnowledgeSourceEntrySummary = {
  total: number;
  code: number;
  document: number;
  metadata_only: number;
  path_only: number;
  removed: number;
};

export type KnowledgeSourceEntry = {
  id: string;
  source_id: string;
  relative_path: string;
  entry_kind: "file" | "directory";
  extension: string;
  file_size: number | null;
  modified_at: string | null;
  processing_mode: "code" | "document" | "metadata_only" | "path_only";
  processing_status: string;
  reason_code: string | null;
  present: boolean;
  last_seen_ingestion_id: string | null;
  processor_fingerprint: string | null;
  content_hash: string | null;
  first_seen_at: string;
  last_seen_at: string;
  processed_at: string | null;
  removed_at: string | null;
};

export type KnowledgeSourceEntryPage = {
  items: KnowledgeSourceEntry[];
  total: number;
  limit: number;
  offset: number;
  summary: KnowledgeSourceEntrySummary;
};

export type KnowledgeIngestionRejection = {
  id: string;
  ingestion_id: string;
  relative_path: string;
  entry_kind: "file" | "directory";
  disposition: "rejected" | "skipped";
  extension: string;
  file_size: number | null;
  reason_code: string;
  extractor: string;
  error_type: string | null;
  error_message: string | null;
  created_at: string;
};

export type KnowledgeIngestionRejectionPage = {
  items: KnowledgeIngestionRejection[];
  total: number;
  limit: number;
  offset: number;
  summary: Array<{
    disposition: "rejected" | "skipped";
    reason_code: string;
    count: number;
  }>;
  archive_available: boolean;
};

export type KnowledgeIngestionEvent = {
  event_id: string;
  ingestion_id: string;
  sequence: number;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
};

export type CodeKnowledgeSummary = {
  symbols: number;
  relations: number;
  document_links: number;
  unresolved_relations: number;
  languages: Record<string, number>;
  kinds: Record<string, number>;
};

export type CodeRelation = {
  id: string;
  source_symbol_id: string;
  target_symbol_id: string | null;
  relation_type: string;
  target_name: string;
  confidence: number;
  evidence: Record<string, unknown>;
};

export type CodeDocumentLink = {
  id: string;
  document_id: string;
  path: string;
  link_type: string;
  score: number;
  evidence: Record<string, unknown>;
};

export type CodeSymbol = {
  id: string;
  document_id: string;
  path: string;
  language: string;
  kind: string;
  name: string;
  qualified_name: string;
  signature: string;
  start_line: number;
  end_line: number;
  scope: string;
  parser: string | null;
  diagnostics: string[];
  outgoing_relations?: CodeRelation[];
  incoming_relations?: CodeRelation[];
  document_links?: CodeDocumentLink[];
};

export type KnowledgeSourceCreate = {
  project_id: string;
  name: string;
  source_type: KnowledgeSource["source_type"];
  location: string;
  reference?: string;
  subpath?: string;
  scope: "tenant" | "product";
  approved_for_codex: boolean;
  sync_mode: KnowledgeSource["sync_mode"];
  sync_interval_minutes: number;
  credential_username?: string;
  credential_secret?: string;
};

export type MemoryCandidate = {
  id: string;
  scope: "tenant" | "product";
  kind: string;
  title: string;
  content: string;
  confidence: number;
  status: string;
};

export type CapabilityAsset = {
  id: string;
  kind: string;
  code: string;
  version: string;
  status: string;
  content_hash: string;
  shadow_runs: number;
  canary_runs: number;
  rolling_quality_delta: number;
  active: boolean;
};

export type StandardControl = {
  id: string;
  code: string;
  framework: string;
  title: string;
  implementation_status: string;
  evidence_paths: string[];
  certification_claimed: boolean;
};

export type ApprovalRequest = {
  id: string;
  task_id: string;
  agent_run_id: string | null;
  request_type: string;
  subject: string;
  risk_level: string;
  status: string;
  policy_decision: string;
  requested_at: string;
  resolution_note: string | null;
};

export type TaskEvent = {
  event_id: string;
  task_id: string;
  sequence: number;
  global_sequence?: number;
  task_sequence?: number;
  conversation_id?: string;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
};

export type AuditTask = {
  trace_id: string;
  task_id: string;
  project_id: string;
  project_code: string;
  conversation_id: string | null;
  trigger_source: string;
  client_id: string;
  client_request_id: string;
  request_hash: string;
  status: string;
  event_count: number;
  last_event_type: string | null;
  last_global_sequence: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  events_url: string;
  audit_url: string;
};

export type AuditEvent = {
  event_id: string;
  trace_id: string;
  task_id: string;
  sequence: number;
  task_sequence: number;
  conversation_id?: string;
  type: string;
  timestamp: string;
  trigger_source: string;
  client_id: string;
  client_request_id: string;
  project_id: string;
  project_code: string;
  data: Record<string, unknown>;
};

export function resolveApiBaseUrl(
  configuredBaseUrl: string | undefined,
): string {
  const normalized = configuredBaseUrl?.trim();
  if (!normalized || normalized === "same-origin") return "";
  return normalized.replace(/\/+$/, "");
}

const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
);

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(payload?.detail ?? `请求失败：HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/v1/projects");
}

export function createConversation(
  projectId: string,
  title?: string,
): Promise<Conversation> {
  return request<Conversation>("/api/v1/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      title,
    }),
  });
}

export function createTask(
  projectId: string,
  prompt: string,
  conversationId?: string,
  knowledgeMode = "assist",
  harnessProfile = "single",
  learningMode = "capture",
): Promise<Task> {
  return request<Task>("/api/v1/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CAG-Source": "test_console",
      "X-CAG-Client-ID": "cag-web-test",
      "X-Request-ID": crypto.randomUUID(),
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify({
      project_id: projectId,
      prompt,
      conversation_id: conversationId,
      knowledge_mode: knowledgeMode,
      harness_profile: harnessProfile,
      learning_mode: learningMode,
    }),
  });
}

export function listAuditTasks(): Promise<AuditTask[]> {
  return request<AuditTask[]>("/api/v1/audit/tasks?limit=100");
}

export function auditEventsUrl(afterSequence = 0): string {
  const query = new URLSearchParams({
    after_sequence: String(afterSequence),
    follow: "true",
  });
  return `${API_BASE_URL}/api/v1/audit/events?${query}`;
}

export function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return request<KnowledgeStatus>("/api/v1/knowledge/status");
}

export function getQueueStatus(): Promise<QueueStatus> {
  return request<QueueStatus>("/api/v1/queue/status");
}

export function getOperationalDashboard(): Promise<OperationalDashboard> {
  return request<OperationalDashboard>("/api/v1/operations/dashboard");
}

export function listOperationalIssues(): Promise<OperationalIssue[]> {
  return request<OperationalIssue[]>("/api/v1/operations/issues");
}

export function getOperationalIssue(
  issueId: string,
): Promise<OperationalIssue> {
  return request<OperationalIssue>(
    `/api/v1/operations/issues/${issueId}`,
  );
}

function operationsAdminHeaders(
  credentials: OperationsAdminCredentials,
): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-CAG-Admin-Identity": credentials.identity,
    "X-CAG-Admin-Token": credentials.token,
  };
}

export function approveOperationalIssue(
  issueId: string,
  note: string,
  credentials: OperationsAdminCredentials,
): Promise<OperationalIssue> {
  return request<OperationalIssue>(
    `/api/v1/operations/issues/${issueId}/approve`,
    {
      method: "POST",
      headers: operationsAdminHeaders(credentials),
      body: JSON.stringify({
        note,
      }),
    },
  );
}

export function rejectOperationalIssue(
  issueId: string,
  note: string,
  credentials: OperationsAdminCredentials,
): Promise<OperationalIssue> {
  return request<OperationalIssue>(
    `/api/v1/operations/issues/${issueId}/reject`,
    {
      method: "POST",
      headers: operationsAdminHeaders(credentials),
      body: JSON.stringify({
        note,
      }),
    },
  );
}

export function recordOperationalImplementation(
  issueId: string,
  payload: {
    summary: string;
    branch: string | null;
    commits: string[];
  },
  credentials: OperationsAdminCredentials,
): Promise<OperationalIssue> {
  return request<OperationalIssue>(
    `/api/v1/operations/issues/${issueId}/implementations`,
    {
      method: "POST",
      headers: operationsAdminHeaders(credentials),
      body: JSON.stringify({
        validation: [],
        ...payload,
      }),
    },
  );
}

export function reopenOperationalIssue(
  issueId: string,
  reason: string,
  credentials: OperationsAdminCredentials,
): Promise<OperationalIssue> {
  return request<OperationalIssue>(
    `/api/v1/operations/issues/${issueId}/reopen`,
    {
      method: "POST",
      headers: operationsAdminHeaders(credentials),
      body: JSON.stringify({
        reason,
      }),
    },
  );
}

export function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  return request<KnowledgeSource[]>("/api/v1/knowledge/sources");
}

export function createKnowledgeSource(
  payload: KnowledgeSourceCreate,
): Promise<KnowledgeSource> {
  return request<KnowledgeSource>("/api/v1/knowledge/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateKnowledgeSource(
  sourceId: string,
  payload: Record<string, unknown>,
): Promise<KnowledgeSource> {
  return request<KnowledgeSource>(
    `/api/v1/knowledge/sources/${sourceId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export function deleteKnowledgeSource(sourceId: string): Promise<void> {
  return request<void>(`/api/v1/knowledge/sources/${sourceId}`, {
    method: "DELETE",
  });
}

export function validateKnowledgeSource(
  sourceId: string,
): Promise<{ ok: boolean; revision: string | null; message: string }> {
  return request(`/api/v1/knowledge/sources/${sourceId}/validate`, {
    method: "POST",
  });
}

export function revealKnowledgeSourceCredential(
  sourceId: string,
): Promise<{ username: string; secret: string }> {
  return request<{ username: string; secret: string }>(
    `/api/v1/knowledge/sources/${sourceId}/credential/reveal`,
    { method: "POST" },
  );
}

export function ingestKnowledgeSource(
  sourceId: string,
): Promise<KnowledgeIngestion> {
  return request<KnowledgeIngestion>(
    `/api/v1/knowledge/sources/${sourceId}/ingest`,
    { method: "POST" },
  );
}

export function listKnowledgeSourceIngestions(
  sourceId: string,
): Promise<KnowledgeIngestion[]> {
  return request<KnowledgeIngestion[]>(
    `/api/v1/knowledge/sources/${sourceId}/ingestions`,
  );
}

export function listKnowledgeSourceEntries(
  sourceId: string,
  limit = 100,
  offset = 0,
): Promise<KnowledgeSourceEntryPage> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    present: "true",
  });
  return request<KnowledgeSourceEntryPage>(
    `/api/v1/knowledge/sources/${sourceId}/entries?${query}`,
  );
}

export function knowledgeIngestionEventsUrl(ingestionId: string): string {
  const query = new URLSearchParams({
    after_sequence: "0",
    follow: "true",
  });
  return `${API_BASE_URL}/api/v1/knowledge/ingestions/${ingestionId}/events?${query}`;
}

export function listKnowledgeIngestionRejections(
  ingestionId: string,
  limit = 100,
  offset = 0,
): Promise<KnowledgeIngestionRejectionPage> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request<KnowledgeIngestionRejectionPage>(
    `/api/v1/knowledge/ingestions/${ingestionId}/rejections?${query}`,
  );
}

export function knowledgeIngestionRejectionsExportUrl(
  ingestionId: string,
): string {
  return `${API_BASE_URL}/api/v1/knowledge/ingestions/${ingestionId}/rejections/export`;
}

export function knowledgeIngestionRejectionsArchiveUrl(
  ingestionId: string,
): string {
  return `${API_BASE_URL}/api/v1/knowledge/ingestions/${ingestionId}/rejections/archive`;
}

export function getCodeKnowledgeSummary(
  projectId: string,
): Promise<CodeKnowledgeSummary> {
  const query = new URLSearchParams({ project_id: projectId });
  return request<CodeKnowledgeSummary>(
    `/api/v1/knowledge/code/summary?${query}`,
  );
}

export function listCodeSymbols(
  projectId: string,
  search = "",
  kind = "",
): Promise<CodeSymbol[]> {
  const query = new URLSearchParams({
    project_id: projectId,
    query: search,
    kind,
    limit: "200",
  });
  return request<CodeSymbol[]>(
    `/api/v1/knowledge/code/symbols?${query}`,
  );
}

export function getCodeSymbol(
  projectId: string,
  symbolId: string,
): Promise<CodeSymbol> {
  const query = new URLSearchParams({ project_id: projectId });
  return request<CodeSymbol>(
    `/api/v1/knowledge/code/symbols/${symbolId}?${query}`,
  );
}

export function listMemoryCandidates(): Promise<MemoryCandidate[]> {
  return request<MemoryCandidate[]>("/api/v1/memory-candidates");
}

export function transitionMemoryCandidate(
  candidateId: string,
  action: "approve" | "reject" | "promote" | "deprecate",
): Promise<{ id: string; scope: string; status: string }> {
  return request(`/api/v1/memory-candidates/${candidateId}/${action}`, {
    method: "POST",
  });
}

export function listCapabilities(
  kind: "skills" | "tools" | "validators" | "harness-profiles",
): Promise<CapabilityAsset[]> {
  return request<CapabilityAsset[]>(`/api/v1/capabilities/${kind}`);
}

export function listStandardControls(): Promise<StandardControl[]> {
  return request<StandardControl[]>("/api/v1/standards/controls");
}

export function listPromotions(): Promise<
  Array<{
    id: string;
    asset_id: string;
    from_status: string;
    to_status: string;
    decision: string;
    created_at: string;
  }>
> {
  return request("/api/v1/promotions");
}

export function listTaskApprovals(taskId: string): Promise<ApprovalRequest[]> {
  return request<ApprovalRequest[]>(`/api/v1/tasks/${taskId}/approvals`);
}

export function resolveApproval(
  approvalId: string,
  decision: "approve" | "deny",
): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/v1/approvals/${approvalId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      decision,
      resolved_by: "gateway-frontend",
      note: "Resolved by an authenticated Gateway operator",
    }),
  });
}

export function getTask(taskId: string): Promise<Task> {
  return request<Task>(`/api/v1/tasks/${taskId}`);
}

export function taskEventsUrl(taskId: string, afterSequence = 0): string {
  const query = new URLSearchParams({
    after_sequence: String(afterSequence),
    follow: "true",
  });
  return `${API_BASE_URL}/api/v1/tasks/${taskId}/events?${query}`;
}

export function conversationEventsUrl(
  conversationId: string,
  afterSequence = 0,
): string {
  const query = new URLSearchParams({
    after_sequence: String(afterSequence),
    follow: "true",
  });
  return `${API_BASE_URL}/api/v1/conversations/${conversationId}/events?${query}`;
}
