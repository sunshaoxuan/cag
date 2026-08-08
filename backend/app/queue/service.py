from __future__ import annotations

import os
import socket
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.database import Database
from app.models import (
    KnowledgeIngestion,
    KnowledgeIngestionEvent,
    KnowledgeSource,
    OperationalIssue,
    OperationalIssueStatus,
    QueueItem,
    QueueItemStatus,
    QueueWorker,
    Task,
    TaskStatus,
)
from app.models.base import utc_now
from app.services.task_service import TaskService


ACTIVE_TASK_STATUSES = {
    TaskStatus.PREPARING,
    TaskStatus.RUNNING,
    TaskStatus.WAITING_APPROVAL,
}


class QueueService:
    def __init__(
        self,
        *,
        database: Database,
        task_service: TaskService,
        lease_seconds: int,
    ) -> None:
        self._database = database
        self._task_service = task_service
        self._lease_seconds = lease_seconds

    @staticmethod
    def add_task_item(session, task: Task) -> QueueItem:
        is_extraction = task.trigger_source == "knowledge_extraction"
        item = QueueItem(
            queue_name="extraction" if is_extraction else "interactive",
            job_type=(
                "customer_knowledge_extraction"
                if is_extraction
                else "agent_task"
            ),
            task_id=task.id,
            project_id=task.project_id,
            conversation_id=task.conversation_id,
            client_id=task.client_id,
            priority=120 if is_extraction else 100,
        )
        session.add(item)
        session.flush()
        return item

    @staticmethod
    def add_ingestion_item(
        session,
        ingestion: KnowledgeIngestion,
        source: KnowledgeSource,
    ) -> QueueItem:
        item = QueueItem(
            queue_name="knowledge",
            job_type="knowledge_ingestion",
            ingestion_id=ingestion.id,
            project_id=source.project_id,
            client_id="knowledge-scheduler"
            if ingestion.trigger == "scheduled"
            else "knowledge-console",
            priority=20 if ingestion.trigger == "scheduled" else 40,
            max_attempts=2,
        )
        session.add(item)
        session.flush()
        return item

    def bootstrap(self) -> dict[str, int]:
        now = utc_now()
        counts = {
            "tasks_enqueued": 0,
            "ingestions_enqueued": 0,
            "issues_enqueued": 0,
            "expired_requeued": 0,
        }
        with self._database.session_factory() as session:
            task_rows = list(
                session.scalars(
                    select(Task)
                    .outerjoin(QueueItem, QueueItem.task_id == Task.id)
                    .where(
                        QueueItem.id.is_(None),
                        ~Task.status.in_(TaskStatus.TERMINAL),
                    )
                    .order_by(Task.created_at, Task.id)
                )
            )
            for task in task_rows:
                if task.status in ACTIVE_TASK_STATUSES:
                    task.status = TaskStatus.QUEUED
                    task.error = None
                    task.completed_at = None
                    self._task_service.append_event(
                        session,
                        task=task,
                        event_type="task.requeued",
                        data={"reason": "durable_queue_bootstrap"},
                    )
                self.add_task_item(session, task)
                counts["tasks_enqueued"] += 1

            inconsistent_task_items = list(
                session.execute(
                    select(QueueItem, Task)
                    .join(Task, Task.id == QueueItem.task_id)
                    .where(
                        QueueItem.status.in_(QueueItemStatus.TERMINAL),
                        ~Task.status.in_(TaskStatus.TERMINAL),
                    )
                    .with_for_update()
                )
            )
            for item, task in inconsistent_task_items:
                task.status = TaskStatus.QUEUED
                task.error = None
                task.completed_at = None
                self._task_service.append_event(
                    session,
                    task=task,
                    event_type="task.requeued",
                    data={"reason": "durable_queue_bootstrap"},
                )
                self._reset_terminal_item(item, now=now)
                counts["tasks_enqueued"] += 1

            ingestion_rows = list(
                session.execute(
                    select(KnowledgeIngestion, KnowledgeSource)
                    .join(
                        KnowledgeSource,
                        KnowledgeSource.id == KnowledgeIngestion.source_id,
                    )
                    .outerjoin(
                        QueueItem,
                        QueueItem.ingestion_id == KnowledgeIngestion.id,
                    )
                    .where(
                        QueueItem.id.is_(None),
                        KnowledgeIngestion.status.in_(("queued", "running")),
                    )
                    .order_by(
                        KnowledgeIngestion.created_at,
                        KnowledgeIngestion.id,
                    )
                )
            )
            for ingestion, source in ingestion_rows:
                if ingestion.status == "running":
                    ingestion.status = "queued"
                    ingestion.error = None
                    ingestion.completed_at = None
                    self._append_ingestion_event(
                        session,
                        ingestion,
                        "knowledge.ingestion.requeued",
                        {"reason": "durable_queue_bootstrap"},
                    )
                self.add_ingestion_item(session, ingestion, source)
                counts["ingestions_enqueued"] += 1

            inconsistent_ingestion_items = list(
                session.execute(
                    select(QueueItem, KnowledgeIngestion)
                    .join(
                        KnowledgeIngestion,
                        KnowledgeIngestion.id == QueueItem.ingestion_id,
                    )
                    .where(
                        QueueItem.status.in_(QueueItemStatus.TERMINAL),
                        KnowledgeIngestion.status.in_(("queued", "running")),
                    )
                    .with_for_update()
                )
            )
            for item, ingestion in inconsistent_ingestion_items:
                ingestion.status = "queued"
                ingestion.error = None
                ingestion.completed_at = None
                self._append_ingestion_event(
                    session,
                    ingestion,
                    "knowledge.ingestion.requeued",
                    {"reason": "durable_queue_bootstrap"},
                )
                self._reset_terminal_item(item, now=now)
                counts["ingestions_enqueued"] += 1

            issue_rows = list(
                session.scalars(
                    select(OperationalIssue).where(
                        OperationalIssue.status.in_(
                            (
                                OperationalIssueStatus.DETECTED,
                                OperationalIssueStatus.TRIAGING,
                                OperationalIssueStatus.EVALUATING,
                            )
                        ),
                        ~exists(
                            select(QueueItem.id).where(
                                QueueItem.issue_id == OperationalIssue.id,
                                QueueItem.status.in_(
                                    (
                                        QueueItemStatus.QUEUED,
                                        QueueItemStatus.LEASED,
                                    )
                                ),
                            )
                        ),
                    )
                )
            )
            for issue in issue_rows:
                issue.status = (
                    OperationalIssueStatus.EVALUATING
                    if issue.evaluation_status in {"queued", "running"}
                    else OperationalIssueStatus.DETECTED
                )
                session.add(
                    QueueItem(
                        queue_name="operations",
                        job_type=(
                            "operational_evaluation"
                            if issue.status == OperationalIssueStatus.EVALUATING
                            else "operational_triage"
                        ),
                        issue_id=issue.id,
                        project_id=issue.project_id,
                        client_id="cag-self-operations",
                        priority=100,
                    )
                )
                counts["issues_enqueued"] += 1

            expired = list(
                session.scalars(
                    select(QueueItem)
                    .where(
                        QueueItem.status == QueueItemStatus.LEASED,
                        QueueItem.lease_expires_at <= now,
                    )
                    .with_for_update(skip_locked=True)
                )
            )
            for item in expired:
                self._requeue_locked(
                    session,
                    item,
                    reason="worker_lease_expired",
                )
                counts["expired_requeued"] += 1
            session.commit()
        return counts

    def claim_next(
        self,
        *,
        queue_name: str,
        worker_key: str,
    ) -> QueueItem | None:
        now = utc_now()
        earlier = aliased(QueueItem)
        earlier_in_conversation = exists(
            select(earlier.id).where(
                earlier.conversation_id == QueueItem.conversation_id,
                earlier.status.in_(
                    (QueueItemStatus.QUEUED, QueueItemStatus.LEASED)
                ),
                or_(
                    earlier.created_at < QueueItem.created_at,
                    and_(
                        earlier.created_at == QueueItem.created_at,
                        earlier.id < QueueItem.id,
                    ),
                ),
            )
        )
        with self._database.session_factory() as session:
            expired = list(
                session.scalars(
                    select(QueueItem)
                    .where(
                        QueueItem.queue_name == queue_name,
                        QueueItem.status == QueueItemStatus.LEASED,
                        QueueItem.lease_expires_at <= now,
                    )
                    .with_for_update(skip_locked=True)
                )
            )
            for expired_item in expired:
                self._requeue_locked(
                    session,
                    expired_item,
                    reason="worker_lease_expired",
                )
            if expired:
                session.flush()
            item = session.scalar(
                select(QueueItem)
                .where(
                    QueueItem.queue_name == queue_name,
                    QueueItem.status == QueueItemStatus.QUEUED,
                    QueueItem.available_at <= now,
                    or_(
                        QueueItem.conversation_id.is_(None),
                        ~earlier_in_conversation,
                    ),
                )
                .order_by(
                    QueueItem.priority.desc(),
                    QueueItem.created_at,
                    QueueItem.id,
                )
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if item is None:
                self.touch_worker(
                    worker_key=worker_key,
                    queue_name=queue_name,
                    status="idle",
                    session=session,
                )
                session.commit()
                return None
            item.status = QueueItemStatus.LEASED
            item.lease_owner = worker_key
            item.lease_expires_at = now + timedelta(seconds=self._lease_seconds)
            item.heartbeat_at = now
            item.attempt_count += 1
            item.error = None
            self.touch_worker(
                worker_key=worker_key,
                queue_name=queue_name,
                status="working",
                current_item_id=item.id,
                session=session,
            )
            session.commit()
            session.refresh(item)
            return item

    def heartbeat(self, *, item_id: str, worker_key: str) -> bool:
        now = utc_now()
        with self._database.session_factory() as session:
            item = session.scalar(
                select(QueueItem)
                .where(
                    QueueItem.id == item_id,
                    QueueItem.status == QueueItemStatus.LEASED,
                    QueueItem.lease_owner == worker_key,
                )
                .with_for_update()
            )
            if item is None:
                return True
            item.heartbeat_at = now
            item.lease_expires_at = now + timedelta(
                seconds=self._lease_seconds
            )
            self.touch_worker(
                worker_key=worker_key,
                queue_name=item.queue_name,
                status="working",
                current_item_id=item.id,
                session=session,
            )
            cancel_requested = item.cancel_requested_at is not None
            session.commit()
            return cancel_requested

    def finish(self, *, item_id: str, worker_key: str) -> str:
        now = utc_now()
        with self._database.session_factory() as session:
            item = session.get(QueueItem, item_id)
            if item is None:
                return QueueItemStatus.FAILED
            if (
                item.cancel_requested_at is not None
                and self._cancellation_precedes_completion(session, item)
            ):
                self._cancel_locked(session, item, reason="cancel_requested")
            else:
                resource_status = self._resource_status(session, item)
                if resource_status in {"completed"}:
                    item.status = QueueItemStatus.COMPLETED
                elif resource_status in {"cancelled"}:
                    item.status = QueueItemStatus.CANCELLED
                else:
                    item.status = QueueItemStatus.FAILED
                    item.error = self._resource_error(session, item)
                item.completed_at = now
                item.lease_owner = None
                item.lease_expires_at = None
                item.heartbeat_at = now
            self.touch_worker(
                worker_key=worker_key,
                queue_name=item.queue_name,
                status="idle",
                session=session,
            )
            session.commit()
            return item.status

    def abandon(
        self,
        *,
        item_id: str,
        worker_key: str,
        reason: str,
    ) -> str:
        with self._database.session_factory() as session:
            item = session.scalar(
                select(QueueItem)
                .where(
                    QueueItem.id == item_id,
                    QueueItem.lease_owner == worker_key,
                )
                .with_for_update()
            )
            if item is None:
                return QueueItemStatus.FAILED
            if item.cancel_requested_at is not None:
                self._cancel_locked(session, item, reason="cancel_requested")
            elif item.attempt_count < item.max_attempts:
                self._requeue_locked(session, item, reason=reason)
            else:
                self._fail_locked(session, item, reason=reason)
            self.touch_worker(
                worker_key=worker_key,
                queue_name=item.queue_name,
                status="idle",
                session=session,
            )
            session.commit()
            return item.status

    def request_cancel(self, item_id: str) -> str:
        with self._database.session_factory() as session:
            item = session.scalar(
                select(QueueItem)
                .where(QueueItem.id == item_id)
                .with_for_update()
            )
            if item is None:
                raise KeyError(item_id)
            if item.status in QueueItemStatus.TERMINAL:
                return item.status
            item.cancel_requested_at = utc_now()
            if item.status == QueueItemStatus.QUEUED:
                self._cancel_locked(session, item, reason="cancel_requested")
            session.commit()
            return item.status

    def status_snapshot(self) -> dict[str, Any]:
        now = utc_now()
        active_cutoff = now - timedelta(seconds=self._lease_seconds)
        with self._database.session_factory() as session:
            grouped = session.execute(
                select(
                    QueueItem.queue_name,
                    QueueItem.status,
                    func.count(QueueItem.id),
                )
                .group_by(QueueItem.queue_name, QueueItem.status)
                .order_by(QueueItem.queue_name, QueueItem.status)
            )
            queues: dict[str, dict[str, Any]] = {}
            for queue_name, status, count in grouped:
                queue = queues.setdefault(
                    str(queue_name),
                    {
                        "name": str(queue_name),
                        "counts": {},
                        "oldest_queued_at": None,
                    },
                )
                queue["counts"][str(status)] = int(count)
            for queue_name, queue in queues.items():
                oldest = session.scalar(
                    select(func.min(QueueItem.created_at)).where(
                        QueueItem.queue_name == queue_name,
                        QueueItem.status == QueueItemStatus.QUEUED,
                    )
                )
                queue["oldest_queued_at"] = (
                    oldest.isoformat() if oldest is not None else None
                )
                queue["oldest_wait_seconds"] = (
                    max(
                        0,
                        int(
                            (
                                now - self._aware_datetime(oldest)
                            ).total_seconds()
                        ),
                    )
                    if oldest is not None
                    else 0
                )
            workers = list(
                session.scalars(
                    select(QueueWorker)
                    .where(QueueWorker.heartbeat_at >= active_cutoff)
                    .order_by(QueueWorker.queue_name, QueueWorker.worker_key)
                )
            )
            return {
                "queues": list(queues.values()),
                "workers": [
                    {
                        "id": worker.id,
                        "worker_key": worker.worker_key,
                        "queue_name": worker.queue_name,
                        "hostname": worker.hostname,
                        "process_id": worker.process_id,
                        "status": worker.status,
                        "current_item_id": worker.current_item_id,
                        "heartbeat_at": worker.heartbeat_at.isoformat(),
                    }
                    for worker in workers
                ],
            }

    def list_items(
        self,
        *,
        queue_name: str | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = select(QueueItem).order_by(
            QueueItem.created_at.desc()
        ).limit(limit)
        if queue_name is not None:
            statement = statement.where(QueueItem.queue_name == queue_name)
        if status is not None:
            statement = statement.where(QueueItem.status == status)
        with self._database.session_factory() as session:
            items = list(session.scalars(statement))
            return [self.item_response(item) for item in items]

    def get_item_for_task(self, task_id: str) -> QueueItem | None:
        with self._database.session_factory() as session:
            return session.scalar(
                select(QueueItem).where(QueueItem.task_id == task_id)
            )

    def get_item_for_ingestion(self, ingestion_id: str) -> QueueItem | None:
        with self._database.session_factory() as session:
            return session.scalar(
                select(QueueItem).where(
                    QueueItem.ingestion_id == ingestion_id
                )
            )

    @staticmethod
    def item_response(item: QueueItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "queue_name": item.queue_name,
            "job_type": item.job_type,
            "task_id": item.task_id,
            "ingestion_id": item.ingestion_id,
            "issue_id": item.issue_id,
            "project_id": item.project_id,
            "conversation_id": item.conversation_id,
            "client_id": item.client_id,
            "priority": item.priority,
            "status": item.status,
            "attempt_count": item.attempt_count,
            "max_attempts": item.max_attempts,
            "available_at": item.available_at.isoformat(),
            "lease_owner": item.lease_owner,
            "lease_expires_at": (
                item.lease_expires_at.isoformat()
                if item.lease_expires_at is not None
                else None
            ),
            "cancel_requested_at": (
                item.cancel_requested_at.isoformat()
                if item.cancel_requested_at is not None
                else None
            ),
            "error": item.error,
            "created_at": item.created_at.isoformat(),
            "completed_at": (
                item.completed_at.isoformat()
                if item.completed_at is not None
                else None
            ),
        }

    def touch_worker(
        self,
        *,
        worker_key: str,
        queue_name: str,
        status: str,
        current_item_id: str | None = None,
        session=None,
    ) -> None:
        owns_session = session is None
        if session is None:
            session = self._database.session_factory()
        try:
            worker = session.scalar(
                select(QueueWorker).where(
                    QueueWorker.worker_key == worker_key
                )
            )
            now = utc_now()
            if worker is None:
                worker = QueueWorker(
                    worker_key=worker_key,
                    queue_name=queue_name,
                    hostname=socket.gethostname(),
                    process_id=os.getpid(),
                )
                session.add(worker)
            worker.queue_name = queue_name
            worker.status = status
            worker.current_item_id = current_item_id
            worker.heartbeat_at = now
            worker.stopped_at = now if status == "stopped" else None
            if owns_session:
                session.commit()
        finally:
            if owns_session:
                session.close()

    def _requeue_locked(self, session, item: QueueItem, *, reason: str) -> None:
        if item.cancel_requested_at is not None:
            self._cancel_locked(session, item, reason="cancel_requested")
            return
        now = utc_now()
        item.status = QueueItemStatus.QUEUED
        item.available_at = now + timedelta(
            seconds=min(60, 2 ** max(0, item.attempt_count - 1))
        )
        item.lease_owner = None
        item.lease_expires_at = None
        item.heartbeat_at = None
        item.error = reason
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            if task is not None and task.status not in TaskStatus.TERMINAL:
                task.status = TaskStatus.QUEUED
                task.error = None
                task.completed_at = None
                self._task_service.append_event(
                    session,
                    task=task,
                    event_type="task.requeued",
                    data={
                        "reason": reason,
                        "attempt": item.attempt_count,
                    },
                )
        if item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            if ingestion is not None and ingestion.status not in {
                "completed",
                "failed",
                "cancelled",
            }:
                ingestion.status = "queued"
                ingestion.error = None
                ingestion.completed_at = None
                self._append_ingestion_event(
                    session,
                    ingestion,
                    "knowledge.ingestion.requeued",
                    {
                        "reason": reason,
                        "attempt": item.attempt_count,
                    },
                )
        if item.issue_id is not None:
            issue = session.get(OperationalIssue, item.issue_id)
            if issue is not None and issue.status not in OperationalIssueStatus.TERMINAL:
                issue.status = OperationalIssueStatus.DETECTED

    @staticmethod
    def _aware_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @staticmethod
    def _reset_terminal_item(item: QueueItem, *, now: datetime) -> None:
        item.status = QueueItemStatus.QUEUED
        item.available_at = now
        item.lease_owner = None
        item.lease_expires_at = None
        item.heartbeat_at = None
        item.cancel_requested_at = None
        item.error = None
        item.completed_at = None

    def _cancel_locked(self, session, item: QueueItem, *, reason: str) -> None:
        now = utc_now()
        item.status = QueueItemStatus.CANCELLED
        item.completed_at = now
        item.lease_owner = None
        item.lease_expires_at = None
        item.error = reason
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            if task is not None and (
                task.status not in TaskStatus.TERMINAL
                or (
                    item.cancel_requested_at is not None
                    and task.completed_at is not None
                    and self._aware_datetime(item.cancel_requested_at)
                    <= self._aware_datetime(task.completed_at)
                )
            ):
                task.status = TaskStatus.CANCELLED
                task.completed_at = now
                task.final_report = None
                task.knowledge_usage = None
                task.error = None
                self._task_service.append_event(
                    session,
                    task=task,
                    event_type="task.cancelled",
                    data={"reason": reason},
                )
        if item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            if ingestion is not None and (
                ingestion.status not in {"completed", "failed", "cancelled"}
                or (
                    item.cancel_requested_at is not None
                    and ingestion.completed_at is not None
                    and self._aware_datetime(item.cancel_requested_at)
                    <= self._aware_datetime(ingestion.completed_at)
                )
            ):
                ingestion.status = "cancelled"
                ingestion.completed_at = now
                event_data: dict[str, Any] = {"reason": reason}
                if ingestion.trigger == "scheduled":
                    source = session.get(KnowledgeSource, ingestion.source_id)
                    if source is not None:
                        source.last_sync_attempt_at = now
                        source.sync_lease_owner = None
                        source.sync_lease_expires_at = None
                        if source.enabled and source.sync_mode == "scheduled":
                            source.next_sync_at = now + timedelta(
                                minutes=source.sync_interval_minutes
                            )
                        else:
                            source.next_sync_at = None
                        event_data["next_sync_at"] = (
                            source.next_sync_at.isoformat()
                            if source.next_sync_at is not None
                            else None
                        )
                self._append_ingestion_event(
                    session,
                    ingestion,
                    "knowledge.ingestion.cancelled",
                    event_data,
                )
        if item.issue_id is not None:
            issue = session.get(OperationalIssue, item.issue_id)
            if issue is not None:
                issue.status = OperationalIssueStatus.REJECTED
                issue.resolution = reason
                issue.closed_at = now

    def _fail_locked(self, session, item: QueueItem, *, reason: str) -> None:
        now = utc_now()
        item.status = QueueItemStatus.FAILED
        item.error = reason
        item.completed_at = now
        item.lease_owner = None
        item.lease_expires_at = None
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            if task is not None and task.status not in TaskStatus.TERMINAL:
                task.status = TaskStatus.FAILED
                task.error = reason
                task.completed_at = now
                self._task_service.append_event(
                    session,
                    task=task,
                    event_type="task.failed",
                    data={"error": reason, "reason": "queue_attempts_exhausted"},
                )
        if item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            if ingestion is not None and ingestion.status not in {
                "completed",
                "failed",
                "cancelled",
            }:
                ingestion.status = "failed"
                ingestion.error = reason
                ingestion.completed_at = now
                self._append_ingestion_event(
                    session,
                    ingestion,
                    "knowledge.ingestion.failed",
                    {"error": reason, "reason": "queue_attempts_exhausted"},
                )
        if item.issue_id is not None:
            issue = session.get(OperationalIssue, item.issue_id)
            if issue is not None:
                issue.summary = reason

    @staticmethod
    def _append_ingestion_event(
        session,
        ingestion: KnowledgeIngestion,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        session.add(
            KnowledgeIngestionEvent(
                ingestion_id=ingestion.id,
                sequence=ingestion.next_event_sequence,
                type=event_type,
                data=data,
            )
        )
        ingestion.next_event_sequence += 1

    @staticmethod
    def _resource_status(session, item: QueueItem) -> str:
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            return task.status if task is not None else "failed"
        if item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            return ingestion.status if ingestion is not None else "failed"
        issue = session.get(OperationalIssue, item.issue_id)
        if issue is None:
            return "failed"
        if issue.status == OperationalIssueStatus.TRIAGE_FAILED:
            return "failed"
        return "completed"

    def _cancellation_precedes_completion(self, session, item: QueueItem) -> bool:
        if item.cancel_requested_at is None:
            return False
        completed_at = None
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            completed_at = task.completed_at if task is not None else None
        elif item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            completed_at = ingestion.completed_at if ingestion is not None else None
        if completed_at is None:
            return True
        return self._aware_datetime(
            item.cancel_requested_at
        ) <= self._aware_datetime(completed_at)

    @staticmethod
    def _resource_error(session, item: QueueItem) -> str | None:
        if item.task_id is not None:
            task = session.get(Task, item.task_id)
            return task.error if task is not None else "Task is unavailable"
        if item.ingestion_id is not None:
            ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
            return (
                ingestion.error
                if ingestion is not None
                else "Knowledge ingestion is unavailable"
            )
        issue = session.get(OperationalIssue, item.issue_id)
        return issue.summary if issue is not None else "Operational issue is unavailable"
