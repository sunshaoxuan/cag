import {
  FormEvent,
  MouseEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  AuditEvent,
  AuditTask,
  auditEventsUrl,
  Conversation,
  conversationEventsUrl,
  createKnowledgeSource,
  createConversation,
  createTask,
  getKnowledgeStatus,
  getCodeKnowledgeSummary,
  getCodeSymbol,
  getTask,
  ingestKnowledgeSource,
  knowledgeIngestionEventsUrl,
  knowledgeIngestionRejectionsArchiveUrl,
  knowledgeIngestionRejectionsExportUrl,
  KnowledgeIngestion,
  KnowledgeIngestionEvent,
  KnowledgeIngestionRejectionPage,
  KnowledgeSource,
  KnowledgeSourceEntryPage,
  KnowledgeStatus,
  CodeKnowledgeSummary,
  CodeSymbol,
  CapabilityAsset,
  ApprovalRequest,
  StandardControl,
  listKnowledgeSources,
  listCodeSymbols,
  listKnowledgeSourceIngestions,
  listKnowledgeSourceEntries,
  listKnowledgeIngestionRejections,
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
  listAuditTasks,
  resolveApproval,
  revealKnowledgeSourceCredential,
  updateKnowledgeSource,
  deleteKnowledgeSource,
  validateKnowledgeSource,
} from "./api";
import packageMetadata from "../package.json";
import ApiDocsPage from "./ApiDocsPage";
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

const SOURCE_TYPE_LABELS: Record<KnowledgeSource["source_type"], string> = {
  local_directory: "本机文件夹",
  network_share: "网络共享",
  git: "Git 仓库",
  gitlab: "GitLab 仓库",
  svn: "SVN 仓库",
};

const SOURCE_STATUS_LABELS: Record<string, string> = {
  draft: "待验证",
  validated: "已验证",
  indexing: "索引中",
  ready: "可检索",
  approved: "可检索",
  failed: "同步失败",
};

const INGESTION_EVENT_LABELS: Record<string, string> = {
  "knowledge.ingestion.queued": "采集任务已排队",
  "knowledge.ingestion.started": "采集任务已启动",
  "knowledge.collection.started": "正在收集资源",
  "knowledge.collection.progress": "逐目录扫描进度",
  "knowledge.collection.completed": "资源收集完成",
  "knowledge.cleaning.started": "正在清洗内容",
  "knowledge.cleaning.completed": "内容清洗完成",
  "knowledge.indexing.started": "正在向量化并建立索引",
  "knowledge.indexing.completed": "向量索引完成",
  "knowledge.rejection.archive.created": "文件审计归档完成",
  "knowledge.rejection.archive.failed": "文件审计归档失败",
  "knowledge.code.analysis.completed": "代码结构分析完成",
  "knowledge.code.graph.persisted": "代码知识图谱已保存",
  "knowledge.memory.persisted": "来源记忆已保存",
  "knowledge.ingestion.completed": "本轮学习完成",
  "knowledge.ingestion.failed": "本轮学习失败",
};

const INGESTION_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  running: "处理中",
  completed: "已完成",
  failed: "失败",
};

const REJECTION_REASON_LABELS: Record<string, string> = {
  metadata_only_policy: "仅登记文件元数据",
  database_dump_policy: "数据库转储仅登记元数据",
  empty_file_path_only: "空文件仅索引路径信息",
  unsupported_extension: "不支持的文件类型",
  file_too_large: "文件超过大小限制",
  encoding_unsupported: "无法识别文本编码",
  empty_text: "未提取到有效文本",
  directory_read_error: "目录无法读取",
  file_stat_error: "无法读取文件属性",
  file_permission_denied: "没有文件读取权限",
  file_read_error: "文件读取失败",
  pdf_unreadable: "PDF 无法解析或已加密",
  office_archive_invalid: "Office 文件结构损坏",
  extractor_unavailable: "内容提取器不可用",
  extractor_rejected: "内容提取失败",
};

const PROCESSING_MODE_LABELS: Record<string, string> = {
  code: "代码分析",
  document: "文档知识",
  metadata_only: "仅登记元数据",
  path_only: "仅路径知识",
};

const PROCESSING_STATUS_LABELS: Record<string, string> = {
  observed: "已发现",
  indexed: "已建立索引",
  metadata_only: "已登记元数据",
  rejected: "处理失败",
  removed: "已移除",
};

function rejectionReasonLabel(reasonCode: string): string {
  return REJECTION_REASON_LABELS[reasonCode] ?? reasonCode;
}

function formatFileSize(value: number | null): string {
  if (value === null) return "未知";
  if (value < 1_000) return `${value} B`;
  if (value < 1_000_000) return `${(value / 1_000).toFixed(1)} KB`;
  if (value < 1_000_000_000) {
    return `${(value / 1_000_000).toFixed(1)} MB`;
  }
  return `${(value / 1_000_000_000).toFixed(2)} GB`;
}

type ChatTurn = {
  taskId: string;
  prompt: string;
  status: string;
  answer: string | null;
  intermediateMessages: IntermediateMessage[];
  error: string | null;
};

type IntermediateMessage = {
  id: string;
  role: string;
  text: string;
};

type FeedbackLevel = "essential" | "standard" | "full";
type FeedbackLimit = 20 | 50 | 100 | "all";
type AppPage =
  | "overview"
  | "conversation"
  | "audit"
  | "knowledge"
  | "codeKnowledge"
  | "memory"
  | "capabilities"
  | "apiDocs";

const PAGE_PATHS: Record<AppPage, string> = {
  overview: "/",
  conversation: "/conversation",
  audit: "/audit",
  knowledge: "/knowledge",
  codeKnowledge: "/code-knowledge",
  memory: "/memory",
  capabilities: "/capabilities",
  apiDocs: "/api-docs",
};

function pageFromPath(pathname: string): AppPage {
  if (pathname.startsWith("/conversation")) return "conversation";
  if (pathname.startsWith("/audit")) return "audit";
  if (pathname.startsWith("/knowledge")) return "knowledge";
  if (pathname.startsWith("/code-knowledge")) return "codeKnowledge";
  if (pathname.startsWith("/memory")) return "memory";
  if (pathname.startsWith("/capabilities")) return "capabilities";
  if (pathname.startsWith("/api-docs")) return "apiDocs";
  return "overview";
}

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

function summarizeKnowledgeIngestionEvent(
  event: KnowledgeIngestionEvent,
): string {
  if (event.type !== "knowledge.collection.progress") {
    return JSON.stringify(event.data);
  }
  const directory = String(event.data.directory ?? ".");
  const scanned = Number(event.data.directories_scanned ?? 0);
  const pending = Number(event.data.directories_pending ?? 0);
  const discovered = Number(event.data.files_discovered ?? 0);
  const processed = Number(event.data.files_processed ?? 0);
  const phase = String(event.data.phase ?? "");
  if (phase === "started") {
    return `开始遍历 ${directory} · 已完成 ${scanned} 个目录，待处理 ${pending} 个目录，已发现 ${discovered} 个文件`;
  }
  if (phase === "failed") {
    return `目录 ${directory} 读取失败 · 已完成 ${scanned} 个目录，待处理 ${pending} 个目录`;
  }
  return `完成目录 ${directory} · 已完成 ${scanned} 个目录，待处理 ${pending} 个目录，已处理 ${processed}/${discovered} 个文件`;
}

function isTerminal(status: string): boolean {
  return ["completed", "failed", "cancelled"].includes(status);
}

function projectIntermediateMessage(
  messages: IntermediateMessage[],
  event: TaskEvent,
): IntermediateMessage[] {
  const itemId = String(event.data.item_id ?? event.event_id);
  const agentRunId = String(event.data.agent_run_id ?? "task");
  const id = `${agentRunId}:${itemId}`;
  const existing = messages.find((message) => message.id === id);
  const text =
    event.data.text === undefined
      ? `${existing?.text ?? ""}${String(event.data.delta ?? "")}`
      : String(event.data.text);
  if (!text) return messages;

  const nextMessage: IntermediateMessage = {
    id,
    role: String(event.data.role ?? existing?.role ?? "agent"),
    text,
  };
  if (existing === undefined) return [...messages, nextMessage];
  return messages.map((message) => (message.id === id ? nextMessage : message));
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
  const [page, setPage] = useState<AppPage>(() =>
    pageFromPath(window.location.pathname),
  );
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
  const [codeKnowledgeSummary, setCodeKnowledgeSummary] =
    useState<CodeKnowledgeSummary | null>(null);
  const [codeSymbols, setCodeSymbols] = useState<CodeSymbol[]>([]);
  const [selectedCodeSymbol, setSelectedCodeSymbol] =
    useState<CodeSymbol | null>(null);
  const [codeSearch, setCodeSearch] = useState("");
  const [codeKind, setCodeKind] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidate[]>([]);
  const [knowledgeForm, setKnowledgeForm] = useState({
    name: "",
    sourceType: "local_directory" as KnowledgeSource["source_type"],
    location: "",
    reference: "",
    subpath: "",
    scope: "product" as "tenant" | "product",
    syncMode: "scheduled" as KnowledgeSource["sync_mode"],
    syncIntervalMinutes: 60,
    credentialUsername: "",
    credentialSecret: "",
  });
  const [knowledgeBusy, setKnowledgeBusy] = useState<string | null>(null);
  const [editingKnowledgeSourceId, setEditingKnowledgeSourceId] = useState<
    string | null
  >(null);
  const [knowledgeFormOpen, setKnowledgeFormOpen] = useState(false);
  const [knowledgeSourceQuery, setKnowledgeSourceQuery] = useState("");
  const [knowledgeSourceFilter, setKnowledgeSourceFilter] = useState<
    "all" | "enabled" | "disabled" | "running"
  >("all");
  const [knowledgeNotice, setKnowledgeNotice] = useState<string | null>(null);
  const [credentialVisible, setCredentialVisible] = useState(false);
  const [credentialCopied, setCredentialCopied] = useState(false);
  const [knowledgeEvents, setKnowledgeEvents] = useState<
    KnowledgeIngestionEvent[]
  >([]);
  const [knowledgeReceivedCount, setKnowledgeReceivedCount] = useState(0);
  const [knowledgeEventLimit, setKnowledgeEventLimit] = useState<
    50 | 100 | 200
  >(100);
  const [knowledgeHistories, setKnowledgeHistories] = useState<
    Record<string, KnowledgeIngestion[]>
  >({});
  const [expandedHistorySourceId, setExpandedHistorySourceId] = useState<
    string | null
  >(null);
  const [expandedRejectionIngestionId, setExpandedRejectionIngestionId] =
    useState<string | null>(null);
  const [knowledgeRejections, setKnowledgeRejections] = useState<
    Record<string, KnowledgeIngestionRejectionPage>
  >({});
  const [expandedInventorySourceId, setExpandedInventorySourceId] =
    useState<string | null>(null);
  const [knowledgeInventories, setKnowledgeInventories] = useState<
    Record<string, KnowledgeSourceEntryPage>
  >({});
  const [knowledgeMode, setKnowledgeMode] = useState("assist");
  const [harnessProfile, setHarnessProfile] = useState("single");
  const [learningMode, setLearningMode] = useState("capture");
  const [capabilities, setCapabilities] = useState<CapabilityAsset[]>([]);
  const [standardControls, setStandardControls] = useState<StandardControl[]>([]);
  const [promotionCount, setPromotionCount] = useState(0);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [auditTasks, setAuditTasks] = useState<AuditTask[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditReceivedCount, setAuditReceivedCount] = useState(0);
  const [auditDisplayLimit, setAuditDisplayLimit] = useState<
    50 | 100 | 200
  >(100);
  const sourceRef = useRef<EventSource | null>(null);
  const auditSourceRef = useRef<EventSource | null>(null);
  const knowledgeSourceRef = useRef<EventSource | null>(null);
  const knowledgeIngestionIdRef = useRef<string | null>(null);
  const knowledgeLastSequenceRef = useRef(0);
  const auditEventIdsRef = useRef<Set<string>>(new Set());

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
      auditSourceRef.current?.close();
      knowledgeSourceRef.current?.close();
      knowledgeIngestionIdRef.current = null;
    };
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setPage(pageFromPath(window.location.pathname));
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
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
        const activeIngestion = sourcesValue
          .map((source) => source.last_ingestion)
          .find(
            (ingestion) =>
              ingestion?.status === "queued" ||
              ingestion?.status === "running",
          );
        if (
          activeIngestion &&
          knowledgeIngestionIdRef.current !== activeIngestion.id
        ) {
          connectKnowledgeIngestion(activeIngestion.id);
        }
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    refreshKnowledge();
  }, []);

  function refreshCodeKnowledge(search = codeSearch, kind = codeKind) {
    if (!projectId) return;
    setCodeLoading(true);
    Promise.all([
      getCodeKnowledgeSummary(projectId),
      listCodeSymbols(projectId, search, kind),
    ])
      .then(([summary, symbols]) => {
        setCodeKnowledgeSummary(summary);
        setCodeSymbols(symbols);
        if (
          selectedCodeSymbol &&
          !symbols.some((item) => item.id === selectedCodeSymbol.id)
        ) {
          setSelectedCodeSymbol(null);
        }
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setCodeLoading(false));
  }

  useEffect(() => {
    if (page === "codeKnowledge" && projectId) {
      refreshCodeKnowledge();
    }
  }, [page, projectId]);

  async function selectCodeSymbol(symbol: CodeSymbol) {
    setCodeLoading(true);
    try {
      setSelectedCodeSymbol(await getCodeSymbol(projectId, symbol.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "代码知识读取失败");
    } finally {
      setCodeLoading(false);
    }
  }

  useEffect(() => {
    if (page !== "knowledge") return;
    const timer = window.setInterval(refreshKnowledge, 10_000);
    return () => window.clearInterval(timer);
  }, [page]);

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

  function refreshAudit() {
    listAuditTasks()
      .then(setAuditTasks)
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    refreshAudit();
  }, []);

  useEffect(() => {
    auditSourceRef.current?.close();
    auditSourceRef.current = null;
    if (page !== "audit") return;

    const source = new EventSource(auditEventsUrl());
    auditSourceRef.current = source;
    const handleAuditEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as AuditEvent;
      if (auditEventIdsRef.current.has(event.event_id)) return;
      auditEventIdsRef.current.add(event.event_id);
      setAuditReceivedCount((current) => current + 1);
      setAuditEvents((current) => {
        return [...current, event]
          .sort((a, b) => a.sequence - b.sequence)
          .slice(-200);
      });
      setAuditTasks((current) => {
        const existing = current.find(
          (item) => item.task_id === event.task_id,
        );
        if (!existing) {
          refreshAudit();
          return current;
        }
        let status = existing.status;
        if (event.type === "task.completed") status = "completed";
        if (event.type === "task.failed") status = "failed";
        if (event.type === "task.cancelled") status = "cancelled";
        if (
          event.type === "task.started" ||
          event.type === "workspace.preparing"
        ) {
          status = "running";
        }
        return current.map((item) =>
          item.task_id === event.task_id
            ? {
                ...item,
                status,
                event_count: Math.max(
                  item.event_count,
                  event.task_sequence,
                ),
                last_event_type: event.type,
                last_global_sequence: event.sequence,
              }
            : item,
        );
      });
    };
    source.addEventListener(
      "audit.event",
      handleAuditEvent as EventListener,
    );
    source.onerror = () => setError("审计事件流正在重连");
    return () => {
      source.close();
      if (auditSourceRef.current === source) {
        auditSourceRef.current = null;
      }
    };
  }, [page]);

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

    const isIntermediateMessage =
      event.type === "agent.message.delta" ||
      (event.type === "agent.message" && event.data.level !== "warning");

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
              intermediateMessages: isIntermediateMessage
                ? projectIntermediateMessage(turn.intermediateMessages, event)
                : turn.intermediateMessages,
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
    setKnowledgeNotice(null);
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
          intermediateMessages: [],
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

  function resetKnowledgeSourceForm() {
    setEditingKnowledgeSourceId(null);
    setCredentialVisible(false);
    setCredentialCopied(false);
    setKnowledgeForm({
      name: "",
      sourceType: "local_directory",
      location: "",
      reference: "",
      subpath: "",
      scope: "product",
      syncMode: "scheduled",
      syncIntervalMinutes: 60,
      credentialUsername: "",
      credentialSecret: "",
    });
  }

  function openKnowledgeSourceCreate() {
    resetKnowledgeSourceForm();
    setKnowledgeFormOpen(true);
    window.requestAnimationFrame(() => {
      document.querySelector(".source-form")?.scrollIntoView?.({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  async function handleKnowledgeSourceEdit(source: KnowledgeSource) {
    setKnowledgeFormOpen(true);
    setEditingKnowledgeSourceId(source.id);
    setCredentialVisible(false);
    setCredentialCopied(false);
    setKnowledgeForm({
      name: source.name,
      sourceType: source.source_type,
      location: source.location,
      reference: source.reference ?? "",
      subpath: source.subpath ?? "",
      scope: source.scope,
      syncMode: source.sync_mode,
      syncIntervalMinutes: source.sync_interval_minutes,
      credentialUsername: source.credential_username ?? "",
      credentialSecret: "",
    });
    window.requestAnimationFrame(() => {
      document.querySelector(".source-form")?.scrollIntoView?.({
        behavior: "smooth",
        block: "start",
      });
    });
    if (!source.credential_configured) {
      setKnowledgeNotice("正在编辑知识来源。");
      return;
    }
    setKnowledgeBusy(source.id);
    setKnowledgeNotice("正在从 Windows 凭据库读取已保存的凭据。");
    try {
      const credential = await revealKnowledgeSourceCredential(source.id);
      setKnowledgeForm((current) => ({
        ...current,
        credentialUsername:
          credential.username || source.credential_username || "",
        credentialSecret: credential.secret,
      }));
      setKnowledgeNotice(
        "已加载保存的凭据。可以显示、复制或输入新值进行轮换。",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "凭据读取失败");
      setKnowledgeNotice("凭据未能加载，密码字段留空会保留现有凭据。");
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleCredentialCopy() {
    if (!knowledgeForm.credentialSecret) return;
    setError(null);
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(
          knowledgeForm.credentialSecret,
        );
      } else {
        const temporary = document.createElement("textarea");
        temporary.value = knowledgeForm.credentialSecret;
        temporary.setAttribute("readonly", "");
        temporary.style.position = "fixed";
        temporary.style.opacity = "0";
        document.body.appendChild(temporary);
        temporary.select();
        const copied = document.execCommand("copy");
        temporary.remove();
        if (!copied) throw new Error("浏览器拒绝复制");
      }
      setCredentialCopied(true);
      window.setTimeout(() => setCredentialCopied(false), 2000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "凭据复制失败");
    }
  }

  async function handleKnowledgeSourceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId || !knowledgeForm.location.trim()) return;
    setError(null);
    setKnowledgeBusy(editingKnowledgeSourceId ?? "create");
    try {
      const sharedPayload = {
        name: knowledgeForm.name.trim() || "企业知识来源",
        source_type: knowledgeForm.sourceType,
        location: knowledgeForm.location.trim(),
        reference: knowledgeForm.reference.trim(),
        subpath: knowledgeForm.subpath.trim(),
        scope: knowledgeForm.scope,
        sync_mode: knowledgeForm.syncMode,
        sync_interval_minutes: knowledgeForm.syncIntervalMinutes,
        approved_for_codex: true,
        credential_username:
          knowledgeForm.credentialUsername.trim() || undefined,
        credential_secret:
          knowledgeForm.credentialSecret || undefined,
      };
      if (editingKnowledgeSourceId) {
        await updateKnowledgeSource(editingKnowledgeSourceId, sharedPayload);
        setKnowledgeNotice(
          "知识来源已更新。来源定位发生变化时，下一轮会重新建立索引。",
        );
      } else {
        await createKnowledgeSource({
          project_id: projectId,
          ...sharedPayload,
          reference: sharedPayload.reference || undefined,
          subpath: sharedPayload.subpath || undefined,
        });
        setKnowledgeNotice(
          knowledgeForm.syncMode === "scheduled"
            ? "知识来源已保存，调度器会持续检查并只重新索引变化内容。"
            : "知识来源已保存，可以先验证连接，再手动触发采集。",
        );
      }
      resetKnowledgeSourceForm();
      setKnowledgeFormOpen(false);
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "知识来源保存失败");
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleKnowledgeSourceValidate(sourceId: string) {
    setKnowledgeBusy(sourceId);
    setError(null);
    setKnowledgeNotice(null);
    try {
      const result = await validateKnowledgeSource(sourceId);
      setKnowledgeNotice(
        result.revision
          ? `${result.message}，版本 ${result.revision.slice(0, 12)}`
          : result.message,
      );
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "连接验证失败");
    } finally {
      setKnowledgeBusy(null);
    }
  }

  function connectKnowledgeIngestion(ingestionId: string) {
    if (
      knowledgeIngestionIdRef.current === ingestionId &&
      knowledgeSourceRef.current
    ) {
      return;
    }
    knowledgeSourceRef.current?.close();
    knowledgeIngestionIdRef.current = ingestionId;
    knowledgeLastSequenceRef.current = 0;
    setKnowledgeEvents([]);
    setKnowledgeReceivedCount(0);
    const source = new EventSource(
      knowledgeIngestionEventsUrl(ingestionId),
    );
    knowledgeSourceRef.current = source;
    const eventTypes = [
      "knowledge.ingestion.queued",
      "knowledge.ingestion.started",
      "knowledge.collection.started",
      "knowledge.collection.progress",
      "knowledge.collection.completed",
      "knowledge.cleaning.started",
      "knowledge.cleaning.completed",
      "knowledge.indexing.started",
      "knowledge.indexing.completed",
      "knowledge.rejection.archive.created",
      "knowledge.rejection.archive.failed",
      "knowledge.code.analysis.completed",
      "knowledge.code.graph.persisted",
      "knowledge.memory.persisted",
      "knowledge.ingestion.completed",
      "knowledge.ingestion.failed",
    ];
    const onEvent = (message: MessageEvent<string>) => {
      const item = JSON.parse(message.data) as KnowledgeIngestionEvent;
      if (item.sequence <= knowledgeLastSequenceRef.current) return;
      knowledgeLastSequenceRef.current = item.sequence;
      setKnowledgeReceivedCount((current) => current + 1);
      setKnowledgeEvents((current) => {
        return [...current, item]
          .sort((left, right) => left.sequence - right.sequence)
          .slice(-200);
      });
      if (
        item.type === "knowledge.ingestion.completed" ||
        item.type === "knowledge.ingestion.failed"
      ) {
        setKnowledgeBusy(null);
        setKnowledgeNotice(
          item.type === "knowledge.ingestion.completed"
            ? "采集、清洗、向量索引和来源记忆保存均已完成。"
            : "本轮知识采集失败，请查看失败事件和来源错误。",
        );
        refreshKnowledge();
        source.close();
        knowledgeIngestionIdRef.current = null;
      }
    };
    eventTypes.forEach((type) =>
      source.addEventListener(type, onEvent as EventListener),
    );
    source.onerror = () => setError("知识采集事件流正在重连");
  }

  async function handleKnowledgeSourceIngest(sourceId: string) {
    setKnowledgeBusy(sourceId);
    setError(null);
    setKnowledgeNotice("采集任务已创建，正在接收后端事实事件。");
    try {
      const ingestion = await ingestKnowledgeSource(sourceId);
      setKnowledgeSources((current) =>
        current.map((source) =>
          source.id === sourceId
            ? { ...source, last_ingestion: ingestion }
            : source,
        ),
      );
      connectKnowledgeIngestion(ingestion.id);
    } catch (reason) {
      setKnowledgeBusy(null);
      setError(reason instanceof Error ? reason.message : "知识采集失败");
    }
  }

  async function handleKnowledgeHistoryToggle(sourceId: string) {
    if (expandedHistorySourceId === sourceId) {
      setExpandedHistorySourceId(null);
      return;
    }
    setKnowledgeBusy(sourceId);
    setError(null);
    try {
      const items = await listKnowledgeSourceIngestions(sourceId);
      setKnowledgeHistories((current) => ({
        ...current,
        [sourceId]: items,
      }));
      setExpandedHistorySourceId(sourceId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "运行历史加载失败");
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleKnowledgeInventoryToggle(sourceId: string) {
    if (expandedInventorySourceId === sourceId) {
      setExpandedInventorySourceId(null);
      return;
    }
    setKnowledgeBusy(sourceId);
    try {
      const inventory = await listKnowledgeSourceEntries(sourceId);
      setKnowledgeInventories((current) => ({
        ...current,
        [sourceId]: inventory,
      }));
      setExpandedInventorySourceId(sourceId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleKnowledgeRejectionToggle(ingestionId: string) {
    if (expandedRejectionIngestionId === ingestionId) {
      setExpandedRejectionIngestionId(null);
      return;
    }
    setKnowledgeBusy(ingestionId);
    setError(null);
    try {
      const page = await listKnowledgeIngestionRejections(ingestionId);
      setKnowledgeRejections((current) => ({
        ...current,
        [ingestionId]: page,
      }));
      setExpandedRejectionIngestionId(ingestionId);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "文件审计明细加载失败",
      );
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleKnowledgeSourceToggle(source: KnowledgeSource) {
    setKnowledgeBusy(source.id);
    try {
      await updateKnowledgeSource(source.id, {
        enabled: !source.enabled,
      });
      setKnowledgeNotice(source.enabled ? "知识来源已停用。" : "知识来源已启用。");
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "来源状态更新失败");
    } finally {
      setKnowledgeBusy(null);
    }
  }

  async function handleKnowledgeSourceDelete(source: KnowledgeSource) {
    if (!window.confirm(`确认删除知识来源“${source.name}”及其索引吗？`)) {
      return;
    }
    setKnowledgeBusy(source.id);
    try {
      await deleteKnowledgeSource(source.id);
      setKnowledgeNotice("知识来源、索引、凭据引用和受管快照已删除。");
      refreshKnowledge();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "知识来源删除失败");
    } finally {
      setKnowledgeBusy(null);
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

  function navigateTo(
    nextPage: AppPage,
    event: MouseEvent<HTMLAnchorElement>,
  ) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    window.history.pushState({}, "", PAGE_PATHS[nextPage]);
    setPage(nextPage);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }

  const filteredKnowledgeSources = knowledgeSources.filter((source) => {
    const query = knowledgeSourceQuery.trim().toLocaleLowerCase();
    const matchesQuery =
      !query ||
      source.name.toLocaleLowerCase().includes(query) ||
      source.location.toLocaleLowerCase().includes(query) ||
      SOURCE_TYPE_LABELS[source.source_type]
        .toLocaleLowerCase()
        .includes(query);
    const isRunning =
      source.last_ingestion?.status === "queued" ||
      source.last_ingestion?.status === "running";
    const matchesFilter =
      knowledgeSourceFilter === "all" ||
      (knowledgeSourceFilter === "enabled" && source.enabled) ||
      (knowledgeSourceFilter === "disabled" && !source.enabled) ||
      (knowledgeSourceFilter === "running" && isRunning);
    return matchesQuery && matchesFilter;
  });
  const activeKnowledgeSource = knowledgeSources.find(
    (source) =>
      source.last_ingestion?.status === "queued" ||
      source.last_ingestion?.status === "running",
  );
  const latestCollectionProgress = [...knowledgeEvents]
    .reverse()
    .find((event) => event.type === "knowledge.collection.progress");

  return (
    <main className="app-shell">
      <header className="site-header">
        <a
          className="brand"
          href="/"
          aria-label="One Agent Gateway 首页"
          onClick={(event) => navigateTo("overview", event)}
        >
          <span className="brand-mark" aria-hidden="true">AG</span>
          <span className="brand-title">One Agent Gateway</span>
          <small className="brand-version">
            v{packageMetadata.version}
          </small>
        </a>
        <nav className="site-nav" aria-label="主要导航">
          <a
            href="/"
            aria-current={page === "overview" ? "page" : undefined}
            onClick={(event) => navigateTo("overview", event)}
          >
            总览
          </a>
          <a
            href="/conversation"
            aria-current={page === "conversation" ? "page" : undefined}
            onClick={(event) => navigateTo("conversation", event)}
          >
            API 测试台
          </a>
          <a
            href="/audit"
            aria-current={page === "audit" ? "page" : undefined}
            onClick={(event) => navigateTo("audit", event)}
          >
            API 监控
          </a>
          <a
            href="/knowledge"
            aria-current={page === "knowledge" ? "page" : undefined}
            onClick={(event) => navigateTo("knowledge", event)}
          >
            企业知识
          </a>
          <a
            href="/code-knowledge"
            aria-current={page === "codeKnowledge" ? "page" : undefined}
            onClick={(event) => navigateTo("codeKnowledge", event)}
          >
            代码知识
          </a>
          <a
            href="/memory"
            aria-current={page === "memory" ? "page" : undefined}
            onClick={(event) => navigateTo("memory", event)}
          >
            长期记忆
          </a>
          <a
            href="/api-docs"
            aria-current={page === "apiDocs" ? "page" : undefined}
            onClick={(event) => navigateTo("apiDocs", event)}
          >
            API 文档
          </a>
          <a
            href="/capabilities"
            aria-current={page === "capabilities" ? "page" : undefined}
            onClick={(event) => navigateTo("capabilities", event)}
          >
            能力治理
          </a>
        </nav>
        <div className="site-actions">
          <a
            className="button button-ghost"
            href="/audit"
            onClick={(event) => navigateTo("audit", event)}
          >
            监控 API
          </a>
          <a
            className="button button-primary"
            href="/conversation"
            onClick={(event) => navigateTo("conversation", event)}
          >
            打开测试台
          </a>
        </div>
      </header>

      {page === "overview" && (
        <>
          <header className="hero">
            <div className="hero-content">
              <p className="eyebrow">LOCAL CODEX · ENTERPRISE KNOWLEDGE · AGENT HARNESS</p>
              <h1>
                一个入口，
                <span>让企业知识与 Agent 协同工作。</span>
              </h1>
              <p className="hero-copy">
                外部系统通过 API 提交任务，CAG 统一调度知识、Agent、审批和验证，
                并将全部动作写入可监听、可恢复的审计事件流。
              </p>
              <div className="hero-actions">
                <a
                  className="button button-primary button-large"
                  href="/conversation"
                  onClick={(event) => navigateTo("conversation", event)}
                >
                  打开 API 测试台
                </a>
                <a
                  className="button button-outline button-large"
                  href="/audit"
                  onClick={(event) => navigateTo("audit", event)}
                >
                  查看调用监控
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
          <section className="module-grid" aria-label="功能入口">
            <a
              className="module-card module-card-primary"
              href="/conversation"
              onClick={(event) => navigateTo("conversation", event)}
            >
              <span>01</span>
              <strong>API 测试台</strong>
              <p>使用与外部调用相同的任务 API 验证连续对话和 SSE。</p>
              <small>发起测试调用</small>
            </a>
            <a
              className="module-card"
              href="/audit"
              onClick={(event) => navigateTo("audit", event)}
            >
              <span>02</span>
              <strong>API 调用监控</strong>
              <p>{auditTasks.length} 条调用轨迹，持续接收全局审计事件。</p>
              <small>查看跟踪审计</small>
            </a>
            <a
              className="module-card"
              href="/knowledge"
              onClick={(event) => navigateTo("knowledge", event)}
            >
              <span>03</span>
              <strong>企业知识</strong>
              <p>{knowledgeSources.length} 个来源，1024 维向量与记忆候选治理。</p>
              <small>管理知识</small>
            </a>
            <a
              className="module-card"
              href="/capabilities"
              onClick={(event) => navigateTo("capabilities", event)}
            >
              <span>04</span>
              <strong>能力治理</strong>
              <p>{capabilities.length} 项 Skill、Tool、Validator 与控制映射。</p>
              <small>查看能力</small>
            </a>
          </section>
        </>
      )}

      {page === "apiDocs" && <ApiDocsPage />}

      {page === "audit" && (
        <>
          <section className="page-intro">
            <div>
              <p className="eyebrow">EXTERNAL API OBSERVABILITY</p>
              <h1>API 调用监控</h1>
              <p>
                监听从外部 API 和网页测试台进入的任务，跟踪其触发的全部
                Gateway、知识、Agent、命令、审批和验证动作。
              </p>
            </div>
            <div className="page-metric">
              <span>调用轨迹</span>
              <strong>{auditTasks.length}</strong>
            </div>
          </section>
          <section
            className="audit-grid page-panel"
            aria-label="API 跟踪审计"
          >
            <section className="audit-calls panel">
              <div className="section-heading">
                <div>
                  <p className="section-index">01</p>
                  <h2>API 调用轨迹</h2>
                </div>
                <span className="status status-completed">持久化审计</span>
              </div>
              <p className="audit-explainer">
                每次调用返回 Trace ID。相同客户端与 Idempotency Key
                只会对应一条任务轨迹。
              </p>
              <div className="audit-call-list">
                {auditTasks.length === 0 && (
                  <div className="empty-state compact-empty">
                    <h3>等待 API 调用</h3>
                    <p>外部调用进入后会自动出现在这里。</p>
                  </div>
                )}
                {auditTasks.slice(0, 40).map((auditTask) => (
                  <article className="audit-call" key={auditTask.task_id}>
                    <div>
                      <strong>{auditTask.project_code}</strong>
                      <span
                        className={`status status-${auditTask.status}`}
                      >
                        {STATUS_LABELS[auditTask.status] ?? auditTask.status}
                      </span>
                    </div>
                    <p>
                      {auditTask.trigger_source === "test_console"
                        ? "网页测试台"
                        : "外部 API"}
                      <span aria-hidden="true"> · </span>
                      {auditTask.client_id}
                    </p>
                    <code>{auditTask.trace_id}</code>
                    <small>
                      {auditTask.event_count} 个动作
                      <span aria-hidden="true"> · </span>
                      最后序号 {auditTask.last_global_sequence ?? "等待中"}
                    </small>
                  </article>
                ))}
              </div>
            </section>

            <section className="audit-events panel" aria-live="polite">
              <div className="section-heading">
                <div>
                  <p className="section-index">02</p>
                  <h2>全局审计事件流</h2>
                </div>
                <span className="status status-running">SSE 监听中</span>
              </div>
              <div className="feedback-controls audit-feedback">
                <label>
                  <span>画面条数</span>
                  <select
                    aria-label="审计画面条数"
                    value={auditDisplayLimit}
                    onChange={(event) =>
                      setAuditDisplayLimit(
                        Number(event.target.value) as 50 | 100 | 200,
                      )
                    }
                  >
                    <option value="50">50 条</option>
                    <option value="100">100 条</option>
                    <option value="200">200 条</option>
                  </select>
                </label>
                <p>
                  后端已反馈 {auditReceivedCount.toLocaleString()} 条
                  <span aria-hidden="true"> · </span>
                  当前显示{" "}
                  {Math.min(
                    auditEvents.length,
                    auditDisplayLimit,
                  ).toLocaleString()}{" "}
                  条
                </p>
              </div>
              {auditEvents.length === 0 && (
                <div className="empty-state">
                  <div className="empty-mark" aria-hidden="true">
                    API
                  </div>
                  <h3>等待审计事件</h3>
                  <p>事件会按 Gateway 全局序号持续投影到这里。</p>
                </div>
              )}
              {auditEvents.length > 0 && (
                <ol className="event-list audit-event-list">
                  {auditEvents
                    .slice(-auditDisplayLimit)
                    .reverse()
                    .map((event) => (
                      <li key={event.event_id}>
                        <span className="event-sequence">
                          {String(event.sequence).padStart(2, "0")}
                        </span>
                        <div>
                          <div className="event-title">
                            <strong>
                              {EVENT_LABELS[event.type] ?? event.type}
                            </strong>
                            <time dateTime={event.timestamp}>
                              {formatTime(event.timestamp)}
                            </time>
                          </div>
                          <p>{summarizeEvent(event)}</p>
                          <small>
                            {event.client_id}
                            <span aria-hidden="true"> · </span>
                            Trace {event.trace_id.slice(0, 8)}
                            <span aria-hidden="true"> · </span>
                            Task #{event.task_sequence}
                          </small>
                        </div>
                      </li>
                    ))}
                </ol>
              )}
            </section>
          </section>
        </>
      )}

      {page === "knowledge" && (
        <>
          <section className="page-intro">
            <div>
              <p className="eyebrow">KNOWLEDGE GOVERNANCE</p>
              <h1>企业知识</h1>
              <p>维护知识位置，验证连接，并追踪采集、清洗与索引。</p>
            </div>
            <div className="page-metric">
              <span>已登记来源</span>
              <strong>{knowledgeSources.length}</strong>
            </div>
          </section>
          <section
            className="knowledge-console panel page-panel"
            aria-label="企业知识治理"
          >
            <div className="section-heading">
              <div>
                <p className="section-index">SOURCE REGISTRY</p>
                <h2>知识来源</h2>
              </div>
              <span
                className={`status status-${
                  knowledgeStatus?.ready ? "completed" : "failed"
                }`}
              >
                {knowledgeStatus?.ready ? "Ollama 就绪" : "知识服务未就绪"}
              </span>
            </div>
            <div className="knowledge-summary">
              <p>
                向量模型 {knowledgeStatus?.embedding_model ?? "未配置"}
                <span aria-hidden="true"> · </span>
                {knowledgeStatus?.dimensions ?? "未知"} 维
              </p>
              <p>
                {knowledgeStatus?.scheduler_running
                  ? `自动监控运行中，每 ${knowledgeStatus.scheduler_poll_seconds} 秒检查到期来源`
                  : knowledgeStatus?.scheduler_enabled
                    ? "自动监控正在启动"
                    : "自动监控未启用"}
              </p>
              <p>
                每轮扫描来源完整快照，只对新增或变化内容重新向量化。
              </p>
            </div>
            {knowledgeNotice && (
              <div className="knowledge-notice" role="status">
                {knowledgeNotice}
              </div>
            )}

            <section
              className="knowledge-management-bar"
              aria-label="知识来源管理工具"
            >
              <div className="knowledge-management-metrics">
                <article>
                  <span>来源总数</span>
                  <strong>{knowledgeSources.length}</strong>
                </article>
                <article>
                  <span>已启用</span>
                  <strong>
                    {
                      knowledgeSources.filter((source) => source.enabled)
                        .length
                    }
                  </strong>
                </article>
                <article>
                  <span>正在学习</span>
                  <strong>{activeKnowledgeSource ? 1 : 0}</strong>
                </article>
                <article>
                  <span>需要处理</span>
                  <strong>
                    {
                      knowledgeSources.filter(
                        (source) =>
                          source.status === "failed" ||
                          source.consecutive_failures > 0,
                      ).length
                    }
                  </strong>
                </article>
              </div>
              <div className="knowledge-management-controls">
                <input
                  aria-label="搜索知识来源"
                  value={knowledgeSourceQuery}
                  onChange={(event) =>
                    setKnowledgeSourceQuery(event.target.value)
                  }
                  placeholder="按名称、位置或类型搜索"
                />
                <select
                  aria-label="筛选知识来源"
                  value={knowledgeSourceFilter}
                  onChange={(event) =>
                    setKnowledgeSourceFilter(
                      event.target.value as typeof knowledgeSourceFilter,
                    )
                  }
                >
                  <option value="all">全部来源</option>
                  <option value="enabled">仅已启用</option>
                  <option value="disabled">仅已停用</option>
                  <option value="running">正在学习</option>
                </select>
                <button type="button" onClick={openKnowledgeSourceCreate}>
                  创建知识来源
                </button>
              </div>
            </section>

            {knowledgeFormOpen && (
              <form
                className="source-form"
                onSubmit={handleKnowledgeSourceSubmit}
              >
              <div className="source-form-heading">
                <div>
                  <span>
                    {editingKnowledgeSourceId ? "编辑来源" : "新增来源"}
                  </span>
                  <strong>
                    {editingKnowledgeSourceId
                      ? "更新位置、版本、范围或认证信息"
                      : "登记一个可持续采集的位置"}
                  </strong>
                </div>
                <div className="source-form-actions">
                  {editingKnowledgeSourceId && (
                    <button
                      type="button"
                      className="button-quiet"
                      disabled={knowledgeBusy !== null}
                      onClick={() => {
                        resetKnowledgeSourceForm();
                        setKnowledgeFormOpen(false);
                      }}
                    >
                      取消编辑
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={
                      knowledgeBusy !== null ||
                      !projectId ||
                      !knowledgeForm.location.trim()
                    }
                  >
                    {knowledgeBusy !== null
                      ? "正在保存"
                      : editingKnowledgeSourceId
                        ? "保存修改"
                        : "保存来源"}
                  </button>
                </div>
              </div>
              <div className="source-form-grid">
                <label>
                  <span>来源名称</span>
                  <input
                    value={knowledgeForm.name}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                    placeholder="例如 产品设计文档"
                  />
                </label>
                <label>
                  <span>来源类型</span>
                  <select
                    value={knowledgeForm.sourceType}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        sourceType: event.target
                          .value as KnowledgeSource["source_type"],
                      }))
                    }
                  >
                    {Object.entries(SOURCE_TYPE_LABELS).map(
                      ([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <label className="source-location-field">
                  <span>位置或仓库 URL</span>
                  <input
                    required
                    value={knowledgeForm.location}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        location: event.target.value,
                      }))
                    }
                    placeholder={
                      knowledgeForm.sourceType === "network_share"
                        ? "\\\\server\\share\\documents"
                        : knowledgeForm.sourceType === "local_directory"
                          ? "D:\\knowledge\\product"
                          : "https://gitlab.example.com/group/project.git"
                    }
                  />
                </label>
                <label>
                  <span>分支或版本</span>
                  <input
                    value={knowledgeForm.reference}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        reference: event.target.value,
                      }))
                    }
                    placeholder="留空使用默认版本"
                  />
                </label>
                <label>
                  <span>限定子目录</span>
                  <input
                    value={knowledgeForm.subpath}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        subpath: event.target.value,
                      }))
                    }
                    placeholder="例如 docs/architecture"
                  />
                </label>
                <label>
                  <span>知识范围</span>
                  <select
                    value={knowledgeForm.scope}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        scope: event.target.value as "tenant" | "product",
                      }))
                    }
                  >
                    <option value="product">产品共享</option>
                    <option value="tenant">当前客户</option>
                  </select>
                </label>
                <label>
                  <span>同步策略</span>
                  <select
                    value={knowledgeForm.syncMode}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        syncMode: event.target
                          .value as KnowledgeSource["sync_mode"],
                      }))
                    }
                  >
                    <option value="scheduled">持续自动同步</option>
                    <option value="manual">仅手动同步</option>
                  </select>
                </label>
                <label>
                  <span>检查间隔</span>
                  <select
                    value={knowledgeForm.syncIntervalMinutes}
                    disabled={knowledgeForm.syncMode === "manual"}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        syncIntervalMinutes: Number(event.target.value),
                      }))
                    }
                  >
                    <option value={15}>每 15 分钟</option>
                    <option value={60}>每小时</option>
                    <option value={360}>每 6 小时</option>
                    <option value={1440}>每天</option>
                    <option value={10080}>每周</option>
                  </select>
                </label>
                <label>
                  <span>认证用户名</span>
                  <input
                    autoComplete="username"
                    value={knowledgeForm.credentialUsername}
                    onChange={(event) =>
                      setKnowledgeForm((current) => ({
                        ...current,
                        credentialUsername: event.target.value,
                      }))
                    }
                    placeholder="没有认证时留空"
                  />
                </label>
                <label>
                  <span>密码或访问令牌</span>
                  <div className="credential-input-row">
                    <input
                      type={credentialVisible ? "text" : "password"}
                      autoComplete="new-password"
                      value={knowledgeForm.credentialSecret}
                      onChange={(event) => {
                        setCredentialCopied(false);
                        setKnowledgeForm((current) => ({
                          ...current,
                          credentialSecret: event.target.value,
                        }));
                      }}
                      placeholder="保存到 Windows 凭据库"
                    />
                    <button
                      type="button"
                      className="credential-action"
                      disabled={!knowledgeForm.credentialSecret}
                      onClick={() =>
                        setCredentialVisible((current) => !current)
                      }
                    >
                      {credentialVisible ? "隐藏" : "显示"}
                    </button>
                    <button
                      type="button"
                      className="credential-action"
                      disabled={!knowledgeForm.credentialSecret}
                      onClick={handleCredentialCopy}
                    >
                      {credentialCopied ? "已复制" : "复制"}
                    </button>
                  </div>
                </label>
              </div>
              <small>
                编辑时会按需从 Windows 凭据库读取密码或令牌。显示和复制只发生在当前管理页面，数据库继续保存凭据引用。
              </small>
              </form>
            )}

            <div className="source-workspace">
              <section className="source-registry" aria-label="已登记知识来源">
                <div className="source-section-title">
                  <h3>已登记来源</h3>
                  <span>{knowledgeSources.length} 个</span>
                </div>
                {knowledgeSources.length === 0 && (
                  <div className="compact-empty">
                    <p>尚未登记知识来源，请使用“创建知识来源”。</p>
                  </div>
                )}
                {knowledgeSources.length > 0 &&
                  filteredKnowledgeSources.length === 0 && (
                    <div className="compact-empty">
                      <p>没有符合当前搜索和筛选条件的来源。</p>
                    </div>
                  )}
                {filteredKnowledgeSources.map((source) => (
                  <article className="source-card" key={source.id}>
                    <header>
                      <div>
                        <span>{SOURCE_TYPE_LABELS[source.source_type]}</span>
                        <strong>{source.name}</strong>
                      </div>
                      <span
                        className={`status status-${
                          source.status === "approved" ||
                          source.status === "ready"
                            ? "completed"
                            : source.status
                        }`}
                      >
                        {source.enabled
                          ? SOURCE_STATUS_LABELS[source.status] ??
                            source.status
                          : "已停用"}
                      </span>
                    </header>
                    <p>{source.location}</p>
                    <small className="source-freshness">
                      {source.last_validated_at
                        ? `最近验证 ${formatTime(source.last_validated_at)}`
                        : "尚未验证连接"}
                      <span aria-hidden="true"> · </span>
                      {source.last_collected_at
                        ? `最近采集 ${formatTime(source.last_collected_at)}`
                        : "尚未采集"}
                      {source.source_commit && (
                        <>
                          <span aria-hidden="true"> · </span>
                          版本 {source.source_commit.slice(0, 12)}
                        </>
                      )}
                    </small>
                    <div className="source-sync-state">
                      <span>
                        {source.sync_mode === "scheduled"
                          ? `自动同步 · 每 ${source.sync_interval_minutes} 分钟`
                          : "仅手动同步"}
                      </span>
                      <span>
                        {source.next_sync_at
                          ? `下次检查 ${formatTime(source.next_sync_at)}`
                          : "当前无计划任务"}
                      </span>
                      <span>
                        {source.last_content_change_at
                          ? `最近内容变化 ${formatTime(source.last_content_change_at)}`
                          : "尚未发现内容变化"}
                      </span>
                      {source.consecutive_failures > 0 && (
                        <span className="source-sync-warning">
                          连续失败 {source.consecutive_failures} 次，已安排重试
                        </span>
                      )}
                    </div>
                    <div className="source-tags">
                      <span>
                        {source.scope === "product"
                          ? "产品共享"
                          : "当前客户"}
                      </span>
                      {source.reference && <span>{source.reference}</span>}
                      {source.subpath && <span>{source.subpath}</span>}
                      {source.credential_configured && <span>凭据已配置</span>}
                    </div>
                    {(source.entry_summary?.total ?? 0) > 0 && (
                      <div
                        className="source-inventory-summary"
                        aria-label="文件资产处理分类"
                      >
                        <span>
                          文件资产{" "}
                          {(source.entry_summary?.total ?? 0).toLocaleString()}
                        </span>
                        <span>
                          代码{" "}
                          {(source.entry_summary?.code ?? 0).toLocaleString()}
                        </span>
                        <span>
                          文档{" "}
                          {(source.entry_summary?.document ?? 0).toLocaleString()}
                        </span>
                        <span>
                          仅元数据{" "}
                          {(
                            source.entry_summary?.metadata_only ?? 0
                          ).toLocaleString()}
                        </span>
                        <span>
                          仅路径{" "}
                          {(
                            source.entry_summary?.path_only ?? 0
                          ).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {source.last_ingestion && (
                      <dl className="source-metrics">
                        <div>
                          <dt>发现文件</dt>
                          <dd>{source.last_ingestion.files_seen}</dd>
                        </div>
                        <div>
                          <dt>新增分块</dt>
                          <dd>{source.last_ingestion.chunks_written}</dd>
                        </div>
                        <div>
                          <dt>复用向量</dt>
                          <dd>{source.last_ingestion.vectors_reused}</dd>
                        </div>
                        <div>
                          <dt>变化文件</dt>
                          <dd>{source.last_ingestion.changed_files}</dd>
                        </div>
                        <div>
                          <dt>删除文件</dt>
                          <dd>{source.last_ingestion.removed_files}</dd>
                        </div>
                        <div>
                          <dt>未变化</dt>
                          <dd>{source.last_ingestion.unchanged_files}</dd>
                        </div>
                      </dl>
                    )}
                    {source.error && (
                      <p className="source-error">{source.error}</p>
                    )}
                    <footer>
                      <button
                        type="button"
                        className="button-quiet"
                        disabled={knowledgeBusy !== null}
                        onClick={() => handleKnowledgeSourceEdit(source)}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="button-quiet"
                        disabled={knowledgeBusy !== null}
                        onClick={() =>
                          handleKnowledgeInventoryToggle(source.id)
                        }
                      >
                        {expandedInventorySourceId === source.id
                          ? "收起文件资产"
                          : "文件资产"}
                      </button>
                      <button
                        type="button"
                        className="button-quiet"
                        disabled={knowledgeBusy !== null}
                        onClick={() =>
                          handleKnowledgeHistoryToggle(source.id)
                        }
                      >
                        {expandedHistorySourceId === source.id
                          ? "收起历史"
                          : "运行历史"}
                      </button>
                      <button
                        type="button"
                        disabled={knowledgeBusy !== null}
                        onClick={() =>
                          handleKnowledgeSourceValidate(source.id)
                        }
                      >
                        验证连接
                      </button>
                      <button
                        type="button"
                        disabled={knowledgeBusy !== null || !source.enabled}
                        onClick={() =>
                          handleKnowledgeSourceIngest(source.id)
                        }
                      >
                        {knowledgeBusy === source.id
                          ? "正在处理"
                          : "采集并学习"}
                      </button>
                      <button
                        type="button"
                        className="button-quiet"
                        disabled={knowledgeBusy !== null}
                        onClick={() =>
                          handleKnowledgeSourceToggle(source)
                        }
                      >
                        {source.enabled ? "停用" : "启用"}
                      </button>
                      <button
                        type="button"
                        className="button-danger"
                        disabled={knowledgeBusy !== null}
                        onClick={() =>
                          handleKnowledgeSourceDelete(source)
                        }
                      >
                        删除
                      </button>
                    </footer>
                    {expandedInventorySourceId === source.id &&
                      knowledgeInventories[source.id] && (
                        <section
                          className="source-inventory"
                          aria-label={`${source.name}文件资产`}
                        >
                          <div className="source-inventory-heading">
                            <strong>
                              当前文件资产{" "}
                              {knowledgeInventories[
                                source.id
                              ].total.toLocaleString()}{" "}
                              条
                            </strong>
                            <small>
                              展示前{" "}
                              {knowledgeInventories[
                                source.id
                              ].items.length.toLocaleString()}{" "}
                              条
                            </small>
                          </div>
                          <div className="source-inventory-table-wrap">
                            <table>
                              <thead>
                                <tr>
                                  <th>处理方式</th>
                                  <th>相对路径</th>
                                  <th>大小</th>
                                  <th>状态</th>
                                  <th>最后发现</th>
                                </tr>
                              </thead>
                              <tbody>
                                {knowledgeInventories[source.id].items.map(
                                  (item) => (
                                    <tr key={item.id}>
                                      <td>
                                        {PROCESSING_MODE_LABELS[
                                          item.processing_mode
                                        ] ?? item.processing_mode}
                                      </td>
                                      <td>{item.relative_path}</td>
                                      <td>{formatFileSize(item.file_size)}</td>
                                      <td>
                                        {item.reason_code
                                          ? rejectionReasonLabel(
                                              item.reason_code,
                                            )
                                          : PROCESSING_STATUS_LABELS[
                                              item.processing_status
                                            ] ?? item.processing_status}
                                      </td>
                                      <td>{formatTime(item.last_seen_at)}</td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </table>
                          </div>
                        </section>
                      )}
                    {expandedHistorySourceId === source.id && (
                      <div
                        className="source-history"
                        aria-label={`${source.name}运行历史`}
                      >
                        {(knowledgeHistories[source.id] ?? []).length ===
                          0 && <p>尚无同步运行记录。</p>}
                        {(knowledgeHistories[source.id] ?? []).map(
                          (ingestion) => (
                            <article key={ingestion.id}>
                              <div>
                                <strong>
                                  {ingestion.trigger === "scheduled"
                                    ? "自动同步"
                                    : "手动同步"}
                                </strong>
                                <span>
                                  {INGESTION_STATUS_LABELS[
                                    ingestion.status
                                  ] ?? ingestion.status}
                                </span>
                                <time dateTime={ingestion.created_at}>
                                  {formatTime(ingestion.created_at)}
                                </time>
                              </div>
                              <small>
                                发现 {ingestion.files_seen} · 变化{" "}
                                {ingestion.changed_files} · 删除{" "}
                                {ingestion.removed_files} · 未变化{" "}
                                {ingestion.unchanged_files} · 复用向量{" "}
                                {ingestion.vectors_reused} · 拒绝{" "}
                                {ingestion.rejected_files ?? 0} · 跳过{" "}
                                {ingestion.skipped_files ?? 0}
                              </small>
                              {ingestion.error && (
                                <div className="ingestion-error-summary">
                                  <p>
                                    {ingestion.error_summary ??
                                      ingestion.error.split("\n")[0]}
                                  </p>
                                  <details>
                                    <summary>查看完整技术日志</summary>
                                    <pre>{ingestion.error}</pre>
                                  </details>
                                </div>
                              )}
                              {((ingestion.rejected_files ?? 0) > 0 ||
                                (ingestion.skipped_files ?? 0) > 0 ||
                                ingestion.rejection_archive_name) && (
                                <div className="rejection-audit-actions">
                                  <button
                                    type="button"
                                    className="button-quiet"
                                    disabled={knowledgeBusy !== null}
                                    onClick={() =>
                                      handleKnowledgeRejectionToggle(
                                        ingestion.id,
                                      )
                                    }
                                  >
                                    {expandedRejectionIngestionId ===
                                    ingestion.id
                                      ? "收起文件审计"
                                      : "查看文件审计"}
                                  </button>
                                  <a
                                    href={knowledgeIngestionRejectionsExportUrl(
                                      ingestion.id,
                                    )}
                                    download
                                  >
                                    导出 CSV
                                  </a>
                                  {ingestion.rejection_archive_name && (
                                    <a
                                      href={knowledgeIngestionRejectionsArchiveUrl(
                                        ingestion.id,
                                      )}
                                      download
                                    >
                                      下载压缩归档
                                    </a>
                                  )}
                                </div>
                              )}
                              {expandedRejectionIngestionId === ingestion.id &&
                                knowledgeRejections[ingestion.id] && (
                                  <section
                                    className="rejection-audit"
                                    aria-label={`${ingestion.id}文件处理审计`}
                                  >
                                    <div className="rejection-audit-summary">
                                      <strong>
                                        文件处理审计{" "}
                                        {knowledgeRejections[
                                          ingestion.id
                                        ].total.toLocaleString()}{" "}
                                        条
                                      </strong>
                                      {knowledgeRejections[
                                        ingestion.id
                                      ].summary.map((item) => (
                                        <span
                                          key={`${item.disposition}-${item.reason_code}`}
                                        >
                                          {item.disposition === "rejected"
                                            ? "拒绝"
                                            : "跳过"}{" "}
                                          {rejectionReasonLabel(
                                            item.reason_code,
                                          )}{" "}
                                          {item.count.toLocaleString()}
                                        </span>
                                      ))}
                                    </div>
                                    <div className="rejection-audit-table-wrap">
                                      <table>
                                        <thead>
                                          <tr>
                                            <th>处理</th>
                                            <th>文件路径</th>
                                            <th>原因</th>
                                            <th>扩展名</th>
                                            <th>错误</th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {knowledgeRejections[
                                            ingestion.id
                                          ].items.map((item) => (
                                            <tr key={item.id}>
                                              <td>
                                                {item.disposition ===
                                                "rejected"
                                                  ? "拒绝"
                                                  : "跳过"}
                                              </td>
                                              <td>{item.relative_path}</td>
                                              <td>
                                                {rejectionReasonLabel(
                                                  item.reason_code,
                                                )}
                                                <small>
                                                  {item.reason_code}
                                                </small>
                                              </td>
                                              <td>{item.extension || "无"}</td>
                                              <td>
                                                {item.error_type
                                                  ? `${item.error_type}: ${
                                                      item.error_message ?? ""
                                                    }`
                                                  : "无异常"}
                                              </td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                    {knowledgeRejections[ingestion.id].total >
                                      knowledgeRejections[ingestion.id].items
                                        .length && (
                                      <small>
                                        页面显示前{" "}
                                        {knowledgeRejections[
                                          ingestion.id
                                        ].items.length.toLocaleString()}{" "}
                                        条，完整记录请导出 CSV。
                                      </small>
                                    )}
                                  </section>
                                )}
                            </article>
                          ),
                        )}
                      </div>
                    )}
                  </article>
                ))}
              </section>
              <section className="collection-events" aria-label="学习运行中心">
                <div className="source-section-title">
                  <h3>学习运行中心</h3>
                  <div className="collection-event-controls">
                    <span>
                      后端已反馈 {knowledgeReceivedCount.toLocaleString()} 条
                    </span>
                    <select
                      aria-label="采集事件画面条数"
                      value={knowledgeEventLimit}
                      onChange={(event) =>
                        setKnowledgeEventLimit(
                          Number(event.target.value) as 50 | 100 | 200,
                        )
                      }
                    >
                      <option value="50">显示 50 条</option>
                      <option value="100">显示 100 条</option>
                      <option value="200">显示 200 条</option>
                    </select>
                  </div>
                </div>
                <div
                  className={`learning-run-overview ${
                    activeKnowledgeSource ? "is-running" : ""
                  }`}
                >
                  <div>
                    <span>
                      {activeKnowledgeSource
                        ? "当前正在学习"
                        : "当前没有运行任务"}
                    </span>
                    <strong>
                      {activeKnowledgeSource?.name ?? "等待学习任务"}
                    </strong>
                  </div>
                  {activeKnowledgeSource?.last_ingestion && (
                    <dl>
                      <div>
                        <dt>状态</dt>
                        <dd>
                          {INGESTION_STATUS_LABELS[
                            activeKnowledgeSource.last_ingestion.status
                          ] ??
                            activeKnowledgeSource.last_ingestion.status}
                        </dd>
                      </div>
                      <div>
                        <dt>开始时间</dt>
                        <dd>
                          {activeKnowledgeSource.last_ingestion.started_at
                            ? formatTime(
                                activeKnowledgeSource.last_ingestion
                                  .started_at,
                              )
                            : "等待启动"}
                        </dd>
                      </div>
                      <div>
                        <dt>当前目录</dt>
                        <dd>
                          {String(
                            latestCollectionProgress?.data.directory ?? "准备中",
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>文件进度</dt>
                        <dd>
                          {String(
                            latestCollectionProgress?.data.files_processed ??
                              0,
                          )}
                          /
                          {String(
                            latestCollectionProgress?.data.files_discovered ??
                              0,
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>拒绝</dt>
                        <dd>
                          {String(
                            latestCollectionProgress?.data.rejected_files ??
                              activeKnowledgeSource.last_ingestion
                                .rejected_files ??
                              0,
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>跳过</dt>
                        <dd>
                          {String(
                            latestCollectionProgress?.data.skipped_files ??
                              activeKnowledgeSource.last_ingestion
                                .skipped_files ??
                              0,
                          )}
                        </dd>
                      </div>
                    </dl>
                  )}
                  {!activeKnowledgeSource && (
                    <p>
                      在任一已启用来源上选择“采集并学习”，运行进度会持续显示在这里。
                    </p>
                  )}
                </div>
                {knowledgeEvents.length === 0 && (
                  <div className="compact-empty">
                    <p>触发“采集并学习”后，这里会持续显示每个阶段。</p>
                  </div>
                )}
                {knowledgeEvents.length > 0 && (
                  <ol className="event-list">
                    {knowledgeEvents.slice(-knowledgeEventLimit).map((event) => (
                      <li key={event.event_id}>
                        <span className="event-sequence">
                          {String(event.sequence).padStart(2, "0")}
                        </span>
                        <div>
                          <div className="event-title">
                            <strong>
                              {INGESTION_EVENT_LABELS[event.type] ??
                                event.type}
                            </strong>
                            <time dateTime={event.timestamp}>
                              {formatTime(event.timestamp)}
                            </time>
                          </div>
                          <p>{summarizeKnowledgeIngestionEvent(event)}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </div>
          </section>
        </>
      )}

      {page === "codeKnowledge" && (
        <>
          <section className="page-intro">
            <div>
              <p className="eyebrow">CODE KNOWLEDGE GRAPH</p>
              <h1>代码知识</h1>
              <p>查看符号、调用、依赖和代码文档关联的可验证事实。</p>
            </div>
            <div className="page-metric">
              <span>已识别符号</span>
              <strong>{codeKnowledgeSummary?.symbols ?? 0}</strong>
            </div>
          </section>
          <section
            className="code-knowledge-console panel page-panel"
            aria-label="代码知识治理"
          >
            <div className="section-heading">
              <div>
                <p className="section-index">STRUCTURAL INDEX</p>
                <h2>代码事实浏览器</h2>
              </div>
              <span className="status status-completed">
                AST 与语义检索协同
              </span>
            </div>
            <div className="code-summary-grid">
              <article>
                <span>符号</span>
                <strong>{codeKnowledgeSummary?.symbols ?? 0}</strong>
              </article>
              <article>
                <span>关系</span>
                <strong>{codeKnowledgeSummary?.relations ?? 0}</strong>
              </article>
              <article>
                <span>文档关联</span>
                <strong>{codeKnowledgeSummary?.document_links ?? 0}</strong>
              </article>
              <article>
                <span>待解析关系</span>
                <strong>
                  {codeKnowledgeSummary?.unresolved_relations ?? 0}
                </strong>
              </article>
            </div>
            <form
              className="code-search"
              onSubmit={(event) => {
                event.preventDefault();
                refreshCodeKnowledge(codeSearch, codeKind);
              }}
            >
              <label>
                <span>项目</span>
                <select
                  aria-label="代码知识项目"
                  value={projectId}
                  onChange={(event) => {
                    setProjectId(event.target.value);
                    setSelectedCodeSymbol(null);
                  }}
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name} · {project.code}
                    </option>
                  ))}
                </select>
              </label>
              <label className="code-search-query">
                <span>符号、限定名或路径</span>
                <input
                  aria-label="搜索代码符号"
                  value={codeSearch}
                  onChange={(event) => setCodeSearch(event.target.value)}
                  placeholder="例如 search_customer 或 src/service.py"
                />
              </label>
              <label>
                <span>类型</span>
                <select
                  aria-label="代码符号类型"
                  value={codeKind}
                  onChange={(event) => setCodeKind(event.target.value)}
                >
                  <option value="">全部类型</option>
                  {Object.keys(codeKnowledgeSummary?.kinds ?? {}).map(
                    (kind) => (
                      <option key={kind} value={kind}>
                        {kind}
                      </option>
                    ),
                  )}
                </select>
              </label>
              <button type="submit" disabled={codeLoading || !projectId}>
                {codeLoading ? "读取中" : "检索事实"}
              </button>
            </form>
            <div className="code-browser">
              <section className="code-symbol-list" aria-label="代码符号列表">
                <div className="source-section-title">
                  <h3>符号索引</h3>
                  <span>{codeSymbols.length} 条</span>
                </div>
                {codeSymbols.length === 0 && (
                  <div className="compact-empty">
                    <p>当前项目尚无代码符号，请先完成知识采集。</p>
                  </div>
                )}
                {codeSymbols.map((symbol) => (
                  <button
                    type="button"
                    className={
                      selectedCodeSymbol?.id === symbol.id
                        ? "code-symbol-row is-selected"
                        : "code-symbol-row"
                    }
                    key={symbol.id}
                    onClick={() => selectCodeSymbol(symbol)}
                  >
                    <span>{symbol.kind} · {symbol.language}</span>
                    <strong>{symbol.name}</strong>
                    <small>
                      {symbol.path}:{symbol.start_line}
                    </small>
                  </button>
                ))}
              </section>
              <section className="code-detail" aria-label="代码符号详情">
                {!selectedCodeSymbol && (
                  <div className="compact-empty">
                    <p>选择符号后查看调用关系、解析证据和关联文档。</p>
                  </div>
                )}
                {selectedCodeSymbol && (
                  <>
                    <header>
                      <span>
                        {selectedCodeSymbol.kind} ·{" "}
                        {selectedCodeSymbol.parser ?? "unknown"}
                      </span>
                      <h3>{selectedCodeSymbol.qualified_name}</h3>
                      <code>{selectedCodeSymbol.signature}</code>
                      <small>
                        {selectedCodeSymbol.path}:
                        {selectedCodeSymbol.start_line} 至{" "}
                        {selectedCodeSymbol.end_line}
                      </small>
                    </header>
                    <div className="code-fact-group">
                      <h4>调用与依赖</h4>
                      {(selectedCodeSymbol.outgoing_relations ?? []).length ===
                        0 && <p>没有已记录的出向关系。</p>}
                      {(selectedCodeSymbol.outgoing_relations ?? []).map(
                        (relation) => (
                          <article key={relation.id}>
                            <span>{relation.relation_type}</span>
                            <strong>{relation.target_name}</strong>
                            <small>
                              {relation.target_symbol_id
                                ? "已解析到代码符号"
                                : "保留外部或待解析目标"}
                              {" · "}
                              置信度 {relation.confidence.toFixed(2)}
                            </small>
                          </article>
                        ),
                      )}
                    </div>
                    <div className="code-fact-group">
                      <h4>关联文档</h4>
                      {(selectedCodeSymbol.document_links ?? []).length ===
                        0 && <p>尚无具有直接证据的文档关联。</p>}
                      {(selectedCodeSymbol.document_links ?? []).map((link) => (
                        <article key={link.id}>
                          <span>{link.link_type}</span>
                          <strong>{link.path}</strong>
                          <small>
                            {String(link.evidence.method ?? "deterministic")}
                            {" · "}
                            评分 {link.score.toFixed(2)}
                          </small>
                        </article>
                      ))}
                    </div>
                  </>
                )}
              </section>
            </div>
          </section>
        </>
      )}

      {page === "memory" && (
        <>
          <section className="page-intro">
            <div>
              <p className="eyebrow">MEMORY GOVERNANCE</p>
              <h1>长期记忆</h1>
              <p>审查由任务产生的记忆候选，并控制客户或产品范围。</p>
            </div>
            <div className="page-metric">
              <span>待治理</span>
              <strong>
                {
                  memoryCandidates.filter(
                    (item) => item.status === "proposed",
                  ).length
                }
              </strong>
            </div>
          </section>
          <section
            className="memory-console panel page-panel"
            aria-label="长期记忆治理"
          >
            <div className="section-heading">
              <div>
                <p className="section-index">MEMORY</p>
                <h2>记忆候选</h2>
              </div>
              <span>人工治理边界</span>
            </div>
            <div className="memory-list">
              {memoryCandidates.length === 0 && (
                <div className="memory-empty compact-empty">
                  <p>尚无记忆候选。</p>
                </div>
              )}
              {memoryCandidates.map((candidate) => (
                <article className="knowledge-item" key={candidate.id}>
                  <strong>{candidate.title}</strong>
                  <span>
                    {candidate.kind} · {candidate.scope} · {candidate.status}
                  </span>
                  <small>{candidate.content}</small>
                  {candidate.status === "proposed" && (
                    <div className="candidate-actions">
                      <button
                        type="button"
                        onClick={() =>
                          handleCandidateAction(candidate.id, "approve")
                        }
                      >
                        批准
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          handleCandidateAction(candidate.id, "reject")
                        }
                      >
                        拒绝
                      </button>
                    </div>
                  )}
                  {candidate.status === "approved" &&
                    candidate.scope === "tenant" && (
                      <button
                        type="button"
                        onClick={() =>
                          handleCandidateAction(candidate.id, "promote")
                        }
                      >
                        提升为产品知识
                      </button>
                    )}
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      {page === "capabilities" && (
        <>
          <section className="page-intro">
            <div>
              <p className="eyebrow">CAPABILITY GOVERNANCE</p>
              <h1>能力治理</h1>
              <p>查看 Skill、Tool、Validator、评测状态和标准控制映射。</p>
            </div>
            <div className="page-metric">
              <span>已登记能力</span>
              <strong>{capabilities.length}</strong>
            </div>
          </section>
          <section
            className="capability-console panel page-panel"
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
        </>
      )}

      {page === "conversation" && (
        <>
          <section className="page-intro page-intro-conversation">
            <div>
              <p className="eyebrow">API TEST CONSOLE</p>
              <h1>API 调用测试台</h1>
              <p>
                这里通过正式任务 API 发起测试调用。每轮任务会进入统一审计流，
                外部系统无需依赖本页面。
              </p>
            </div>
            <div className="hero-status">
              <span className="runtime-dot" aria-hidden="true" />
              CAG 持续会话
            </div>
          </section>
          <section className="workspace-grid conversation-grid">
        <section className="conversation-panel panel">
          <div className="section-heading">
            <div>
              <p className="section-index">01</p>
              <h2>连续对话测试</h2>
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
                  {turn.intermediateMessages.length > 0 && (
                    <details className="message-intermediate">
                      <summary>
                        中间回答 · {turn.intermediateMessages.length} 条
                      </summary>
                      <div className="message-intermediate-list">
                        {turn.intermediateMessages.map((message) => (
                          <article key={message.id}>
                            <span>{message.role}</span>
                            <p>{message.text}</p>
                          </article>
                        ))}
                      </div>
                    </details>
                  )}
                  {turn.answer && (
                    <div className="message-final">
                      <strong>最终结果</strong>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.answer}
                      </ReactMarkdown>
                    </div>
                  )}
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
        </>
      )}
    </main>
  );
}
