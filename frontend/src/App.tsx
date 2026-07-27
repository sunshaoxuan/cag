import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  Conversation,
  conversationEventsUrl,
  createConversation,
  createTask,
  getTask,
  listProjects,
  Project,
  Task,
  TaskEvent,
} from "./api";
import "./styles.css";

const EVENT_TYPES = [
  "task.created",
  "task.started",
  "workspace.preparing",
  "workspace.ready",
  "runtime.connected",
  "runtime.thread",
  "agent.message",
  "agent.plan",
  "skill.selected",
  "tool.called",
  "tool.completed",
  "command.requested",
  "command.started",
  "command.output",
  "command.completed",
  "file.read",
  "file.changed",
  "test.started",
  "test.completed",
  "approval.requested",
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
  "runtime.connected": "本机 Codex 已连接",
  "runtime.thread": "Codex 会话已连接",
  "agent.plan": "Agent 已生成计划",
  "agent.message": "Agent 消息",
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

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function summarizeEvent(event: TaskEvent): string {
  if (event.type === "agent.message") {
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

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [prompt, setPrompt] = useState("");
  const [task, setTask] = useState<Task | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projectId, projects],
  );
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

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">CODEX CONVERSATION CONTROL</p>
          <h1>Agent Gateway</h1>
          <p className="hero-copy">
            CAG 维护对话、SSE 事件和断线续传，本机 Codex 在独立工作区中完成每一轮。
          </p>
        </div>
        <div className="runtime-chip">
          <span className="runtime-dot" aria-hidden="true" />
          CAG 持续会话
        </div>
      </header>

      <section className="workspace-grid conversation-grid">
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

          {events.length === 0 && (
            <div className="empty-state">
              <div className="empty-mark" aria-hidden="true">
                SSE
              </div>
              <h3>等待会话事件</h3>
              <p>CAG 将在这里持续显示各轮工作区、Agent、命令和测试事件。</p>
            </div>
          )}

          {events.length > 0 && (
            <ol className="event-list">
              {events.map((event) => (
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
