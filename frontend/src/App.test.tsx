import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Task } from "./api";

const project = {
  id: "6ee71a6a-f30a-4a2d-a281-309c7511b832",
  code: "cag",
  name: "Codex/ChatGPT Agent Gateway",
  default_branch: "master",
  default_runtime_profile: "general-engineering",
};

const queuedTask: Task = {
  id: "task-1234",
  project_id: project.id,
  project_code: project.code,
  conversation_id: null,
  prompt: "运行测试",
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

const completedTask: Task = {
  ...queuedTask,
  status: "completed",
  workspace_id: `${project.id}/task-1234`,
  workspace_commit: "1234567890abcdef1234567890abcdef12345678",
  started_at: "2026-07-27T00:00:01Z",
  completed_at: "2026-07-27T00:00:02Z",
  final_report: {
    status: "completed",
    summary: "验证完成。",
    root_cause: null,
    changes: [],
    validation: [{ command: "pytest", status: "passed" }],
    approvals: [],
    warnings: ["Fake Runtime"],
    next_actions: [],
  },
};

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

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response;
}

describe("Agent Gateway task page", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/v1/projects")) {
          return jsonResponse([project]);
        }
        if (url.endsWith("/api/v1/tasks") && init?.method === "POST") {
          return jsonResponse(queuedTask);
        }
        if (url.endsWith(`/api/v1/tasks/${queuedTask.id}`)) {
          return jsonResponse(completedTask);
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the configured project and keeps submit disabled for an empty prompt", async () => {
    render(<App />);

    expect(
      await screen.findByRole("option", {
        name: "Codex/ChatGPT Agent Gateway · cag",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("本地 Codex 订阅架构")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "开始执行" }),
    ).toBeDisabled();
  });

  it("submits a prompt and opens the event stream", async () => {
    render(<App />);
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });

    fireEvent.change(screen.getByLabelText("任务 Prompt"), {
      target: { value: "运行测试" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始执行" }));

    expect(await screen.findByText("排队中")).toBeInTheDocument();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain(
      `/api/v1/tasks/${queuedTask.id}/events`,
    );
  });

  it("renders ordered events and the final report", async () => {
    render(<App />);
    await screen.findByRole("option", {
      name: "Codex/ChatGPT Agent Gateway · cag",
    });
    fireEvent.change(screen.getByLabelText("任务 Prompt"), {
      target: { value: "运行测试" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始执行" }));
    await screen.findByText("排队中");

    const source = MockEventSource.instances[0];
    source.emit("workspace.ready", {
      event_id: "event-1",
      task_id: queuedTask.id,
      sequence: 4,
      type: "workspace.ready",
      timestamp: "2026-07-27T00:00:01Z",
      data: {
        branch: "master",
        commit_sha: "1234567890abcdef",
      },
    });
    source.emit("task.completed", {
      event_id: "event-2",
      task_id: queuedTask.id,
      sequence: 8,
      type: "task.completed",
      timestamp: "2026-07-27T00:00:02Z",
      data: {},
    });

    expect(await screen.findByText("工作区已就绪")).toBeInTheDocument();
    expect(await screen.findByText("验证完成。")).toBeInTheDocument();
    expect(screen.getByText("pytest")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("已完成")).toBeInTheDocument();
    });
  });
});
