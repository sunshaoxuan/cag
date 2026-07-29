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
  last_ingestion: KnowledgeIngestion | null;
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
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  rejection_archive_name: string | null;
  rejection_archive_sha256: string | null;
  rejection_archive_created_at: string | null;
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
