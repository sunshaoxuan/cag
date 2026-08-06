import asyncio
import signal

from app.config import get_settings
from app.main import app


async def run_worker() -> None:
    settings = get_settings()
    if settings.process_role != "worker":
        raise RuntimeError("AGENT_GATEWAY_PROCESS_ROLE must be worker")
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop(*_: object) -> None:
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    async with app.router.lifespan_context(app):
        await stop_event.wait()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
