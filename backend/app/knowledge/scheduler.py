import asyncio
import logging
import uuid
from contextlib import suppress

from app.knowledge.service import KnowledgeService


logger = logging.getLogger(__name__)


class KnowledgeScheduler:
    def __init__(
        self,
        *,
        service: KnowledgeService,
        poll_seconds: int,
        lease_seconds: int,
    ) -> None:
        self._service = service
        self._poll_seconds = poll_seconds
        self._lease_seconds = lease_seconds
        self._worker_id = f"knowledge-scheduler:{uuid.uuid4()}"
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._service.recover_interrupted_ingestions()
        self._task = asyncio.create_task(
            self._run(),
            name="cag-knowledge-scheduler",
        )

    async def stop(self) -> None:
        task = self._task
        if task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(task, timeout=30)
        except TimeoutError:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        finally:
            self._task = None
            self._service.set_scheduler_running(False)

    async def run_once(self) -> bool:
        source_id = await asyncio.to_thread(
            self._service.claim_due_source,
            worker_id=self._worker_id,
            lease_seconds=self._lease_seconds,
        )
        if source_id is None:
            return False
        try:
            ingestion, created = await asyncio.to_thread(
                self._service.create_ingestion,
                source_id,
                trigger="scheduled",
            )
            if created:
                await self._service.ingest(ingestion.id)
        finally:
            await asyncio.to_thread(
                self._service.release_sync_lease,
                source_id,
                self._worker_id,
            )
        return True

    async def _run(self) -> None:
        self._service.set_scheduler_running(True)
        try:
            while not self._stop_event.is_set():
                try:
                    worked = await self.run_once()
                except Exception:
                    logger.exception(
                        "Knowledge scheduler iteration failed"
                    )
                    worked = False
                if worked:
                    continue
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._poll_seconds,
                    )
                except TimeoutError:
                    continue
        finally:
            self._service.set_scheduler_running(False)
