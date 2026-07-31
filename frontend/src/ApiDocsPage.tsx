import { useEffect, useState } from "react";

import { apiUrl, getQueueStatus, QueueStatus } from "./api";

type Example = {
  title: string;
  description: string;
  language: string;
  code: string;
};

const EXAMPLES: Example[] = [
  {
    title: "创建持续会话",
    description: "保存返回的 conversation.id，后续任务可复用同一上下文。",
    language: "PowerShell",
    code: [
      "$headers = @{",
      '  "Content-Type" = "application/json"',
      '  "X-CAG-Client-ID" = "oneops"',
      '  "X-Request-ID" = [guid]::NewGuid().ToString()',
      "}",
      "$conversation = Invoke-RestMethod `",
      "  -Method Post `",
      '  -Uri "$baseUrl/api/v1/conversations" `',
      "  -Headers $headers `",
      "  -Body (@{",
      '    project_id = "<project-id>"',
      '    title = "生产问题调查"',
      "  } | ConvertTo-Json)",
    ].join("\n"),
  },
  {
    title: "提交可接续任务",
    description: "Idempotency-Key 防止调用方重试时重复创建任务。",
    language: "curl",
    code: `curl -X POST "$BASE_URL/api/v1/tasks" \\
  -H "Content-Type: application/json" \\
  -H "X-CAG-Client-ID: oneops" \\
  -H "X-Request-ID: $(uuidgen)" \\
  -H "Idempotency-Key: task-20260729-001" \\
  -d '{
    "project_id": "<project-id>",
    "conversation_id": "<conversation-id>",
    "prompt": "调查告警并给出验证结果",
    "knowledge_mode": "assist"
  }'`,
  },
  {
    title: "监听 SSE 任务流",
    description: "浏览器会自动重连，服务端支持 Last-Event-ID 接续。",
    language: "JavaScript",
    code: `const stream = new EventSource(
  \`\${baseUrl}/api/v1/tasks/\${taskId}/events?follow=true\`
);
[
  "task.started",
  "agent.message",
  "task.completed",
  "task.failed"
].forEach((type) => {
  stream.addEventListener(type, (message) => {
    const event = JSON.parse(message.data);
    console.log(event.sequence, event.type, event.data);
  });
});`,
  },
  {
    title: "查看队列与工作器",
    description: "PostgreSQL 保存任务真相，Redis 用于跨进程即时唤醒。",
    language: "PowerShell",
    code: [
      "$queue = Invoke-RestMethod `",
      "  -Method Get `",
      '  -Uri "$baseUrl/api/v1/queue/status"',
      "$queue.queues",
      "$queue.workers",
      "$queue.redis",
    ].join("\n"),
  },
  {
    title: "启动知识学习并监听进度",
    description: "学习任务进入独立 knowledge 队列，事件流提供全程进度。",
    language: "JavaScript",
    code: `const ingestion = await fetch(
  \`\${baseUrl}/api/v1/knowledge/sources/\${sourceId}/ingest\`,
  { method: "POST" }
).then((response) => response.json());

const progress = new EventSource(
  \`\${baseUrl}/api/v1/knowledge/ingestions/\${ingestion.id}/events?follow=true\`
);
progress.addEventListener("knowledge.collection.progress", (message) => {
  console.log(JSON.parse(message.data));
});`,
  },
  {
    title: "查询知识文件资产",
    description: "检查每个条目的处理模式、状态、大小和策略原因。",
    language: "PowerShell",
    code: [
      "$assets = Invoke-RestMethod `",
      "  -Method Get `",
      '  -Uri "$baseUrl/api/v1/knowledge/sources/$sourceId/entries?limit=100"',
      "$assets.items | Select-Object `",
      "  relative_path, processing_mode, status, file_size, reason_code",
    ].join("\n"),
  },
  {
    title: "提交运行失败到问题中心",
    description: "调用方提供稳定事件ID，重复上报会保留幂等并按指纹归并。",
    language: "curl",
    code: `curl -X POST "$BASE_URL/api/v1/operations/issues/intake" \\
  -H "Content-Type: application/json" \\
  -d '{
    "project_reference": "cag",
    "source_type": "external_connector",
    "source_id": "upds-share",
    "title": "Network share authentication failed",
    "error_type": "CredentialFailure",
    "error_message": "Authentication failed",
    "severity": "high",
    "external_event_id": "connector-event-20260731-001",
    "evidence": {"attempt": 3}
  }'`,
  },
  {
    title: "审批AI改进方案",
    description: "内部问题批准后创建受控改进分支任务，外部问题转为等待管理员处理。",
    language: "PowerShell",
    code: [
      "$approval = @{",
      '  note = "批准隔离分支实施并执行回归测试"',
      "} | ConvertTo-Json",
      "Invoke-RestMethod `",
      "  -Method Post `",
      '  -Uri "$baseUrl/api/v1/operations/issues/$issueId/approve" `',
      '  -Headers @{"X-CAG-Admin-Token" = $env:CAG_OPERATIONS_ADMIN_TOKEN; "X-CAG-Admin-Identity" = "gateway-admin"} `',
      "  -ContentType 'application/json; charset=utf-8' `",
      "  -Body $approval",
    ].join("\n"),
  },
  {
    title: "分页读取问题处理时间线",
    description:
      "详情接口保持轻量，完整审计事件通过事件序号分页读取。使用返回的 next_before_sequence 继续向前翻页。",
    language: "PowerShell",
    code: [
      "$page = Invoke-RestMethod `",
      "  -Method Get `",
      '  -Uri "$baseUrl/api/v1/operations/issues/$issueId/events?limit=100"',
      "$page.items",
      "$older = Invoke-RestMethod `",
      "  -Method Get `",
      '  -Uri "$baseUrl/api/v1/operations/issues/$issueId/events?limit=100&before_sequence=$($page.next_before_sequence)"',
    ].join("\n"),
  },
  {
    title: "重新提交可恢复的问题",
    description:
      "已关闭、已拒绝、验证完成、已移交、分诊失败和方案待修订可以进入新一轮分诊。",
    language: "PowerShell",
    code: [
      '$body = @{reason = "证据和工具已经更新，请重新评估"} | ConvertTo-Json',
      "Invoke-RestMethod `",
      "  -Method Post `",
      '  -Uri "$baseUrl/api/v1/operations/issues/$issueId/reopen" `',
      '  -Headers @{"X-CAG-Admin-Token" = $env:CAG_OPERATIONS_ADMIN_TOKEN; "X-CAG-Admin-Identity" = "gateway-admin"} `',
      "  -ContentType 'application/json; charset=utf-8' `",
      "  -Body $body",
    ].join("\n"),
  },
];

function countFor(
  status: QueueStatus | null,
  queueName: string,
  itemStatus: string,
): number {
  return (
    status?.queues.find((queue) => queue.name === queueName)?.counts[
      itemStatus
    ] ?? 0
  );
}

export default function ApiDocsPage() {
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = () => {
      getQueueStatus()
        .then((value) => {
          if (!active) return;
          setQueueStatus(value);
          setQueueError(null);
        })
        .catch((reason: Error) => {
          if (active) setQueueError(reason.message);
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 5_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function copyExample(example: Example) {
    await navigator.clipboard.writeText(example.code);
    setCopied(example.title);
    window.setTimeout(() => setCopied(null), 1_500);
  }

  return (
    <>
      <section className="page-intro page-intro-api">
        <div>
          <p className="eyebrow">ONLINE API REFERENCE</p>
          <h1>API 在线文档</h1>
          <p>
            面向集成开发与运行维护的调用入口、请求约定、SSE 接续方式和
            PostgreSQL 加 Redis 队列状态。
          </p>
        </div>
        <div className="api-doc-links">
          <a className="button button-outline" href={apiUrl("/docs")}>
            交互式 OpenAPI
          </a>
          <a className="button button-primary" href={apiUrl("/openapi.json")}>
            下载规范
          </a>
        </div>
      </section>

      <section className="api-runtime panel page-panel" aria-label="队列实时状态">
        <div className="section-heading">
          <div>
            <p className="section-index">RUNTIME</p>
            <h2>队列实时状态</h2>
          </div>
          <span
            className={`status ${
              queueStatus?.running ? "status-completed" : "status-failed"
            }`}
          >
            {queueStatus?.running ? "工作器运行中" : "正在连接"}
          </span>
        </div>
        <div className="api-runtime-grid">
          <article>
            <span>交互任务等待</span>
            <strong>{countFor(queueStatus, "interactive", "queued")}</strong>
            <small>
              {queueStatus?.configured_workers.interactive ?? 0} 个工作器
            </small>
          </article>
          <article>
            <span>知识学习等待</span>
            <strong>{countFor(queueStatus, "knowledge", "queued")}</strong>
            <small>
              {queueStatus?.configured_workers.knowledge ?? 0} 个工作器
            </small>
          </article>
          <article>
            <span>问题处理等待</span>
            <strong>{countFor(queueStatus, "operations", "queued")}</strong>
            <small>
              {queueStatus?.configured_workers.operations ?? 0} 个工作器
            </small>
          </article>
          <article>
            <span>正在执行</span>
            <strong>
              {countFor(queueStatus, "interactive", "leased") +
                countFor(queueStatus, "knowledge", "leased") +
                countFor(queueStatus, "operations", "leased")}
            </strong>
            <small>{queueStatus?.workers.length ?? 0} 个活跃工作器</small>
          </article>
          <article>
            <span>Redis 唤醒</span>
            <strong>{queueStatus?.redis.connected ? "已连接" : "轮询保障"}</strong>
            <small>任务记录以 PostgreSQL 为准</small>
          </article>
        </div>
        {queueError && <p className="error-banner">{queueError}</p>}
      </section>

      <section className="api-contract-grid">
        <article className="panel api-contract">
          <p className="section-index">REQUEST CONTRACT</p>
          <h2>调用约定</h2>
          <dl>
            <div>
              <dt>Base URL</dt>
              <dd>http://gateway-host:8000</dd>
            </div>
            <div>
              <dt>内容类型</dt>
              <dd>application/json</dd>
            </div>
            <div>
              <dt>调用方</dt>
              <dd>X-CAG-Client-ID</dd>
            </div>
            <div>
              <dt>请求跟踪</dt>
              <dd>X-Request-ID</dd>
            </div>
            <div>
              <dt>幂等控制</dt>
              <dd>Idempotency-Key</dd>
            </div>
            <div>
              <dt>会话标识</dt>
              <dd>conversation.id</dd>
            </div>
          </dl>
        </article>
        <article className="panel api-contract">
          <p className="section-index">EVENT DELIVERY</p>
          <h2>SSE 接续规则</h2>
          <ul>
            <li>每个任务与知识学习流程都有独立事件地址。</li>
            <li>事件包含稳定 event_id 和递增 sequence。</li>
            <li>客户端通过 Last-Event-ID 或 after_sequence 接续。</li>
            <li>同一 conversation 内任务按提交顺序串行执行。</li>
            <li>不同 conversation 与知识队列可并行执行。</li>
          </ul>
        </article>
      </section>

      <section className="api-examples" aria-label="API 调用范例">
        <div className="section-heading">
          <div>
            <p className="section-index">COPY AND RUN</p>
            <h2>调用范例</h2>
          </div>
          <span>PowerShell · curl · JavaScript</span>
        </div>
        <div className="api-example-grid">
          {EXAMPLES.map((example) => (
            <article className="panel api-example" key={example.title}>
              <header>
                <div>
                  <small>{example.language}</small>
                  <h3>{example.title}</h3>
                </div>
                <button
                  className="button button-ghost"
                  type="button"
                  onClick={() => copyExample(example)}
                >
                  {copied === example.title ? "已复制" : "复制"}
                </button>
              </header>
              <p>{example.description}</p>
              <pre>
                <code>{example.code}</code>
              </pre>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
