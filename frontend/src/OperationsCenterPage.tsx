import { useCallback, useEffect, useMemo, useState } from "react";

import {
  approveOperationalIssue,
  getOperationalDashboard,
  getOperationalIssue,
  listOperationalIssues,
  OperationalDashboard,
  OperationalIssue,
  recordOperationalImplementation,
  rejectOperationalIssue,
  reopenOperationalIssue,
} from "./api";


const STATUS_LABELS: Record<string, string> = {
  detected: "等待分诊",
  triaging: "AI 分诊中",
  waiting_approval: "等待审批",
  waiting_external: "等待外部处理",
  implementing: "改进中",
  evaluating: "再评估中",
  closed: "已关闭",
  rejected: "已拒绝",
  out_of_scope: "已移交",
  triage_failed: "分诊失败",
};

const BOUNDARY_LABELS: Record<string, string> = {
  cag_internal: "CAG 内部",
  external_dependency: "外部依赖",
  credential_or_authorization: "凭据与授权",
  policy_or_scope: "职能边界",
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
  return typeof value === "string" ? value : JSON.stringify(content, null, 2);
}

export default function OperationsCenterPage() {
  const [dashboard, setDashboard] = useState<OperationalDashboard | null>(null);
  const [issues, setIssues] = useState<OperationalIssue[]>([]);
  const [selected, setSelected] = useState<OperationalIssue | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [boundary, setBoundary] = useState("all");
  const [decisionNote, setDecisionNote] = useState("");
  const [implementationSummary, setImplementationSummary] = useState("");
  const [implementationBranch, setImplementationBranch] = useState("");
  const [implementationCommits, setImplementationCommits] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (preserveId?: string) => {
    try {
      const [nextDashboard, nextIssues] = await Promise.all([
        getOperationalDashboard(),
        listOperationalIssues(),
      ]);
      setDashboard(nextDashboard);
      setIssues(nextIssues);
      const targetId = preserveId ?? selected?.id ?? nextIssues[0]?.id;
      if (targetId) {
        setSelected(await getOperationalIssue(targetId));
      } else {
        setSelected(null);
      }
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "问题中心读取失败");
    }
  }, [selected?.id]);

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
    setBusy(true);
    try {
      setSelected(await getOperationalIssue(issueId));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "问题详情读取失败");
    } finally {
      setBusy(false);
    }
  }

  async function decide(action: "approve" | "reject") {
    if (!selected) return;
    setBusy(true);
    try {
      const updated =
        action === "approve"
          ? await approveOperationalIssue(selected.id, decisionNote)
          : await rejectOperationalIssue(
              selected.id,
              decisionNote || "管理员拒绝本轮改进方案",
            );
      setSelected(updated);
      setDecisionNote("");
      await refresh(updated.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "审批操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function recordImplementation() {
    if (!selected || !implementationSummary.trim()) return;
    setBusy(true);
    try {
      const updated = await recordOperationalImplementation(selected.id, {
        summary: implementationSummary.trim(),
        branch: implementationBranch.trim() || null,
        commits: implementationCommits
          .split(/[\s,]+/)
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setSelected(updated);
      setImplementationSummary("");
      setImplementationBranch("");
      setImplementationCommits("");
      await refresh(updated.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "改进证据登记失败");
    } finally {
      setBusy(false);
    }
  }

  async function reopen() {
    if (!selected) return;
    setBusy(true);
    try {
      const updated = await reopenOperationalIssue(
        selected.id,
        decisionNote || "管理员要求重新评估",
      );
      setSelected(updated);
      setDecisionNote("");
      await refresh(updated.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "重新打开失败");
    } finally {
      setBusy(false);
    }
  }

  const activeCount = dashboard
    ? dashboard.total -
      (dashboard.by_status.closed ?? 0) -
      (dashboard.by_status.rejected ?? 0) -
      (dashboard.by_status.out_of_scope ?? 0)
    : 0;

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
                  selected?.id === issue.id ? "is-selected" : ""
                }`}
                onClick={() => void selectIssue(issue.id)}
                disabled={busy}
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
          {!selected && (
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
                  <dt>改进分支</dt>
                  <dd>{selected.improvement_branch ?? "尚未创建"}</dd>
                </div>
                <div>
                  <dt>再评估</dt>
                  <dd>{selected.evaluation_status}</dd>
                </div>
              </dl>

              {selected.required_human_input && (
                <div className="operations-human-input">
                  <strong>需要管理员处理</strong>
                  <p>{selected.required_human_input}</p>
                </div>
              )}

              {selected.status === "waiting_approval" && (
                <section className="operations-approval">
                  <h3>改进审批</h3>
                  <textarea
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                    placeholder="填写审批意见或需要补充的改进点"
                  />
                  <div>
                    <button
                      type="button"
                      className="button button-primary"
                      onClick={() => void decide("approve")}
                      disabled={busy}
                    >
                      批准进入改进
                    </button>
                    <button
                      type="button"
                      className="button button-outline"
                      onClick={() => void decide("reject")}
                      disabled={busy}
                    >
                      拒绝本轮方案
                    </button>
                  </div>
                </section>
              )}

              {selected.status === "waiting_external" && (
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

              {["closed", "rejected", "out_of_scope", "triage_failed"].includes(
                selected.status,
              ) && (
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
                <h3>方案、Review 与评估证据</h3>
                {(selected.artifacts ?? []).map((artifact) => (
                  <details key={artifact.id} open={artifact.artifact_type === "plan"}>
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

              <section className="operations-timeline">
                <h3>完整处理时间线</h3>
                <ol>
                  {[...(selected.events ?? [])].reverse().map((event) => (
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
              </section>
            </>
          )}
        </section>
      </section>
    </>
  );
}
