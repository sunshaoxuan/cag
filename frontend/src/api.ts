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
  status: string;
  final_report: FinalReport | null;
  error: string | null;
  workspace_id: string | null;
  workspace_commit: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
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
): Promise<Task> {
  return request<Task>("/api/v1/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      prompt,
      conversation_id: conversationId,
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
