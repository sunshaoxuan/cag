import asyncio
import logging
from contextlib import suppress

from redis.asyncio import Redis


logger = logging.getLogger(__name__)


class QueueNotifier:
    def __init__(
        self,
        *,
        redis_url: str,
        channel_prefix: str,
        enabled: bool,
    ) -> None:
        self._redis_url = redis_url
        self._channel_prefix = channel_prefix.rstrip(":")
        self._enabled = enabled
        self._events: dict[str, asyncio.Event] = {}
        self._publisher: Redis | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._connected = False
        self._last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def status(self) -> dict[str, object]:
        return {
            "enabled": self._enabled,
            "connected": self._connected,
            "delivery_role": "wake_up_only",
            "last_error": self._last_error,
        }

    async def start(self) -> None:
        if not self._enabled or self._listener_task is not None:
            return
        self._stop_event.clear()
        self._publisher = Redis.from_url(
            self._redis_url,
            decode_responses=True,
        )
        self._listener_task = asyncio.create_task(
            self._listen_forever(),
            name="cag-queue-redis-listener",
        )

    async def stop(self) -> None:
        self._stop_event.set()
        task = self._listener_task
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._listener_task = None
        if self._publisher is not None:
            await self._publisher.aclose()
        self._publisher = None
        self._connected = False

    async def publish(self, queue_name: str) -> None:
        self._event(queue_name).set()
        if not self._enabled or self._publisher is None:
            return
        try:
            await self._publisher.publish(
                self._channel(queue_name),
                queue_name,
            )
            self._connected = True
            self._last_error = None
        except Exception as error:
            self._connected = False
            self._last_error = self._safe_error(error)
            logger.warning("Redis queue wake-up publish failed: %s", self._last_error)

    async def wait(self, queue_name: str, timeout: float) -> None:
        event = self._event(queue_name)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            return
        finally:
            event.clear()

    async def _listen_forever(self) -> None:
        while not self._stop_event.is_set():
            subscriber: Redis | None = None
            pubsub = None
            try:
                subscriber = Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                )
                await subscriber.ping()
                pubsub = subscriber.pubsub()
                await pubsub.psubscribe(f"{self._channel_prefix}:*")
                self._connected = True
                self._last_error = None
                while not self._stop_event.is_set():
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    if not message:
                        continue
                    queue_name = str(message.get("data", ""))
                    if queue_name:
                        self._event(queue_name).set()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self._connected = False
                self._last_error = self._safe_error(error)
                logger.warning(
                    "Redis queue wake-up listener unavailable: %s",
                    self._last_error,
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=5,
                    )
                except TimeoutError:
                    pass
            finally:
                if pubsub is not None:
                    with suppress(Exception):
                        await pubsub.aclose()
                if subscriber is not None:
                    with suppress(Exception):
                        await subscriber.aclose()
        self._connected = False

    def _event(self, queue_name: str) -> asyncio.Event:
        event = self._events.get(queue_name)
        if event is None:
            event = asyncio.Event()
            self._events[queue_name] = event
        return event

    def _channel(self, queue_name: str) -> str:
        return f"{self._channel_prefix}:{queue_name}"

    @staticmethod
    def _safe_error(error: Exception) -> str:
        return f"{type(error).__name__}: {str(error)[:240]}"
