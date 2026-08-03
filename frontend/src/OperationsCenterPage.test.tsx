import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OperationsCenterPage from "./OperationsCenterPage";
import {
  approveOperationalIssue,
  getOperationalDashboard,
  getOperationalIssue,
  listOperationalIssueEvents,
  listOperationalIssues,
  rejectOperationalIssue,
  reopenOperationalIssue,
} from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    approveOperationalIssue: vi.fn(),
    getOperationalDashboard: vi.fn(),
    getOperationalIssue: vi.fn(),
    listOperationalIssueEvents: vi.fn(),
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
  resolution_mode: "agent_self_improvement" as const,
  resolution_mode_confidence: 0.91,
  resolution_mode_reason: "问题位于 CAG 内部，可由受控 Agent 改进流程处理。",
  decision_brief: {
    administrator_language: "zh-CN" as const,
    problem_summary: "知识检索会在请求线程中加载全部知识分块。",
    impact_summary: "大规模知识源会导致查询超时。",
    root_cause_summary: "查询缺少数据库侧候选召回。",
    improvement_goal: "将候选召回下推到 PostgreSQL 和 pgvector。",
    recommended_changes: [
      {
        area: "知识检索",
        change: "增加数据库侧混合召回",
        reason: "缩小进入重排的候选集合",
      },
    ],
    validation_plan: ["验证精确短语和语义查询", "验证大规模知识源延迟"],
    blocking_findings: [],
    review_summary: "方案具备实施和回滚路径。",
    review_recommendation: "approve" as const,
    approval_ready: true,
  },
  review_recommendation: "approve" as const,
  blocking_finding_count: 0,
  status: "waiting_approval",
  occurrence_count: 3,
  evidence: {},
  allowed_actions: ["approve", "reject"],
  planned_actions: ["plan", "review"],
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
  event_count: 1,
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
};

describe("OperationsCenterPage", () => {
  beforeEach(() => {
    vi.mocked(getOperationalDashboard).mockResolvedValue({
      total: 1,
      by_status: { waiting_approval: 1 },
      by_severity: { high: 1 },
      by_boundary: { cag_internal: 1 },
      by_resolution_mode: { agent_self_improvement: 1 },
    });
    vi.mocked(listOperationalIssues).mockResolvedValue([issue]);
    vi.mocked(getOperationalIssue).mockResolvedValue(issue);
    vi.mocked(listOperationalIssueEvents).mockResolvedValue({
      items: [
        {
          id: "event-1",
          sequence: 1,
          type: "issue.detected",
          data: {},
          created_at: "2026-07-31T01:00:00Z",
        },
      ],
      total: 1,
      has_more: false,
      next_before_sequence: null,
    });
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
    expect(screen.getByText("Agent 自增益实施 · 91%")).toBeInTheDocument();
    expect(screen.getByText("审核决策摘要")).toBeInTheDocument();
    expect(screen.getByText("建议改进点")).toBeInTheDocument();
    expect(screen.getByText("增加数据库侧混合召回")).toBeInTheDocument();
    expect(screen.getByText("AI 改进方案")).toBeInTheDocument();
    expect(screen.getByText("独立 AI Review")).toBeInTheDocument();
    const timeline = screen
      .getByText("完整处理时间线")
      .closest("details");
    expect(timeline).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("完整处理时间线"));
    expect(timeline).toHaveAttribute("open");
    expect(await screen.findByText("issue.detected")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("填写审批意见，或说明禁止修改并结束的原因"),
      {
        target: { value: "批准隔离分支实施" },
      },
    );
    fireEvent.change(screen.getByPlaceholderText("管理员身份"), {
      target: { value: "security-admin" },
    });
    fireEvent.change(screen.getByPlaceholderText("管理员令牌"), {
      target: { value: "session-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "批准 Agent 自增益" }));

    await waitFor(() => {
      expect(approveOperationalIssue).toHaveBeenCalledWith(
        issue.id,
        "批准隔离分支实施",
        {
          identity: "security-admin",
          token: "session-secret",
        },
      );
    });
  });

  it("keeps administrator decisions visible for a repeated revision issue", async () => {
    const revisionIssue = {
      ...issue,
      id: "issue-revision",
      code: "OI-REVISION",
      title: "重复失败的问题",
      status: "plan_revision_required",
      occurrence_count: 100,
      approval_status: "revision_required",
      review_recommendation: "revise" as const,
      blocking_finding_count: 2,
      allowed_actions: ["reopen", "reject"],
      decision_brief: {
        ...issue.decision_brief,
        approval_ready: false,
        review_recommendation: "revise" as const,
        blocking_findings: [
          {
            code: "B1",
            title: "需要修订",
            finding: "方案证据不足。",
            required_change: "补充验证证据。",
          },
        ],
      },
    };
    vi.mocked(listOperationalIssues).mockResolvedValue([revisionIssue]);
    vi.mocked(getOperationalIssue).mockResolvedValue(revisionIssue);
    vi.mocked(rejectOperationalIssue).mockResolvedValue({
      ...revisionIssue,
      status: "rejected",
      approval_status: "rejected",
      allowed_actions: ["reopen"],
    });

    render(<OperationsCenterPage />);

    expect(
      await screen.findByRole("heading", { name: "管理员决策" }),
    ).toBeInTheDocument();
    expect(screen.getByText("已发生 100 次")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "要求修订并重新 Review" }),
    ).toBeInTheDocument();
    fireEvent.change(
      screen.getByPlaceholderText("填写修订重点，或说明禁止修改并结束的原因"),
      { target: { value: "当前风险不可接受，禁止本轮修改" } },
    );
    fireEvent.change(screen.getByPlaceholderText("管理员身份"), {
      target: { value: "operations-admin" },
    });
    fireEvent.change(screen.getByPlaceholderText("管理员令牌"), {
      target: { value: "session-secret" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "不允许修改并结束" }),
    );

    await waitFor(() => {
      expect(rejectOperationalIssue).toHaveBeenCalledWith(
        revisionIssue.id,
        "当前风险不可接受，禁止本轮修改",
        {
          identity: "operations-admin",
          token: "session-secret",
        },
      );
    });
  });

  it("reopens a rejected issue and shows an inline authentication error", async () => {
    const rejectedIssue = {
      ...issue,
      id: "issue-rejected",
      code: "OI-REJECTED",
      title: "发布验证记录",
      status: "rejected",
      approval_status: "rejected",
      allowed_actions: ["reopen"],
      review_recommendation: null,
      decision_brief: {},
    };
    vi.mocked(listOperationalIssues).mockResolvedValue([rejectedIssue]);
    vi.mocked(getOperationalIssue).mockResolvedValue(rejectedIssue);
    vi.mocked(reopenOperationalIssue).mockRejectedValue(
      new Error("Valid operations administrator credentials are required"),
    );

    render(<OperationsCenterPage />);

    expect(
      await screen.findByRole("heading", { name: "发布验证记录" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("管理员身份"), {
      target: { value: "operations-admin" },
    });
    fireEvent.change(screen.getByPlaceholderText("管理员令牌"), {
      target: { value: "expired-token" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "重新提交问题处理" }),
    );

    const inlineError = await screen.findByText(
      "Valid operations administrator credentials are required",
    );
    expect(inlineError).toHaveAttribute("role", "alert");
    expect(reopenOperationalIssue).toHaveBeenCalledWith(
      rejectedIssue.id,
      "管理员要求重新评估",
      {
        identity: "operations-admin",
        token: "expired-token",
      },
    );
  });

  it("keeps the latest selection when an older detail request finishes later", async () => {
    const secondIssue = {
      ...issue,
      id: "issue-2",
      code: "OI-SECOND",
      title: "第二个问题",
    };
    let resolveFirst: ((value: typeof issue) => void) | undefined;
    const delayedFirst = new Promise<typeof issue>((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(listOperationalIssues).mockResolvedValue([issue, secondIssue]);
    vi.mocked(getOperationalIssue).mockImplementation((issueId) =>
      issueId === issue.id ? delayedFirst : Promise.resolve(secondIssue),
    );

    render(<OperationsCenterPage />);

    const secondButton = await screen.findByRole("button", {
      name: /OI-SECOND/,
    });
    fireEvent.click(secondButton);
    expect(
      await screen.findByRole("heading", { name: "第二个问题" }),
    ).toBeInTheDocument();

    await act(async () => {
      resolveFirst?.(issue);
      await delayedFirst;
    });
    expect(
      screen.getByRole("heading", { name: "第二个问题" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "知识检索阻塞 Gateway" }),
    ).not.toBeInTheDocument();
  });
});
