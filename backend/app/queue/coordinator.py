import asyncio
import logging
import os
import socket
import uuid
from contextlib import suppress

from app.knowledge.service import KnowledgeService
from app.knowledge.extraction import CustomerKnowledgeExtractionService
from app.models import QueueItem
from app.queue.notifier import QueueNotifier
from app.queue.service import QueueService
from app.tasks.executor import TaskExecutor
from app.operations.service import OperationalIssueService


logger = logging.getLogger(__name__)


class QueueCoordinator:
    def __init__(
        self,
        *,
        service: QueueService,
        notifier: QueueNotifier,
        task_executor: TaskExecutor,
        knowledge_service: KnowledgeService,
        extraction_service: CustomerKnowledgeExtractionService,
        interactive_workers: int,
        knowledge_workers: int,
        extraction_workers: int,
        operations_workers: int,
        operational_issue_service: OperationalIssueService,
        poll_seconds: float,
        heartbeat_seconds: int,
        shutdown_seconds: int,
    ) -> None:
        self._service = service
        self._notifier = notifier
        self._task_executor = task_executor
        self._knowledge_service = knowledge_service
        self._extraction_service = extraction_service
        self._operational_issue_service = operational_issue_service
        self._worker_counts = {
            "interactive": interactive_workers,
            "knowledge": knowledge_workers,
            "extraction": extraction_workers,
            "operations": operations_workers,
        }
        self._poll_seconds = poll_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._shutdown_seconds = shutdown_seconds
        self._stop_event = asyncio.Event()
        self._workers: list[asyncio.Task[None]] = []

    @property
    def running(self) -> bool:
        return bool(self._workers) and any(
            not worker.done() for worker in self._workers
        )

    async def start(self) -> dict[str, int]:
        if self.running:
            return {
                "tasks_enqueued": 0,
                "ingestions_enqueued": 0,
                "expired_requeued": 0,
            }
        bootstrap = await asyncio.to_thread(self._service.bootstrap)
        await self._notifier.start()
        self._stop_event.clear()
        for queue_name, count in self._worker_counts.items():
            for ordinal in range(1, count + 1):
                worker_key = (
                    f"{socket.gethostname()}:{os.getpid()}:"
                    f"{queue_name}:{ordinal}:{uuid.uuid4()}"
                )
                task = asyncio.create_task(
                    self._worker_loop(
                        queue_name=queue_name,
                        worker_key=worker_key,
                    ),
                    name=f"cag-{queue_name}-worker-{ordinal}",
                )
                self._workers.append(task)
        for queue_name in self._worker_counts:
            await self._notifier.publish(queue_name)
        return bootstrap

    async def stop(self) -> None:
        if not self._workers:
            await self._notifier.stop()
            return
        self._stop_event.set()
        for queue_name in self._worker_counts:
            await self._notifier.publish(queue_name)
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=self._shutdown_seconds,
            )
        except TimeoutError:
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
        finally:
            self._workers.clear()
            await self._notifier.stop()

    async def notify(self, queue_name: str) -> None:
        await self._notifier.publish(queue_name)

    def status(self) -> dict[str, object]:
        snapshot = self._service.status_snapshot()
        return {
            "running": self.running or bool(snapshot["workers"]),
            "local_consumers_running": self.running,
            "configured_workers": dict(self._worker_counts),
            "redis": self._notifier.status(),
            **snapshot,
        }

    async def _worker_loop(
        self,
        *,
        queue_name: str,
        worker_key: str,
    ) -> None:
        await asyncio.to_thread(
            self._service.touch_worker,
            worker_key=worker_key,
            queue_name=queue_name,
            status="idle",
        )
        try:
            while not self._stop_event.is_set():
                item = await asyncio.to_thread(
                    self._service.claim_next,
                    queue_name=queue_name,
                    worker_key=worker_key,
                )
                if item is None:
                    await self._notifier.wait(
                        queue_name,
                        self._poll_seconds,
                    )
                    continue
                await self._execute_item(item, worker_key)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Queue worker %s failed", worker_key)
        finally:
            await asyncio.to_thread(
                self._service.touch_worker,
                worker_key=worker_key,
                queue_name=queue_name,
                status="stopped",
            )

    async def _execute_item(
        self,
        item: QueueItem,
        worker_key: str,
    ) -> None:
        execution = asyncio.create_task(
            self._dispatch(item),
            name=f"cag-queue-item-{item.id}",
        )
        try:
            while not execution.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(execution),
                        timeout=self._heartbeat_seconds,
                    )
                except TimeoutError:
                    cancel_requested = await asyncio.to_thread(
                        self._service.heartbeat,
                        item_id=item.id,
                        worker_key=worker_key,
                    )
                    if cancel_requested:
                        execution.cancel()
                except asyncio.CancelledError:
                    execution.cancel()
                    with suppress(asyncio.CancelledError):
                        await execution
                    raise
            await execution
        except asyncio.CancelledError:
            status = await asyncio.to_thread(
                self._service.abandon,
                item_id=item.id,
                worker_key=worker_key,
                reason=(
                    "worker_shutdown"
                    if self._stop_event.is_set()
                    else "cancel_requested"
                ),
            )
            if self._stop_event.is_set():
                raise
            logger.info(
                "Queue item %s stopped with status %s",
                item.id,
                status,
            )
        except Exception as error:
            logger.exception("Queue item %s execution failed", item.id)
            abandoned_status = await asyncio.to_thread(
                self._service.abandon,
                item_id=item.id,
                worker_key=worker_key,
                reason=f"{type(error).__name__}: {str(error)[:500]}",
            )
            if abandoned_status == "failed":
                await asyncio.to_thread(
                    self._operational_issue_service.capture_queue_failure,
                    item.id,
                )
        else:
            final_status = await asyncio.to_thread(
                self._service.finish,
                item_id=item.id,
                worker_key=worker_key,
            )
            if final_status == "failed":
                await asyncio.to_thread(
                    self._operational_issue_service.capture_queue_failure,
                    item.id,
                )

    async def _dispatch(self, item: QueueItem) -> None:
        if item.job_type == "agent_task" and item.task_id is not None:
            await self._task_executor.execute(item.task_id)
            return
        if (
            item.job_type == "knowledge_ingestion"
            and item.ingestion_id is not None
        ):
            await self._knowledge_service.ingest(item.ingestion_id)
            return
        if item.job_type == "customer_knowledge_extraction" and item.task_id is not None:
            await self._extraction_service.execute(item.task_id)
            return
        if item.issue_id is not None and item.job_type.startswith("operational_"):
            await self._operational_issue_service.process(
                item.issue_id,
                item.job_type,
            )
            return
        raise RuntimeError(f"Unsupported queue job type: {item.job_type}")
