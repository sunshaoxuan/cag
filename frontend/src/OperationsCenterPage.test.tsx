import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OperationsCenterPage from "./OperationsCenterPage";
import {
  approveOperationalIssue,
  getOperationalDashboard,
  getOperationalIssue,
  listOperationalIssues,
} from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    approveOperationalIssue: vi.fn(),
    getOperationalDashboard: vi.fn(),
    getOperationalIssue: vi.fn(),
    listOperationalIssues: vi.fn(),
    recordOperationalImplementation: vi.fn(),
    rejectOperationalIssue: vi.fn(),
    reopenOperationalIssue: vi.fn(),
  };
});

const issue = {
  id: "issue-1",
  project_id: "project-1",
  parent_issue_id: null,
  implementation_task_id: null,
  code: "OI-ABC123",
  fingerprint: "a".repeat(64),
  source_type: "knowledge_search",
  source_id: "search-1",
  title: "知识检索阻塞 Gateway",
  summary: "检索加载全部知识分块",
  severity: "high" as const,
  boundary: "cag_internal",
  boundary_confidence: 0.94,
  status: "waiting_approval",
  occurrence_count: 3,
  evidence: {},
  allowed_actions: ["plan", "review"],
  required_human_input: null,
  approval_status: "pending",
  approved_by: null,
  approval_note: null,
  approved_at: null,
  improvement_branch: null,
  evaluation_status: "not_started",
  resolution: null,
  closed_by: null,
  first_seen_at: "2026-07-31T00:00:00Z",
  last_seen_at: "2026-07-31T01:00:00Z",
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T01:00:00Z",
  closed_at: null,
  occurrences: [],
  artifacts: [
    {
      id: "artifact-plan",
      artifact_type: "plan" as const,
      revision: 1,
      content: {
        problem_statement: "将检索下推到 PostgreSQL 和 pgvector",
      },
      created_by: "ai-planner",
      created_at: "2026-07-31T01:01:00Z",
    },
    {
      id: "artifact-review",
      artifact_type: "review" as const,
      revision: 1,
      content: {
        summary: "增加大规模语料性能回归测试",
        recommendation: "approve",
      },
      created_by: "ai-independent-reviewer",
      created_at: "2026-07-31T01:02:00Z",
    },
  ],
  events: [
    {
      id: "event-1",
      sequence: 1,
      type: "issue.detected",
      data: {},
      created_at: "2026-07-31T01:00:00Z",
    },
  ],
};

describe("OperationsCenterPage", () => {
  beforeEach(() => {
    vi.mocked(getOperationalDashboard).mockResolvedValue({
      total: 1,
      by_status: { waiting_approval: 1 },
      by_severity: { high: 1 },
      by_boundary: { cag_internal: 1 },
    });
    vi.mocked(listOperationalIssues).mockResolvedValue([issue]);
    vi.mocked(getOperationalIssue).mockResolvedValue(issue);
    vi.mocked(approveOperationalIssue).mockResolvedValue({
      ...issue,
      status: "implementing",
      approval_status: "approved",
      improvement_branch: "codex/improvement/oi-abc123",
    });
  });

  it("shows the AI plan, independent review, timeline, and approval action", async () => {
    render(<OperationsCenterPage />);

    expect(
      await screen.findByRole("heading", {
        name: "自运维问题处理中心",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("知识检索阻塞 Gateway")).toBeInTheDocument();
    expect(screen.getByText("CAG 内部 · 94%")).toBeInTheDocument();
    expect(screen.getByText("AI 改进方案")).toBeInTheDocument();
    expect(screen.getByText("独立 AI Review")).toBeInTheDocument();
    expect(screen.getByText("issue.detected")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("填写审批意见或需要补充的改进点"), {
      target: { value: "批准隔离分支实施" },
    });
    fireEvent.click(screen.getByRole("button", { name: "批准进入改进" }));

    await waitFor(() => {
      expect(approveOperationalIssue).toHaveBeenCalledWith(
        issue.id,
        "批准隔离分支实施",
      );
    });
  });
});
