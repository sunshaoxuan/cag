import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  Conversation,
  conversationEventsUrl,
  createKnowledgeSource,
  createConversation,
  createTask,
  getKnowledgeStatus,
  getTask,
  ingestKnowledgeSource,
  KnowledgeSource,
  KnowledgeStatus,
  CapabilityAsset,
  ApprovalRequest,
  StandardControl,
  listKnowledgeSources,
  listMemoryCandidates,
  MemoryCandidate,
  listProjects,
  Project,
  Task,
  TaskEvent,
  transitionMemoryCandidate,
  listCapabilities,
  listPromotions,
  listStandardControls,
  listTaskApprovals,
  resolveApproval,
} from "./api";
import "./styles.css";

const EVENT_TYPES = [
  "task.created",
  "task.started",
  "workspace.preparing",
  "workspace.ready",
  "harness.started",
  "harness.preflight.completed",
  "harness.synthesis.completed",
  "agent.run.queued",
  "agent.run.started",
  "agent.run.completed",
  "agent.run.failed",
  "harness.completed",
  "knowledge.retrieval.started",
  "knowledge.retrieval.completed",
  "knowledge.context.injected",
  "knowledge.retrieval.failed",
  "memory.extraction.started",
  "memory.candidate.created",
  "memory.extraction.completed",
  "memory.extraction.failed",
  "learning.capture.started",
  "learning.signal.recorded",
  "learning.candidate.proposed",
  "learning.capture.completed",
  "learning.capture.failed",
  "evaluation.started",
  "evaluation.completed",
  "promotion.shadow",
  "promotion.canary",
  "promotion.active",
  "promotion.rollback",
  "runtime.connected",
  "runtime.thread",
  "agent.message.started",
  "agent.message.delta",
  "agent.message",
  "agent.plan.delta",
  "agent.plan",
  "agent.reasoning.summary.delta",
  "skill.selected",
  "tool.called",
  "tool.completed",
  "command.requested",
  "command.started",
  "command.output",
  "command.output.delta",
  "command.completed",
  "file.read",
  "file.changed",
  "test.started",
  "test.completed",
  "approval.requested",
  "approval.pending",
  "approval.resolved",
  "task.completed",
  "task.failed",
  "task.cancelled",
] as const;

const EVENT_LABELS: Record<string, string> = {
  "task.created": "新一轮已创建",
  "task.started": "本轮已启动",
  "workspace.preparing": "正在准备独立工作区",
  "workspace.ready": "工作区已就绪",
  "harness.started": "Harness 已启动",
  "harness.preflight.completed": "Harness 预检完成",
  "harness.synthesis.completed": "调查证据已汇总",
  "agent.run.queued": "子 Agent 已排队",
  "agent.run.started": "子 Agent 已启动",
  "agent.run.completed": "子 Agent 已完成",
  "agent.run.failed": "子 Agent 运行失败",
  "harness.completed": "Harness 已完成",
  "runtime.connected": "本机 Codex 已连接",
  "runtime.thread": "Codex 会话已连接",
  "knowledge.retrieval.started": "正在检索企业知识",
  "knowledge.retrieval.completed": "企业知识检索完成",
  "knowledge.context.injected": "已注入批准知识",
  "knowledge.retrieval.failed": "企业知识检索失败",
  "memory.extraction.started": "正在提取记忆候选",
  "memory.candidate.created": "已生成记忆候选",
  "memory.extraction.completed": "记忆候选提取完成",
  "memory.extraction.failed": "记忆候选提取失败",
  "learning.capture.started": "正在分析本轮学习信号",
  "learning.signal.recorded": "学习信号已记录",
  "learning.candidate.proposed": "可复用能力候选已创建",
  "learning.capture.completed": "本轮学习分析完成",
  "learning.capture.failed": "本轮学习分析失败",
  "evaluation.started": "能力评测已启动",
  "evaluation.completed": "能力评测已完成",
  "promotion.shadow": "能力进入影子运行",
  "promotion.canary": "能力进入金丝雀运行",
  "promotion.active": "能力已在 Gateway 启用",
  "promotion.rollback": "能力已自动回滚",
  "approval.pending": "等待命令审批",
  "agent.plan": "Agent 已生成计划",
  "agent.plan.delta": "Agent 计划增量",
  "agent.message.started": "Agent 开始回复",
  "agent.message.delta": "Agent 输出增量",
  "agent.message": "Agent 消息",
  "agent.reasoning.summary.delta": "Agent 推理摘要",
  "command.output.delta": "命令输出增量",
  "test.completed": "验证已完成",
  "task.completed": "本轮已完成",
  "task.failed": "本轮执行失败",
  "task.cancelled": "本轮已取消",
};

const STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  preparing: "准备工作区",
  running: "执行中",
  waiting_approval: "等待审批",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

type ChatTurn = {
  taskId: string;
  prompt: string;
  status: string;
  answer: string | null;
  error: string | null;
};

type FeedbackLevel = "essential" | "standard" | "full";
type FeedbackLimit = 20 | 50 | 100 | "all";

const DELTA_EVENT_TYPES = new Set([
  "agent.message.delta",
  "agent.plan.delta",
  "agent.reasoning.summary.delta",
  "command.output.delta",
]);

const ESSENTIAL_EVENT_TYPES = new Set([
  "task.created",
  "task.started",
  "harness.started",
  "agent.run.started",
  "agent.run.completed",
  "harness.completed",
  "runtime.connected",
  "runtime.thread",
  "agent.message",
  "command.completed",
  "file.changed",
  "test.completed",
  "approval.requested",
  "approval.pending",
  "approval.resolved",
  "task.completed",
  "task.failed",
  "task.cancelled",
]);

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function summarizeEvent(event: TaskEvent): string {
  if (
    event.type === "agent.message" ||
    event.type === "agent.message.delta" ||
    event.type === "agent.plan.delta" ||
    event.type === "agent.reasoning.summary.delta" ||
    event.type === "command.output.delta"
  ) {
    if (event.type.endsWith(".delta")) {
      return String(event.data.delta ?? "");
    }
    return String(event.data.text ?? "");
  }
  if (event.type === "workspace.ready") {
    return `分支 ${String(event.data.branch ?? "")}，提交 ${String(
      event.data.commit_sha ?? "",
    ).slice(0, 8)}`;
  }
  if (event.type === "runtime.thread") {
    return event.data.action === "resumed" ? "恢复持续上下文" : "建立持续上下文";
  }
  if (event.type.startsWith("agent.run.")) {
    return `${String(event.data.role ?? "Agent")} · ${String(
      event.data.phase ?? event.type,
    )}`;
  }
  if (event.type.startsWith("harness.")) {
    return `${String(event.data.profile ?? "Harness")} · ${String(
      event.data.harness_run_id ?? "",
    ).slice(0, 8)}`;
  }
  if (event.type === "test.completed") {
    return `${String(event.data.command ?? "验证")}：${String(
      event.data.status ?? "",
    )}`;
  }
  return EVENT_LABELS[event.type] ?? event.type;
}

function isTerminal(status: string): boolean {
  return ["completed", "failed", "cancelled"].includes(status);
}

function includeFeedbackEvent(
  event: TaskEvent,
  feedbackLevel: FeedbackLevel,
): boolean {
  if (feedbackLevel === "full") return true;
  if (feedbackLevel === "essential") {
    return ESSENTIAL_EVENT_TYPES.has(event.type);
  }
  return !DELTA_EVENT_TYPES.has(event.type);
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [prompt, setPrompt] = useState("");
  const [task, setTask] = useState<Task | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [feedbackLevel, setFeedbackLevel] =
    useState<FeedbackLevel>("standard");
  const [feedbackLimit, setFeedbackLimit] = useState<FeedbackLimit>(20);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [knowledgeStatus, setKnowledgeStatus] =
    useState<KnowledgeStatus | null>(null);
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidate[]>([]);
  const [knowledgeRoot, setKnowledgeRoot] = useState("");
  const [knowledgeMode, setKnowledgeMode] = useState("assist");
  const [harnessProfile, setHarnessProfile] = useState("single");
  const [learningMode, setLearningMode] = useState("capture");
  const [capabilities, setCapabilities] = useState<CapabilityAsset[]>([]);
  const [standardControls, setStandardControls] = useState<StandardControl[]>([]);
  const [promotionCount, setPromotionCount] = useState(0);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let active = true;
    listProjects()
      .then((items) => {
        if (!active) return;
        setProjects(items);
        setProjectId(items[0]?.id ?? "");
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      })
      .finally(() => {
        if (active) setLoadingProjects(false);
      });
    return () => {
      active = false;
      sourceRef.current?.close();
    };
  }, []);

  function refreshKnowledge() {
    Promise.all([
      getKnowledgeStatus(),
      listKnowledgeSources(),
      listMemoryCandidates(),
    ])
      .then(([statusValue, sourcesValue, candidatesValue]) => {
        setKnowledgeStatus(statusValue);
        setKnowledgeSources(sourcesValue);
        setMemoryCandidates(candidatesValue);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    refreshKnowledge();
  }, []);

  function refreshGovernance() {
    Promise.all([
      listCapabilities("skills"),
      listCapabilities("tools"),
      listCapabilities("validators"),
      listCapabilities("harness-profiles"),
      listStandardControls(),
      listPromotions(),
    ])
      .then(([skills, tools, validators, profiles, controls, promotions]) => {
        setCapabilities([...skills, ...tools, ...validators, ...profiles]);
        setStandardControls(controls);
        setPromotionCount(promotions.length);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    refreshGovernance();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projectId, projects],
  );
  const visibleEvents = useMemo(() => {
    const filteredEvents = events.filter((event) =>
      includeFeedbackEvent(event, feedbackLevel),
    );
    if (feedbackLimit === "all") return filteredEvents;
    return filteredEvents.slice(-feedbackLimit);
  }, [events, feedbackLevel, feedbackLimit]);
  const busy = task !== null && !isTerminal(task.status);

  function completeTurn(taskId: string) {
    getTask(taskId)
      .then((completedTask) => {
        setTask(completedTask);
        setTurns((current) =>
          current.map((turn) =>
            turn.taskId === taskId
              ? {
                  ...turn,
                  status: completedTask.status,
                  answer: completedTask.final_report?.summary ?? null,
                  error: completedTask.error,
                }
              : turn,
          ),
        );
      })
      .catch((reason: Error) => setError(reason.message));
  }

  function reflectLiveEvent(event: TaskEvent) {
    let nextStatus: string | null = null;
    if (event.type === "task.created") {
      nextStatus = "queued";
    } else if (
      event.type === "task.started" ||
      event.type === "workspace.preparing"
    ) {
      nextStatus = "preparing";
    } else if (
      event.type === "approval.requested" ||
      event.type === "approval.pending"
    ) {
      nextStatus = "waiting_approval";
    } else if (event.type === "task.completed") {
      nextStatus = "completed";
    } else if (event.type === "task.failed") {
      nextStatus = "failed";
    } else if (event.type === "task.cancelled") {
      nextStatus = "cancelled";
    } else {
      nextStatus = "running";
    }

    let liveAnswer: string | null = null;
    if (event.type === "agent.message.delta") {
      liveAnswer = String(event.data.text ?? "");
    } else if (
      event.type === "agent.message" &&
      event.data.level !== "warning"
    ) {
      liveAnswer = String(event.data.text ?? "");
    }

    setTask((current) =>
      current?.id === event.task_id
        ? {
            ...current,
            status: nextStatus ?? current.status,
          }
        : current,
    );
    setTurns((current) =>
      current.map((turn) =>
        turn.taskId === event.task_id
          ? {
              ...turn,
              status: nextStatus ?? turn.status,
              answer: liveAnswer || turn.answer,
            }
          : turn,
      ),
    );
    if (
      event.type === "approval.pending" ||
      event.type === "approval.requested" ||
      event.type === "approval.resolved"
    ) {
      listTaskApprovals(event.task_id)
        .then(setApprovals)
        .catch((reason: Error) => setError(reason.message));
    }
  }

  function connectConversationEvents(activeConversation: Conversation) {
    sourceRef.current?.close();
    const source = new EventSource(
      conversationEventsUrl(activeConversation.id),
    );
    sourceRef.current = source;

    const handleEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as TaskEvent;
      setEvents((current) => {
        if (current.some((item) => item.event_id === event.event_id)) {
          return current;
        }
        return [...current, event].sort((a, b) => a.sequence - b.sequence);
      });
      reflectLiveEvent(event);

      if (
        event.type === "task.completed" ||
        event.type === "task.failed" ||
        event.type === "task.cancelled"
      ) {
        completeTurn(event.task_id);
      }
    };

    EVENT_TYPES.forEach((eventType) => {
      source.addEventListener(eventType, handleEvent as EventListener);
    });
    source.onerror = () => {
      setError("会话事件流正在重连");
    };
  }

  function resetConversation(nextProjectId: string) {
    sourceRef.current?.close();
    sourceRef.current = null;
    setProjectId(nextProjectId);
    setConversation(null);
    setTask(null);
    setTurns([]);
    setEvents([]);
    setApprovals([]);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedPrompt = prompt.trim();
    if (!projectId || !trimmedPrompt || submitting || busy) return;

    setSubmitting(true);
    setError(null);
    try {
      let activeConversation = conversation;
      if (activeConversation === null) {
        activeConversation = await createConversation(
          projectId,
          trimmedPrompt.slice(0, 80),
        );
        setConversation(activeConversation);
        connectConversationEvents(activeConversation);
      }
      const createdTask = await createTask(
        projectId,
        trimmedPrompt,
        activeConversation.id,
        knowledgeMode,
        harnessProfile,
        learningMode,
      );
      setTask(createdTask);
      setTurns((current) => [
        ...current,
        {
          taskId: createdTask.id,
          prompt: trimmedPrompt,
          status: createdTask.status,
          answer: null,
          error: null,
        },
      ]);
      setPrompt("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "消息提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleKnowledgeSourceCreate() {
    if (!projectId || !knowledgeRoot.trim()) return;
    setError(null);
    try {
      const source = await createKnowledgeSource(
        projectId,
        "项目知识库",
        knowledgeRoot.trim(),
        "product",
      );
      await ingestKnowledgeSource(source.id);
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "知识来源创建失败");
    }
  }

  async function handleCandidateAction(
    candidateId: string,
    action: "approve" | "reject" | "promote" | "deprecate",
  ) {
    try {
      await transitionMemoryCandidate(candidateId, action);
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "记忆操作失败");
    }
  }

  async function handleApprovalAction(
    approvalId: string,
    decision: "approve" | "deny",
  ) {
    try {
      await resolveApproval(approvalId, decision);
      if (task) {
        setApprovals(await listTaskApprovals(task.id));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "审批操作失败");
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Agent Gateway 首页">
          <span className="brand-mark" aria-hidden="true">AG</span>
          <span>Agent Gateway</span>
        </a>
        <nav className="site-nav" aria-label="主要导航">
          <a href="#conversation">连续对话</a>
          <a href="#knowledge">企业知识</a>
          <a href="#capabilities">能力治理</a>
        </nav>
        <div className="site-actions">
          <a className="button button-ghost" href="#knowledge">查看知识库</a>
          <a className="button button-primary" href="#conversation">开始任务</a>
        </div>
      </header>

      <header className="hero">
        <div className="hero-content" id="top">
          <p className="eyebrow">LOCAL CODEX · ENTERPRISE KNOWLEDGE · AGENT HARNESS</p>
          <h1>
            一个入口，
            <span>让企业知识与 Agent 协同工作。</span>
          </h1>
          <p className="hero-copy">
            从连续对话、知识检索到并行调查与独立验证，CAG 在同一条任务链中
            维护完整上下文、审批和事实事件。
          </p>
          <div className="hero-actions">
            <a className="button button-primary button-large" href="#conversation">
              立即开始
            </a>
            <a className="button button-outline button-large" href="#capabilities">
              查看治理能力
            </a>
          </div>
          <ul className="hero-proof" aria-label="运行能力">
            <li>订阅 Codex</li>
            <li>1024 维向量</li>
            <li>完整 SSE</li>
          </ul>
        </div>
        <div className="hero-visual" aria-label="CAG 一体化任务链">
          <div className="hero-status">
            <span className="runtime-dot" aria-hidden="true" />
            CAG 持续会话
          </div>
          <p>从目标到可验证结果</p>
          <div className="flow-nodes" aria-hidden="true">
            <span>知识</span>
            <span>Agent</span>
            <span>验证</span>
          </div>
          <div className="flow-core">
            <span>CAG</span>
            <strong>统一任务上下文</strong>
            <small>Conversation · Harness · Evidence</small>
          </div>
          <div className="flow-footer">
            <span>01 检索</span>
            <span>02 执行</span>
            <span>03 复核</span>
          </div>
        </div>
      </header>

      <section
        className="knowledge-console panel"
        id="knowledge"
        aria-label="企业知识治理"
      >
        <div className="section-heading">
          <div>
            <p className="section-index">KNOWLEDGE</p>
            <h2>企业知识与记忆</h2>
          </div>
          <span className={`status status-${knowledgeStatus?.ready ? "completed" : "failed"}`}>
            {knowledgeStatus?.ready ? "Ollama 就绪" : "知识服务未就绪"}
          </span>
        </div>
        <div className="knowledge-summary">
          <p>
            向量模型 {knowledgeStatus?.embedding_model ?? "未配置"}
            <span aria-hidden="true"> · </span>
            维数 {knowledgeStatus?.dimensions ?? "未知"}
          </p>
          <p>
            已登记 {knowledgeSources.length} 个来源
            <span aria-hidden="true"> · </span>
            待治理 {memoryCandidates.filter((item) => item.status === "proposed").length} 条
          </p>
        </div>
        <div className="knowledge-actions">
          <input
            aria-label="知识来源路径"
            value={knowledgeRoot}
            onChange={(event) => setKnowledgeRoot(event.target.value)}
            placeholder="输入已授权的本机仓库路径"
          />
          <button type="button" onClick={handleKnowledgeSourceCreate}>
            登记并索引
          </button>
        </div>
        <div className="knowledge-grid">
          <div>
            <h3>知识来源</h3>
            {knowledgeSources.length === 0 && <p>尚未登记知识来源</p>}
            {knowledgeSources.map((source) => (
              <article className="knowledge-item" key={source.id}>
                <strong>{source.name}</strong>
                <span>{source.scope} · {source.status}</span>
                <small>{source.source_commit?.slice(0, 8) ?? source.root_path}</small>
              </article>
            ))}
          </div>
          <div>
            <h3>记忆候选</h3>
            {memoryCandidates.length === 0 && <p>尚无记忆候选</p>}
            {memoryCandidates.slice(0, 5).map((candidate) => (
              <article className="knowledge-item" key={candidate.id}>
                <strong>{candidate.title}</strong>
                <span>{candidate.kind} · {candidate.scope} · {candidate.status}</span>
                <small>{candidate.content}</small>
                {candidate.status === "proposed" && (
                  <div className="candidate-actions">
                    <button type="button" onClick={() => handleCandidateAction(candidate.id, "approve")}>
                      批准
                    </button>
                    <button type="button" onClick={() => handleCandidateAction(candidate.id, "reject")}>
                      拒绝
                    </button>
                  </div>
                )}
                {candidate.status === "approved" && candidate.scope === "tenant" && (
                  <button type="button" onClick={() => handleCandidateAction(candidate.id, "promote")}>
                    提升为产品知识
                  </button>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        className="capability-console panel"
        id="capabilities"
        aria-label="自学习能力治理"
      >
        <div className="section-heading">
          <div>
            <p className="section-index">CAPABILITY</p>
            <h2>自学习与能力治理</h2>
          </div>
          <span className="status status-completed">
            Gateway 注册表
          </span>
        </div>
        <div className="knowledge-summary">
          <p>
            已登记 {capabilities.length} 项能力
            <span aria-hidden="true"> · </span>
            已启用 {capabilities.filter((item) => item.active).length} 项
          </p>
          <p>
            提升记录 {promotionCount} 条
            <span aria-hidden="true"> · </span>
            控制映射 {standardControls.length} 项
          </p>
        </div>
        <div className="capability-grid">
          <div>
            <h3>Skill 与 Tool 注册表</h3>
            {capabilities.slice(0, 10).map((asset) => (
              <article className="knowledge-item" key={asset.id}>
                <strong>{asset.code}</strong>
                <span>{asset.kind} · {asset.status} · v{asset.version}</span>
                <small>
                  影子 {asset.shadow_runs} 次 · 金丝雀 {asset.canary_runs} 次
                </small>
              </article>
            ))}
          </div>
          <div>
            <h3>标准控制矩阵</h3>
            {standardControls.map((control) => (
              <article className="knowledge-item" key={control.id}>
                <strong>{control.framework}</strong>
                <span>{control.code} · {control.implementation_status}</span>
                <small>{control.title}</small>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        className="workspace-grid conversation-grid"
        id="conversation"
      >
        <section className="conversation-panel panel">
          <div className="section-heading">
            <div>
              <p className="section-index">01</p>
              <h2>连续对话</h2>
            </div>
            <span>{conversation ? `会话 ${conversation.id.slice(0, 8)}` : "新会话"}</span>
          </div>

          <label htmlFor="project">项目</label>
          <select
            id="project"
            value={projectId}
            onChange={(event) => resetConversation(event.target.value)}
            disabled={loadingProjects || submitting || busy}
          >
            {loadingProjects && <option>正在加载项目</option>}
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name} · {project.code}
              </option>
            ))}
          </select>

          {selectedProject && (
            <p className="project-meta">
              默认分支 {selectedProject.default_branch}
              <span aria-hidden="true"> · </span>
              {selectedProject.default_runtime_profile}
            </p>
          )}

          <div className="chat-history" aria-live="polite">
            {turns.length === 0 && (
              <div className="empty-state chat-empty">
                <div className="empty-mark" aria-hidden="true">
                  AG
                </div>
                <h3>开始一段持续对话</h3>
                <p>后续消息会复用同一个 CAG Conversation 和 Codex thread。</p>
              </div>
            )}
            {turns.map((turn) => (
              <article className="chat-turn" key={turn.taskId}>
                <div className="message message-user">
                  <span>你</span>
                  <p>{turn.prompt}</p>
                </div>
                <div className="message message-agent">
                  <span>Codex</span>
                  {turn.answer && !isTerminal(turn.status) && (
                    <em className="message-live">实时反馈</em>
                  )}
                  {turn.answer && <p>{turn.answer}</p>}
                  {turn.error && <p className="message-error">{turn.error}</p>}
                  {!turn.answer && !turn.error && (
                    <p className="message-pending">
                      {STATUS_LABELS[turn.status] ?? "处理中"}
                    </p>
                  )}
                </div>
              </article>
            ))}
          </div>

          <form className="chat-composer" onSubmit={handleSubmit}>
            <label htmlFor="prompt">发送消息</label>
            <label className="knowledge-mode-control">
              <span>企业知识</span>
              <select
                value={knowledgeMode}
                onChange={(event) => setKnowledgeMode(event.target.value)}
                disabled={submitting || busy}
              >
                <option value="assist">辅助模式</option>
                <option value="required">必需模式</option>
                <option value="off">关闭</option>
              </select>
            </label>
            <div className="harness-controls">
              <label>
                <span>Agent Harness</span>
                <select
                  aria-label="Agent Harness"
                  value={harnessProfile}
                  onChange={(event) => setHarnessProfile(event.target.value)}
                  disabled={submitting || busy}
                >
                  <option value="single">单 Agent</option>
                  <option value="fast">快速 Harness</option>
                  <option value="balanced">平衡 Harness</option>
                  <option value="deep">深度 Harness</option>
                </select>
              </label>
              <label>
                <span>学习模式</span>
                <select
                  aria-label="学习模式"
                  value={learningMode}
                  onChange={(event) => setLearningMode(event.target.value)}
                  disabled={submitting || busy}
                >
                  <option value="off">关闭</option>
                  <option value="capture">记录候选</option>
                  <option value="evaluate">记录并评测</option>
                </select>
              </label>
            </div>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="描述目标，下一轮会继续使用当前上下文。"
              rows={4}
              disabled={submitting || busy}
            />
            <div className="composer-footer">
              <span>{prompt.trim().length.toLocaleString()} 字</span>
              <button
                type="submit"
                disabled={
                  !projectId || !prompt.trim() || submitting || busy
                }
              >
                {submitting ? "正在发送" : busy ? "本轮执行中" : "发送"}
              </button>
            </div>
          </form>
          {error && <p className="error-banner">{error}</p>}
        </section>

        <section className="execution-panel panel" aria-live="polite">
          <div className="section-heading">
            <div>
              <p className="section-index">02</p>
              <h2>CAG 事件流</h2>
            </div>
            {task && (
              <span className={`status status-${task.status}`}>
                {STATUS_LABELS[task.status] ?? task.status}
              </span>
            )}
          </div>

          <div className="feedback-controls">
            <label>
              <span>反馈粒度</span>
              <select
                aria-label="反馈粒度"
                value={feedbackLevel}
                onChange={(event) =>
                  setFeedbackLevel(event.target.value as FeedbackLevel)
                }
              >
                <option value="essential">关键反馈</option>
                <option value="standard">标准反馈</option>
                <option value="full">完整反馈</option>
              </select>
            </label>
            <label>
              <span>画面条数</span>
              <select
                aria-label="画面条数"
                value={feedbackLimit}
                onChange={(event) => {
                  const value = event.target.value;
                  setFeedbackLimit(
                    value === "all"
                      ? "all"
                      : (Number(value) as FeedbackLimit),
                  );
                }}
              >
                <option value="20">20 条</option>
                <option value="50">50 条</option>
                <option value="100">100 条</option>
                <option value="all">全部</option>
              </select>
            </label>
            <p>
              后端已反馈 {events.length.toLocaleString()} 条
              <span aria-hidden="true"> · </span>
              当前显示 {visibleEvents.length.toLocaleString()} 条
            </p>
          </div>

          {approvals.some((item) => item.status === "pending") && (
            <div className="approval-panel" aria-label="待处理审批">
              <h3>待处理审批</h3>
              {approvals
                .filter((item) => item.status === "pending")
                .map((approval) => (
                  <article key={approval.id}>
                    <strong>{approval.request_type} · {approval.risk_level}</strong>
                    <p>{approval.subject}</p>
                    <div>
                      <button
                        type="button"
                        onClick={() => handleApprovalAction(approval.id, "approve")}
                      >
                        批准
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApprovalAction(approval.id, "deny")}
                      >
                        拒绝
                      </button>
                    </div>
                  </article>
                ))}
            </div>
          )}

          {events.length === 0 && (
            <div className="empty-state">
              <div className="empty-mark" aria-hidden="true">
                SSE
              </div>
              <h3>等待会话事件</h3>
              <p>CAG 将在这里持续显示各轮工作区、Agent、命令和测试事件。</p>
            </div>
          )}

          {events.length > 0 && visibleEvents.length === 0 && (
            <div className="feedback-empty">
              当前粒度没有可显示事件，后端事件仍然完整保留。
            </div>
          )}

          {visibleEvents.length > 0 && (
            <ol className="event-list">
              {visibleEvents.map((event) => (
                <li key={event.event_id}>
                  <span className="event-sequence">
                    {String(event.sequence).padStart(2, "0")}
                  </span>
                  <div>
                    <div className="event-title">
                      <strong>{EVENT_LABELS[event.type] ?? event.type}</strong>
                      <time dateTime={event.timestamp}>
                        {formatTime(event.timestamp)}
                      </time>
                    </div>
                    <p>{summarizeEvent(event)}</p>
                  </div>
                </li>
              ))}
              {busy && (
                <li className="event-pending">
                  <span className="event-sequence pulse" />
                  <div>
                    <strong>正在等待下一事件</strong>
                  </div>
                </li>
              )}
            </ol>
          )}
        </section>
      </section>
    </main>
  );
}
