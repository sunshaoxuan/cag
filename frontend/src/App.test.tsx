import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Conversation, Task } from "./api";

const project = {
  id: "6ee71a6a-f30a-4a2d-a281-309c7511b832",
  code: "cag",
  name: "Codex/ChatGPT Agent Gateway",
  default_branch: "master",
  default_runtime_profile: "general-engineering",
  allowed_runtime_profiles: [
    "general-engineering",
    "self-improvement-candidate",
  ],
};

const conversation: Conversation = {
  id: "11111111-1111-4111-8111-111111111111",
  project_id: project.id,
  project_code: project.code,
  title: "运行测试",
  codex_thread_id: null,
  created_at: "2026-07-27T00:00:00Z",
};

function queuedTask(id: string, prompt: string): Task {
  return {
    id,
    trace_id: id,
    project_id: project.id,
    project_code: project.code,
    conversation_id: conversation.id,
    trigger_source: "test_console",
    client_id: "cag-web-test",
    client_request_id: `request-${id}`,
    request_hash: "a".repeat(64),
    events_url: `/api/v1/tasks/${id}/events`,
    audit_url: `/api/v1/audit/tasks/${id}`,
    prompt,
    runtime_profile: "general-engineering",
    knowledge_mode: "assist",
    harness_profile: "single",
    learning_mode: "capture",
    knowledge_usage: null,
    status: "queued",
    final_report: null,
    error: null,
    workspace_id: null,
    workspace_commit: null,
    created_at: "2026-07-27T00:00:00Z",
    started_at: null,
    completed_at: null,
  };
}

function completedTask(task: Task): Task {
  return {
    ...task,
    status: "completed",
    workspace_id: `${project.id}/${task.id}`,
    workspace_commit: "1234567890abcdef1234567890abcdef12345678",
    started_at: "2026-07-27T00:00:01Z",
    completed_at: "2026-07-27T00:00:02Z",
    final_report: {
      status: "completed",
      summary: `已完成：${task.prompt}`,
      root_cause: null,
      changes: [],
      validation: [{ command: "pytest", status: "passed" }],
      approvals: [],
      warnings: [],
      next_actions: [],
    },
  };
}

class MockEventSource {
  static instances: MockEventSource[] = [];
  listeners = new Map<string, EventListener[]>();
  onerror: ((event: Event) => void) | null = null;

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  close() {}

  emit(type: string, data: object) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }
}

function jsonResponse(payload: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    json: async () => payload,
  } as Response;
}

async function openConversationPage() {
  fireEvent.click(
    screen.getByRole("link", { name: "API 测试台" }),
  );
  await screen.findByRole("heading", { name: "连续对话测试" });
}

describe("Agent Gateway conversation page", () => {
  let submittedTasks: Task[];
  let pendingApprovals: Array<Record<string, unknown>>;

  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    MockEventSource.instances = [];
    submittedTasks = [];
    pendingApprovals = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/v1/projects")) {
          return jsonResponse([project]);
        }
        if (url.endsWith("/api/v1/knowledge/status")) {
          return jsonResponse({
            enabled: true,
            ready: true,
            embedding_model: "qwen3-embedding:8b",
            memory_model: "qwen3:14b",
            dimensions: 1024,
          });
        }
        if (url.endsWith("/api/v1/knowledge/sources")) {
          return jsonResponse([]);
        }
        if (url.endsWith("/api/v1/memory-candidates")) {
          return jsonResponse([]);
        }
        if (url.includes("/api/v1/capabilities/")) {
          return jsonResponse([]);
        }
        if (url.endsWith("/api/v1/standards/controls")) {
          return jsonResponse([
            {
              id: "control-1",
              code: "RAG-01",
              framework: "NeurIPS RAG",
              title: "Non-parametric evidence retrieval",
              implementation_status: "mapped",
              evidence_paths: ["docs/standards-control-matrix.md"],
              certification_claimed: false,
            },
          ]);
        }
        if (url.endsWith("/api/v1/promotions")) {
          return jsonResponse([]);
        }
        if (url.endsWith("/api/v1/audit/tasks?limit=100")) {
          return jsonResponse([]);
        }
        if (url.includes("/api/v1/tasks/") && url.endsWith("/approvals")) {
          return jsonResponse(pendingApprovals);
        }
        if (
          url.includes("/api/v1/approvals/") &&
          url.endsWith("/resolve") &&
          init?.method === "POST"
        ) {
          const resolved = {
            ...pendingApprovals[0],
            status: "approved",
          };
          pendingApprovals = [resolved];
          return jsonResponse(resolved);
        }
        if (
          url.endsWith("/api/v1/conversations") &&
          init?.method === "POST"
        ) {
          return jsonResponse(conversation, 201);
        }
        if (url.endsWith("/api/v1/tasks") && init?.method === "POST") {
          const payload = JSON.parse(String(init.body)) as {
            prompt: string;
          };
          const task = queuedTask(
            `task-${submittedTasks.length + 1}`,
            payload.prompt,
          );
          submittedTasks.push(task);
          return jsonResponse(task, 202);
        }
        const matchedTask = submittedTasks.find((item) =>
          url.endsWith(`/api/v1/tasks/${item.id}`),
        );
        if (matchedTask) {
          return jsonResponse(completedTask(matchedTask));
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads a project and waits for the first message", async () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "一个入口， 让企业知识与 Agent 协同工作。",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "主要导航" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "打开 API 测试台" }),
    ).toHaveAttribute("href", "/conversation");
    expect(
      screen.queryByRole("heading", { name: "连续对话测试" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("CAG 持续会话")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("link", { name: "打开 API 测试台" }),
    );
    expect(window.location.pathname).toBe("/conversation");
    expect(
      await screen.findByRole("option", {
        name: "Codex/ChatGPT Agent Gateway · cag",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });

  it("routes each feature domain to an independent page", async () => {
    render(<App />);

    fireEvent.click(
      screen.getByRole("link", { name: "企业知识" }),
    );
    expect(window.location.pathname).toBe("/knowledge");
    expect(
      await screen.findByRole("heading", { name: "企业知识", level: 1 }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Ollama 就绪")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "连续对话测试" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("link", { name: "能力治理" }),
    );
    expect(window.location.pathname).toBe("/capabilities");
    expect(
      await screen.findByRole("heading", { name: "能力治理", level: 1 }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Gateway 注册表")).toBeInTheDocument();
    expect(screen.getByText("NeurIPS RAG")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "企业知识与记忆" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "API 监控" }));
    expect(window.location.pathname).toBe("/audit");
    expect(
      await screen.findByRole("heading", {
        name: "API 调用监控",
        level: 1,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "全局审计事件流" }),
    ).toBeInTheDocument();
  });

  it("projects the global external API audit SSE into the monitor", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "API 监控" }));
    await screen.findByRole("heading", { name: "全局审计事件流" });

    const auditSource = MockEventSource.instances.find((source) =>
      source.url.includes("/api/v1/audit/events"),
    );
    expect(auditSource).toBeDefined();
    act(() => {
      auditSource?.emit("audit.event", {
        event_id: "audit-event-1",
        trace_id: "22222222-2222-4222-8222-222222222222",
        task_id: "22222222-2222-4222-8222-222222222222",
        sequence: 42,
        task_sequence: 3,
        conversation_id: null,
        type: "workspace.preparing",
        timestamp: "2026-07-27T00:00:03Z",
        trigger_source: "external_api",
        client_id: "erp-integration",
        client_request_id: "erp-request-001",
        project_id: project.id,
        project_code: project.code,
        data: {},
      });
    });

    expect(
      await screen.findAllByText("正在准备独立工作区"),
    ).toHaveLength(2);
    expect(screen.getByText(/erp-integration/)).toBeInTheDocument();
    expect(
      screen.getAllByText(
        (_, element) =>
          element?.textContent ===
          "后端已反馈 1 条 · 当前显示 1 条",
      ),
    ).toHaveLength(1);
  });

  it("creates a CAG conversation and opens one persistent SSE stream", async () => {
    render(<App />);
    await openConversationPage();
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });

    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "运行测试" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("运行测试")).toBeInTheDocument();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain(
      `/api/v1/conversations/${conversation.id}/events`,
    );
    const taskRequest = vi
      .mocked(fetch)
      .mock.calls.find(
        ([input, init]) =>
          String(input).endsWith("/api/v1/tasks") &&
          init?.method === "POST",
      );
    expect(JSON.parse(String(taskRequest?.[1]?.body))).toMatchObject({
      conversation_id: conversation.id,
      prompt: "运行测试",
    });
    const requestHeaders = new Headers(taskRequest?.[1]?.headers);
    expect(requestHeaders.get("X-CAG-Source")).toBe("test_console");
    expect(requestHeaders.get("X-CAG-Client-ID")).toBe("cag-web-test");
    expect(requestHeaders.get("X-Request-ID")).toBeTruthy();
    expect(requestHeaders.get("Idempotency-Key")).toBeTruthy();
  });

  it("keeps the SSE stream and reuses the conversation for another turn", async () => {
    render(<App />);
    await openConversationPage();
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });
    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "第一轮" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByText("第一轮");

    const source = MockEventSource.instances[0];
    source.emit("runtime.thread", {
      event_id: "event-1",
      conversation_id: conversation.id,
      task_id: "task-1",
      sequence: 4,
      task_sequence: 4,
      type: "runtime.thread",
      timestamp: "2026-07-27T00:00:01Z",
      data: { action: "started" },
    });
    source.emit("task.completed", {
      event_id: "event-2",
      conversation_id: conversation.id,
      task_id: "task-1",
      sequence: 8,
      task_sequence: 8,
      type: "task.completed",
      timestamp: "2026-07-27T00:00:02Z",
      data: {},
    });

    expect(await screen.findByText("建立持续上下文")).toBeInTheDocument();
    expect(await screen.findByText("已完成：第一轮")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByLabelText("发送消息")).toBeEnabled(),
    );

    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "第二轮" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    expect(await screen.findByText("第二轮")).toBeInTheDocument();

    const conversationRequests = vi
      .mocked(fetch)
      .mock.calls.filter(
        ([input, init]) =>
          String(input).endsWith("/api/v1/conversations") &&
          init?.method === "POST",
      );
    const taskRequests = vi
      .mocked(fetch)
      .mock.calls.filter(
        ([input, init]) =>
          String(input).endsWith("/api/v1/tasks") &&
          init?.method === "POST",
      );
    expect(conversationRequests).toHaveLength(1);
    expect(taskRequests).toHaveLength(2);
    expect(MockEventSource.instances).toHaveLength(1);
    expect(JSON.parse(String(taskRequests[1][1]?.body))).toMatchObject({
      conversation_id: conversation.id,
      prompt: "第二轮",
    });
  });

  it("projects live Agent deltas into the conversation independently of the event filter", async () => {
    render(<App />);
    await openConversationPage();
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });
    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "查询天气" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByText("查询天气");

    const source = MockEventSource.instances[0];
    act(() => {
      source.emit("task.started", {
        event_id: "event-live-1",
        conversation_id: conversation.id,
        task_id: "task-1",
        sequence: 1,
        task_sequence: 1,
        type: "task.started",
        timestamp: "2026-07-27T00:00:01Z",
        data: {},
      });
      source.emit("agent.message.started", {
        event_id: "event-live-2",
        conversation_id: conversation.id,
        task_id: "task-1",
        sequence: 2,
        task_sequence: 2,
        type: "agent.message.started",
        timestamp: "2026-07-27T00:00:02Z",
        data: { item_id: "message-1" },
      });
      source.emit("agent.message.delta", {
        event_id: "event-live-3",
        conversation_id: conversation.id,
        task_id: "task-1",
        sequence: 3,
        task_sequence: 3,
        type: "agent.message.delta",
        timestamp: "2026-07-27T00:00:03Z",
        data: {
          item_id: "message-1",
          delta: "正在查询东京天气",
          text: "正在查询东京天气",
        },
      });
    });

    expect(await screen.findByText("正在查询东京天气")).toBeInTheDocument();
    expect(screen.getByText("实时反馈")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "本轮执行中" }),
    ).toBeDisabled();
    expect(screen.queryByText("Agent 输出增量")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("反馈粒度"), {
      target: { value: "full" },
    });
    expect(await screen.findByText("Agent 输出增量")).toBeInTheDocument();
    expect(screen.getAllByText("正在查询东京天气")).toHaveLength(2);

    act(() => {
      source.emit("task.completed", {
        event_id: "event-live-4",
        conversation_id: conversation.id,
        task_id: "task-1",
        sequence: 4,
        task_sequence: 4,
        type: "task.completed",
        timestamp: "2026-07-27T00:00:04Z",
        data: {},
      });
    });
    expect(await screen.findByText("已完成：查询天气")).toBeInTheDocument();
    expect(screen.queryByText("实时反馈")).not.toBeInTheDocument();
  });

  it("limits visible feedback rows without dropping received events", async () => {
    render(<App />);
    await openConversationPage();
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });
    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "反馈数量测试" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByText("反馈数量测试");

    const source = MockEventSource.instances[0];
    act(() => {
      for (let sequence = 1; sequence <= 25; sequence += 1) {
        source.emit("task.started", {
          event_id: `event-count-${sequence}`,
          conversation_id: conversation.id,
          task_id: "task-1",
          sequence,
          task_sequence: sequence,
          type: "task.started",
          timestamp: "2026-07-27T00:00:01Z",
          data: {},
        });
      }
    });

    await waitFor(() => {
      expect(
        document.querySelectorAll(
          ".event-list > li:not(.event-pending)",
        ),
      ).toHaveLength(20);
    });
    expect(
      screen.getByText(
        (_, element) =>
          element?.textContent ===
          "后端已反馈 25 条 · 当前显示 20 条",
      ),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("画面条数"), {
      target: { value: "50" },
    });
    await waitFor(() => {
      expect(
        document.querySelectorAll(
          ".event-list > li:not(.event-pending)",
        ),
      ).toHaveLength(25);
    });
  });

  it("shows and resolves a pending command approval", async () => {
    pendingApprovals = [
      {
        id: "approval-1",
        task_id: "task-1",
        agent_run_id: "agent-1",
        request_type: "command",
        subject: "git log --oneline",
        risk_level: "medium",
        status: "pending",
        policy_decision: "approval_required",
        requested_at: "2026-07-27T00:00:01Z",
        resolution_note: null,
      },
    ];
    render(<App />);
    await openConversationPage();
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });
    fireEvent.change(screen.getByLabelText("发送消息"), {
      target: { value: "审批测试" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByText("审批测试");

    act(() => {
      MockEventSource.instances[0].emit("approval.pending", {
        event_id: "approval-event",
        conversation_id: conversation.id,
        task_id: "task-1",
        sequence: 9,
        task_sequence: 9,
        type: "approval.pending",
        timestamp: "2026-07-27T00:00:01Z",
        data: { approval_id: "approval-1" },
      });
    });

    expect(await screen.findByText("git log --oneline")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "批准" }));
    await waitFor(() =>
      expect(screen.queryByLabelText("待处理审批")).not.toBeInTheDocument(),
    );
  });
});
