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
  project_id: string;
  project_code: string;
  conversation_id: string | null;
  prompt: string;
  runtime_profile: string;
  knowledge_mode: string;
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
  root_path: string;
  scope: "tenant" | "product";
  status: string;
  source_commit: string | null;
  approved_for_codex: boolean;
  error: string | null;
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

export type TaskEvent = {
  event_id: string;
  task_id: string;
  sequence: number;
  task_sequence?: number;
  conversation_id?: string;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(payload?.detail ?? `请求失败：HTTP ${response.status}`);
  }
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
): Promise<Task> {
  return request<Task>("/api/v1/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      prompt,
      conversation_id: conversationId,
      knowledge_mode: knowledgeMode,
    }),
  });
}

export function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return request<KnowledgeStatus>("/api/v1/knowledge/status");
}

export function listKnowledgeSources(): Promise<KnowledgeSource[]> {
  return request<KnowledgeSource[]>("/api/v1/knowledge/sources");
}

export function createKnowledgeSource(
  projectId: string,
  name: string,
  rootPath: string,
  scope: "tenant" | "product",
): Promise<KnowledgeSource> {
  return request<KnowledgeSource>("/api/v1/knowledge/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      name,
      root_path: rootPath,
      scope,
      approved_for_codex: true,
    }),
  });
}

export function ingestKnowledgeSource(
  sourceId: string,
): Promise<{ id: string }> {
  return request<{ id: string }>(
    `/api/v1/knowledge/sources/${sourceId}/ingest`,
    { method: "POST" },
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
