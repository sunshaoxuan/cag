import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    project_id: project.id,
    project_code: project.code,
    conversation_id: conversation.id,
    prompt,
    runtime_profile: "general-engineering",
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

describe("Agent Gateway conversation page", () => {
  let submittedTasks: Task[];

  beforeEach(() => {
    MockEventSource.instances = [];
    submittedTasks = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/v1/projects")) {
          return jsonResponse([project]);
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
      await screen.findByRole("option", {
        name: "Codex/ChatGPT Agent Gateway · cag",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("CAG 持续会话")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });

  it("creates a CAG conversation and opens one persistent SSE stream", async () => {
    render(<App />);
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
  });

  it("keeps the SSE stream and reuses the conversation for another turn", async () => {
    render(<App />);
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
});
