import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  approveOperationalIssue,
  getOperationalDashboard,
  getOperationalIssue,
  listOperationalIssueEvents,
  listOperationalIssues,
  OperationsAdminCredentials,
  OperationalDashboard,
  OperationalIssue,
  OperationalIssueEvent,
  OperationalIssueEventPage,
  recordOperationalImplementation,
  rejectOperationalIssue,
  reopenOperationalIssue,
} from "./api";

const ADMIN_IDENTITY_KEY = "cag.operations.admin.identity";
const ADMIN_TOKEN_KEY = "cag.operations.admin.token";

const STATUS_LABELS: Record<string, string> = {
  detected: "等待分诊",
  triaging: "AI 分诊中",
  waiting_approval: "等待审批",
  plan_revision_required: "方案待修订",
  waiting_external: "等待外部处理",
  implementing: "改进中",
  evaluating: "再评估中",
  closed: "已关闭",
  rejected: "已拒绝",
  validation_completed: "验证完成",
  out_of_scope: "已移交",
  triage_failed: "分诊失败",
};

const BOUNDARY_LABELS: Record<string, string> = {
  cag_internal: "CAG 内部",
  external_dependency: "外部依赖",
  credential_or_authorization: "凭据与授权",
  policy_or_scope: "职能边界",
};

const RESOLUTION_LABELS: Record<string, string> = {
  agent_self_improvement: "Agent 自增益实施",
  human_code_change: "人工代码补强",
  external_operator_action: "人工或外部操作",
  mixed: "Agent 与人工协作",
  out_of_scope: "移交职责方",
  undetermined: "实施方式待判断",
};

const REVIEW_LABELS: Record<string, string> = {
  approve: "建议批准",
  revise: "要求修订",
  reject: "建议拒绝",
};

const ARTIFACT_LABELS: Record<string, string> = {
  plan: "AI 改进方案",
  review: "独立 AI Review",
  implementation: "改进实施证据",
  evaluation: "再评估报告",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function contentSummary(content: Record<string, unknown>): string {
  const value =
    content.problem_statement ??
    content.summary ??
    content.root_cause ??
    content.recommendation;
  const text =
    typeof value === "string" ? value : JSON.stringify(content, null, 2);
  return text.length > 240 ? `${text.slice(0, 240)}…` : text;
}

export default function OperationsCenterPage() {
  const [dashboard, setDashboard] = useState<OperationalDashboard | null>(null);
  const [issues, setIssues] = useState<OperationalIssue[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<OperationalIssue | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [boundary, setBoundary] = useState("all");
  const [decisionNote, setDecisionNote] = useState("");
  const [implementationSummary, setImplementationSummary] = useState("");
  const [implementationBranch, setImplementationBranch] = useState("");
  const [implementationCommits, setImplementationCommits] = useState("");
  const [adminIdentity, setAdminIdentity] = useState(
    () => window.sessionStorage.getItem(ADMIN_IDENTITY_KEY) ?? "",
  );
  const [adminToken, setAdminToken] = useState(
    () => window.sessionStorage.getItem(ADMIN_TOKEN_KEY) ?? "",
  );
  const [busy, setBusy] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<OperationalIssueEvent[]>(
    [],
  );
  const [timelinePage, setTimelinePage] =
    useState<OperationalIssueEventPage | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const selectedIdRef = useRef<string | null>(null);
  const detailRequestRef = useRef(0);
  const refreshRequestRef = useRef(0);

  const loadIssue = useCallback(async (issueId: string) => {
    const requestId = ++detailRequestRef.current;
    setDetailLoading(true);
    try {
      const detail = await getOperationalIssue(issueId);
      if (
        requestId === detailRequestRef.current &&
        selectedIdRef.current === issueId
      ) {
        setSelected(detail);
        setError(null);
      }
    } catch (reason) {
      if (
        requestId === detailRequestRef.current &&
        selectedIdRef.current === issueId
      ) {
        setError(
          reason instanceof Error ? reason.message : "问题详情读取失败",
        );
      }
    } finally {
      if (requestId === detailRequestRef.current) {
        setDetailLoading(false);
      }
    }
  }, []);

  const refresh = useCallback(async (preserveId?: string) => {
    const requestId = ++refreshRequestRef.current;
    try {
      const [nextDashboard, nextIssues] = await Promise.all([
        getOperationalDashboard(),
        listOperationalIssues(),
      ]);
      if (requestId !== refreshRequestRef.current) return;
      setDashboard(nextDashboard);
      setIssues(nextIssues);
      const targetId =
        preserveId ?? selectedIdRef.current ?? nextIssues[0]?.id ?? null;
      if (targetId) {
        if (selectedIdRef.current !== targetId) {
          selectedIdRef.current = targetId;
          setSelectedId(targetId);
        }
        await loadIssue(targetId);
      } else {
        selectedIdRef.current = null;
        setSelectedId(null);
        setSelected(null);
      }
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "问题中心读取失败");
    }
  }, [loadIssue]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return issues.filter((issue) => {
      const matchesQuery =
        !normalized ||
        issue.code.toLocaleLowerCase().includes(normalized) ||
        issue.title.toLocaleLowerCase().includes(normalized) ||
        issue.summary.toLocaleLowerCase().includes(normalized);
      const matchesStatus = status === "all" || issue.status === status;
      const matchesBoundary =
        boundary === "all" || issue.boundary === boundary;
      return matchesQuery && matchesStatus && matchesBoundary;
    });
  }, [boundary, issues, query, status]);

  async function selectIssue(issueId: string) {
    selectedIdRef.current = issueId;
    setSelectedId(issueId);
    setSelected(null);
    setDecisionNote("");
    setImplementationSummary("");
    setImplementationBranch("");
    setImplementationCommits("");
    setActionError(null);
    setActionMessage(null);
    setTimelineEvents([]);
    setTimelinePage(null);
    await loadIssue(issueId);
  }

  async function decide(action: "approve" | "reject") {
    if (!selected) return;
    const issueId = selected.id;
    setBusy(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const credentials = getAdminCredentials();
      const updated =
        action === "approve"
          ? await approveOperationalIssue(
              issueId,
              decisionNote,
              credentials,
            )
          : await rejectOperationalIssue(
              issueId,
              decisionNote || "管理员拒绝本轮改进方案",
              credentials,
            );
      if (selectedIdRef.current === issueId) {
        setSelected(updated);
        setActionMessage(
          action === "approve" ? "审批已提交" : "拒绝意见已提交",
        );
      }
      setDecisionNote("");
      await refresh(selectedIdRef.current === issueId ? updated.id : undefined);
    } catch (reason) {
      setActionError(
        reason instanceof Error ? reason.message : "审批操作失败",
      );
    } finally {
      setBusy(false);
    }
  }

  async function recordImplementation() {
    if (!selected || !implementationSummary.trim()) return;
    const issueId = selected.id;
    setBusy(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const updated = await recordOperationalImplementation(
        issueId,
        {
          summary: implementationSummary.trim(),
          branch: implementationBranch.trim() || null,
          commits: implementationCommits
            .split(/[\s,]+/)
            .map((item) => item.trim())
            .filter(Boolean),
        },
        getAdminCredentials(),
      );
      if (selectedIdRef.current === issueId) {
        setSelected(updated);
        setActionMessage("改进证据已登记");
      }
      setImplementationSummary("");
      setImplementationBranch("");
      setImplementationCommits("");
      await refresh(selectedIdRef.current === issueId ? updated.id : undefined);
    } catch (reason) {
      setActionError(
        reason instanceof Error ? reason.message : "改进证据登记失败",
      );
    } finally {
      setBusy(false);
    }
  }

  async function reopen() {
    if (!selected) return;
    const issueId = selected.id;
    setBusy(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const updated = await reopenOperationalIssue(
        issueId,
        decisionNote || "管理员要求重新评估",
        getAdminCredentials(),
      );
      if (selectedIdRef.current === issueId) {
        setSelected(updated);
        setActionMessage("问题已重新提交，正在等待分诊");
      }
      setDecisionNote("");
      await refresh(selectedIdRef.current === issueId ? updated.id : undefined);
    } catch (reason) {
      setActionError(
        reason instanceof Error ? reason.message : "重新打开失败",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadTimeline(reset: boolean) {
    const issueId = selectedIdRef.current;
    if (!issueId || timelineLoading) return;
    setTimelineLoading(true);
    try {
      const page = await listOperationalIssueEvents(
        issueId,
        reset ? null : timelinePage?.next_before_sequence,
      );
      if (selectedIdRef.current !== issueId) return;
      setTimelinePage(page);
      setTimelineEvents((current) =>
        reset ? page.items : [...page.items, ...current],
      );
    } catch (reason) {
      if (selectedIdRef.current === issueId) {
        setActionError(
          reason instanceof Error ? reason.message : "问题时间线读取失败",
        );
      }
    } finally {
      if (selectedIdRef.current === issueId) {
        setTimelineLoading(false);
      }
    }
  }

  const activeCount = dashboard
    ? dashboard.total -
      (dashboard.by_status.closed ?? 0) -
      (dashboard.by_status.rejected ?? 0) -
      (dashboard.by_status.validation_completed ?? 0) -
      (dashboard.by_status.out_of_scope ?? 0)
    : 0;
  const decisionBrief = selected?.decision_brief ?? {};
  const recommendedChanges = decisionBrief.recommended_changes ?? [];
  const blockingFindings = decisionBrief.blocking_findings ?? [];
  const validationPlan = decisionBrief.validation_plan ?? [];

  function getAdminCredentials(): OperationsAdminCredentials {
    const identity = adminIdentity.trim();
    const token = adminToken.trim();
    if (identity.length < 2 || !token) {
      throw new Error("请先填写管理员身份和令牌");
    }
    return { identity, token };
  }

  function saveAdminCredentials() {
    try {
      const credentials = getAdminCredentials();
      window.sessionStorage.setItem(ADMIN_IDENTITY_KEY, credentials.identity);
      window.sessionStorage.setItem(ADMIN_TOKEN_KEY, credentials.token);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "管理员凭据无效");
    }
  }

  function clearAdminCredentials() {
    window.sessionStorage.removeItem(ADMIN_IDENTITY_KEY);
    window.sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setAdminIdentity("");
    setAdminToken("");
  }

  return (
    <>
      <section className="page-intro operations-intro">
        <div>
          <p className="eyebrow">SELF OPERATIONS · GOVERNED IMPROVEMENT</p>
          <h1>自运维问题处理中心</h1>
          <p>
            汇集运行失败，执行AI边界判断、改进规划、独立Review、管理员审批、
            隔离实施和再评估，完整保留每一次证据。
          </p>
        </div>
        <div className="page-metric">
          <span>处理中问题</span>
          <strong>{activeCount}</strong>
        </div>
      </section>

      <section className="operations-admin-access" aria-label="管理员授权">
        <div>
          <strong>管理员授权</strong>
          <span>审批和状态变更需要令牌，凭据只保存在当前浏览器会话。</span>
        </div>
        <label>
          <span>管理员身份</span>
          <input
            value={adminIdentity}
            onChange={(event) => setAdminIdentity(event.target.value)}
            placeholder="管理员身份"
            autoComplete="username"
          />
        </label>
        <label>
          <span>管理员令牌</span>
          <input
            type="password"
            value={adminToken}
            onChange={(event) => setAdminToken(event.target.value)}
            placeholder="管理员令牌"
            autoComplete="current-password"
          />
        </label>
        <button
          type="button"
          className="button button-outline"
          onClick={saveAdminCredentials}
        >
          保存本次会话
        </button>
        <button
          type="button"
          className="button button-ghost"
          onClick={clearAdminCredentials}
        >
          清除
        </button>
      </section>

      <section className="operations-dashboard" aria-label="问题中心总览">
        <article>
          <span>全部问题</span>
          <strong>{dashboard?.total ?? 0}</strong>
        </article>
        <article>
          <span>等待审批</span>
          <strong>{dashboard?.by_status.waiting_approval ?? 0}</strong>
        </article>
        <article>
          <span>方案待修订</span>
          <strong>{dashboard?.by_status.plan_revision_required ?? 0}</strong>
        </article>
        <article>
          <span>改进与评估</span>
          <strong>
            {(dashboard?.by_status.implementing ?? 0) +
              (dashboard?.by_status.evaluating ?? 0)}
          </strong>
        </article>
        <article>
          <span>严重问题</span>
          <strong>
            {(dashboard?.by_severity.critical ?? 0) +
              (dashboard?.by_severity.high ?? 0)}
          </strong>
        </article>
      </section>

      {error && <div className="operations-error" role="alert">{error}</div>}

      <section className="operations-workspace page-panel">
        <aside className="operations-list" aria-label="问题队列">
          <div className="operations-toolbar">
            <label>
              <span>检索</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="问题编号、标题或错误"
              />
            </label>
            <label>
              <span>状态</span>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="all">全部状态</option>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option value={value} key={value}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              <span>边界</span>
              <select
                value={boundary}
                onChange={(event) => setBoundary(event.target.value)}
              >
                <option value="all">全部边界</option>
                {Object.entries(BOUNDARY_LABELS).map(([value, label]) => (
                  <option value={value} key={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="operations-count">当前显示 {filtered.length} 项</p>
          <div className="operations-items">
            {filtered.map((issue) => (
              <button
                type="button"
                key={issue.id}
                className={`operations-item ${
                  selectedId === issue.id ? "is-selected" : ""
                }`}
                onClick={() => void selectIssue(issue.id)}
              >
                <span className={`severity severity-${issue.severity}`}>
                  {issue.severity.toUpperCase()}
                </span>
                <strong>{issue.code} · {issue.title}</strong>
                <small>
                  {STATUS_LABELS[issue.status] ?? issue.status}
                  <span aria-hidden="true"> · </span>
                  {issue.boundary
                    ? BOUNDARY_LABELS[issue.boundary] ?? issue.boundary
                    : "等待边界判断"}
                </small>
                <small>
                  {issue.resolution_mode
                    ? RESOLUTION_LABELS[issue.resolution_mode] ??
                      issue.resolution_mode
                    : "实施方式待判断"}
                </small>
                <small>
                  发生 {issue.occurrence_count} 次
                  <span aria-hidden="true"> · </span>
                  {formatDate(issue.last_seen_at)}
                </small>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="operations-empty">当前筛选条件下没有问题。</p>
            )}
          </div>
        </aside>

        <section className="operations-detail" aria-label="问题详情">
          {!selected && detailLoading && (
            <div className="operations-empty">正在读取问题详情…</div>
          )}
          {!selected && !detailLoading && (
            <div className="operations-empty">
              选择一个问题查看AI判断、审批意见和完整处理时间线。
            </div>
          )}
          {selected && (
            <>
              <header className="operations-detail-header">
                <div>
                  <p>{selected.code}</p>
                  <h2>{selected.title}</h2>
                  <span>{selected.summary}</span>
                </div>
                <span className={`issue-status status-${selected.status}`}>
                  {STATUS_LABELS[selected.status] ?? selected.status}
                </span>
              </header>

              <dl className="operations-facts">
                <div>
                  <dt>责任边界</dt>
                  <dd>
                    {selected.boundary
                      ? BOUNDARY_LABELS[selected.boundary] ?? selected.boundary
                      : "AI 判断中"}
                    {selected.boundary_confidence !== null &&
                      ` · ${(selected.boundary_confidence * 100).toFixed(0)}%`}
                  </dd>
                </div>
                <div>
                  <dt>审批状态</dt>
                  <dd>{selected.approval_status}</dd>
                </div>
                <div>
                  <dt>实施方式</dt>
                  <dd>
                    {selected.resolution_mode
                      ? RESOLUTION_LABELS[selected.resolution_mode] ??
                        selected.resolution_mode
                      : "AI 判断中"}
                    {selected.resolution_mode_confidence !== null &&
                      ` · ${(selected.resolution_mode_confidence * 100).toFixed(0)}%`}
                  </dd>
                </div>
                <div>
                  <dt>独立 Review</dt>
                  <dd>
                    {selected.review_recommendation
                      ? REVIEW_LABELS[selected.review_recommendation] ??
                        selected.review_recommendation
                      : "尚未完成"}
                    {selected.blocking_finding_count > 0 &&
                      ` · ${selected.blocking_finding_count} 个阻断项`}
                  </dd>
                </div>
                <div>
                  <dt>改进分支</dt>
                  <dd>{selected.improvement_branch ?? "尚未创建"}</dd>
                </div>
                <div>
                  <dt>再评估</dt>
                  <dd>{selected.evaluation_status}</dd>
                </div>
              </dl>

              {actionError && (
                <div className="operations-action-feedback is-error" role="alert">
                  {actionError}
                </div>
              )}
              {actionMessage && (
                <div className="operations-action-feedback is-success" role="status">
                  {actionMessage}
                </div>
              )}

              <section className="operations-decision-brief">
                <div className="operations-section-heading">
                  <div>
                    <p>DECISION BRIEF</p>
                    <h3>审核决策摘要</h3>
                  </div>
                  <span
                    className={`review-recommendation review-${
                      selected.review_recommendation ?? "pending"
                    }`}
                  >
                    {selected.review_recommendation
                      ? REVIEW_LABELS[selected.review_recommendation]
                      : "等待 Review"}
                  </span>
                </div>

                <div className="operations-brief-grid">
                  <article>
                    <span>问题归纳</span>
                    <p>{decisionBrief.problem_summary ?? selected.summary}</p>
                  </article>
                  <article>
                    <span>业务与运行影响</span>
                    <p>
                      {decisionBrief.impact_summary ??
                        "AI 分析完成后生成影响摘要。"}
                    </p>
                  </article>
                  <article>
                    <span>根因判断</span>
                    <p>
                      {decisionBrief.root_cause_summary ??
                        "当前证据尚未形成根因结论。"}
                    </p>
                  </article>
                  <article>
                    <span>改进目标</span>
                    <p>
                      {decisionBrief.improvement_goal ??
                        "AI 分析完成后生成改进目标。"}
                    </p>
                  </article>
                </div>

                <div className="operations-resolution-callout">
                  <strong>
                    {selected.resolution_mode
                      ? RESOLUTION_LABELS[selected.resolution_mode]
                      : "实施方式待判断"}
                  </strong>
                  <p>
                    {selected.resolution_mode_reason ??
                      "需要更多结构化证据才能选择实施方式。"}
                  </p>
                </div>

                {recommendedChanges.length > 0 && (
                  <div className="operations-improvement-plan">
                    <h4>建议改进点</h4>
                    <ol>
                      {recommendedChanges.map((change, index) => (
                        <li key={`${change.area ?? "change"}-${index}`}>
                          <strong>{change.area ?? `改进项 ${index + 1}`}</strong>
                          <p>{change.change ?? "待补充具体变更"}</p>
                          {change.reason && <small>{change.reason}</small>}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {blockingFindings.length > 0 && (
                  <div className="operations-blockers">
                    <h4>审批阻断项</h4>
                    <ol>
                      {blockingFindings.map((finding, index) => (
                        <li key={`${finding.code ?? "blocker"}-${index}`}>
                          <strong>
                            {finding.code ?? `B${index + 1}`} ·{" "}
                            {finding.title ?? "待修订项"}
                          </strong>
                          <p>{finding.finding ?? "Review 要求补充证据。"}</p>
                          {finding.required_change && (
                            <small>要求：{finding.required_change}</small>
                          )}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {validationPlan.length > 0 && (
                  <div className="operations-validation-plan">
                    <h4>验收计划</h4>
                    <ul>
                      {validationPlan.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>

              {selected.required_human_input && (
                <div className="operations-human-input">
                  <strong>需要管理员处理</strong>
                  <p>{selected.required_human_input}</p>
                </div>
              )}

              {selected.status === "plan_revision_required" &&
                selected.allowed_actions.includes("reopen") && (
                <section className="operations-approval operations-revision">
                  <h3>方案需要修订</h3>
                  <p>
                    当前 Review 存在阻断项，审批入口保持关闭。补充证据后可重新执行
                    AI 规划和独立 Review。
                  </p>
                  <textarea
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                    placeholder="填写重新规划原因或需要补充的重点"
                  />
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={() => void reopen()}
                    disabled={busy}
                  >
                    重新规划与 Review
                  </button>
                </section>
              )}

              {selected.status === "waiting_approval" &&
                (selected.allowed_actions.includes("approve") ||
                  selected.allowed_actions.includes("reject")) && (
                  <section className="operations-approval">
                    <h3>改进审批</h3>
                    <textarea
                      value={decisionNote}
                      onChange={(event) => setDecisionNote(event.target.value)}
                      placeholder="填写审批意见或需要补充的改进点"
                    />
                    <div>
                      {selected.allowed_actions.includes("approve") && (
                        <button
                          type="button"
                          className="button button-primary"
                          onClick={() => void decide("approve")}
                          disabled={busy}
                        >
                          批准进入改进
                        </button>
                      )}
                      {selected.allowed_actions.includes("reject") && (
                        <button
                          type="button"
                          className="button button-outline"
                          onClick={() => void decide("reject")}
                          disabled={busy}
                        >
                          拒绝本轮方案
                        </button>
                      )}
                    </div>
                  </section>
                )}

              {selected.allowed_actions.includes(
                "record_manual_implementation",
              ) && (
                <section className="operations-approval">
                  <h3>登记人工或批量改进</h3>
                  <textarea
                    value={implementationSummary}
                    onChange={(event) =>
                      setImplementationSummary(event.target.value)
                    }
                    placeholder="说明完成的凭据、外部系统或批量改进"
                  />
                  <div className="operations-implementation-fields">
                    <input
                      value={implementationBranch}
                      onChange={(event) =>
                        setImplementationBranch(event.target.value)
                      }
                      placeholder="关联分支，可留空"
                    />
                    <input
                      value={implementationCommits}
                      onChange={(event) =>
                        setImplementationCommits(event.target.value)
                      }
                      placeholder="提交哈希，以空格或逗号分隔"
                    />
                  </div>
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={() => void recordImplementation()}
                    disabled={busy || !implementationSummary.trim()}
                  >
                    进入独立再评估
                  </button>
                </section>
              )}

              {selected.status !== "plan_revision_required" &&
                selected.allowed_actions.includes("reopen") && (
                <section className="operations-approval">
                  <h3>重新处理</h3>
                  <textarea
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                    placeholder="填写重新打开原因"
                  />
                  <button
                    type="button"
                    className="button button-outline"
                    onClick={() => void reopen()}
                    disabled={busy}
                  >
                    重新提交问题处理
                  </button>
                </section>
              )}

              <section className="operations-artifacts">
                <h3>完整证据与执行日志</h3>
                <p className="operations-evidence-intro">
                  上方决策摘要用于审核。以下原始材料保留审计追踪，按需展开查看。
                </p>
                {(selected.artifacts ?? []).map((artifact) => (
                  <details key={artifact.id}>
                    <summary>
                      {ARTIFACT_LABELS[artifact.artifact_type] ??
                        artifact.artifact_type}
                      <span>
                        v{artifact.revision} · {artifact.created_by}
                      </span>
                    </summary>
                    <p>{contentSummary(artifact.content)}</p>
                    <pre>{JSON.stringify(artifact.content, null, 2)}</pre>
                  </details>
                ))}
              </section>

              <details
                className="operations-timeline"
                onToggle={(event) => {
                  if (
                    event.currentTarget.open &&
                    timelineEvents.length === 0 &&
                    !timelineLoading
                  ) {
                    void loadTimeline(true);
                  }
                }}
              >
                <summary>
                  完整处理时间线
                  <span>{selected.event_count} 条事件</span>
                </summary>
                {timelineLoading && timelineEvents.length === 0 && (
                  <p className="operations-timeline-state">正在读取最新事件…</p>
                )}
                <ol>
                  {[...timelineEvents].reverse().map((event) => (
                    <li key={event.id}>
                      <span>{event.sequence}</span>
                      <div>
                        <strong>{event.type}</strong>
                        <small>{formatDate(event.created_at)}</small>
                        <p>{JSON.stringify(event.data)}</p>
                      </div>
                    </li>
                  ))}
                </ol>
                {timelinePage?.has_more && (
                  <button
                    type="button"
                    className="button button-outline operations-timeline-more"
                    onClick={() => void loadTimeline(false)}
                    disabled={timelineLoading}
                  >
                    {timelineLoading ? "正在加载…" : "加载更早事件"}
                  </button>
                )}
              </details>
            </>
          )}
        </section>
      </section>
    </>
  );
}
