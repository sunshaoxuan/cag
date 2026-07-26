import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  createTask,
  getTask,
  listProjects,
  Project,
  Task,
  TaskEvent,
  taskEventsUrl,
} from "./api";
import "./styles.css";

const EVENT_TYPES = [
  "task.created",
  "task.started",
  "workspace.preparing",
  "workspace.ready",
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
  "task.created": "任务已创建",
  "task.started": "任务已启动",
  "workspace.preparing": "正在准备独立工作区",
  "workspace.ready": "工作区已就绪",
  "agent.plan": "Agent 已生成计划",
  "agent.message": "Agent 消息",
  "test.completed": "验证已完成",
  "task.completed": "任务已完成",
  "task.failed": "任务执行失败",
  "task.cancelled": "任务已取消",
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
  if (event.type === "test.completed") {
    return `${String(event.data.command ?? "验证")}：${String(
      event.data.status ?? "",
    )}`;
  }
  return EVENT_LABELS[event.type] ?? event.type;
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [task, setTask] = useState<Task | null>(null);
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

  function connectEvents(createdTask: Task) {
    sourceRef.current?.close();
    const source = new EventSource(taskEventsUrl(createdTask.id));
    sourceRef.current = source;

    const handleEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as TaskEvent;
      setEvents((current) => {
        if (current.some((item) => item.sequence === event.sequence)) {
          return current;
        }
        return [...current, event].sort((a, b) => a.sequence - b.sequence);
      });

      if (
        event.type === "task.completed" ||
        event.type === "task.failed" ||
        event.type === "task.cancelled"
      ) {
        source.close();
        getTask(createdTask.id)
          .then(setTask)
          .catch((reason: Error) => setError(reason.message));
      }
    };

    EVENT_TYPES.forEach((eventType) => {
      source.addEventListener(eventType, handleEvent as EventListener);
    });
    source.onerror = () => {
      source.close();
      getTask(createdTask.id)
        .then(setTask)
        .catch((reason: Error) => setError(reason.message));
    };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId || !prompt.trim() || submitting) return;

    setSubmitting(true);
    setError(null);
    setEvents([]);
    setTask(null);
    try {
      const createdTask = await createTask(projectId, prompt.trim());
      setTask(createdTask);
      connectEvents(createdTask);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "任务提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  const isTerminal = task
    ? ["completed", "failed", "cancelled"].includes(task.status)
    : false;

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">CODEX TASK CONTROL</p>
          <h1>Agent Gateway</h1>
          <p className="hero-copy">
            选择项目，描述目标。Gateway 将准备独立工作区并持续呈现执行事件。
          </p>
        </div>
        <div className="runtime-chip">
          <span className="runtime-dot" aria-hidden="true" />
          本地 Codex 订阅架构
        </div>
      </header>

      <section className="workspace-grid">
        <form className="task-composer panel" onSubmit={handleSubmit}>
          <div className="section-heading">
            <div>
              <p className="section-index">01</p>
              <h2>创建任务</h2>
            </div>
            <span>Phase 2</span>
          </div>

          <label htmlFor="project">项目</label>
          <select
            id="project"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            disabled={loadingProjects || submitting}
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

          <label htmlFor="prompt">任务 Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="例如：检查当前构建失败的原因，修复能够确认的问题并运行测试。"
            rows={8}
            disabled={submitting}
          />
          <div className="composer-footer">
            <span>{prompt.trim().length.toLocaleString()} 字</span>
            <button
              type="submit"
              disabled={!projectId || !prompt.trim() || submitting}
            >
              {submitting ? "正在提交" : "开始执行"}
            </button>
          </div>
          {error && <p className="error-banner">{error}</p>}
        </form>

        <section className="execution-panel panel" aria-live="polite">
          <div className="section-heading">
            <div>
              <p className="section-index">02</p>
              <h2>执行过程</h2>
            </div>
            {task && (
              <span className={`status status-${task.status}`}>
                {STATUS_LABELS[task.status] ?? task.status}
              </span>
            )}
          </div>

          {!task && (
            <div className="empty-state">
              <div className="empty-mark" aria-hidden="true">
                AG
              </div>
              <h3>等待新任务</h3>
              <p>提交后将在这里显示工作区、Agent、命令和测试事件。</p>
            </div>
          )}

          {task && (
            <>
              <div className="task-summary">
                <div>
                  <span>任务</span>
                  <strong>{task.id.slice(0, 8)}</strong>
                </div>
                <div>
                  <span>项目</span>
                  <strong>{task.project_code}</strong>
                </div>
                <div>
                  <span>工作区</span>
                  <strong>{task.workspace_id ? "独立" : "准备中"}</strong>
                </div>
              </div>

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
                {!isTerminal && (
                  <li className="event-pending">
                    <span className="event-sequence pulse" />
                    <div>
                      <strong>正在等待下一事件</strong>
                    </div>
                  </li>
                )}
              </ol>
            </>
          )}
        </section>
      </section>

      {task?.final_report && (
        <section className="result-panel panel">
          <div className="section-heading">
            <div>
              <p className="section-index">03</p>
              <h2>最终报告</h2>
            </div>
            <span className="status status-completed">验证完成</span>
          </div>
          <p className="result-summary">{task.final_report.summary}</p>
          <div className="result-grid">
            <div>
              <h3>验证</h3>
              {task.final_report.validation.map((validation) => (
                <p key={validation.command} className="validation-row">
                  <span>{validation.command}</span>
                  <strong>{validation.status}</strong>
                </p>
              ))}
            </div>
            <div>
              <h3>提醒</h3>
              <ul>
                {task.final_report.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
