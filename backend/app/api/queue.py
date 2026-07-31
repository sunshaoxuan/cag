from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_queue_coordinator, get_queue_service
from app.queue.coordinator import QueueCoordinator
from app.queue.service import QueueService


router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.get("/status")
def queue_status(
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, object]:
    return coordinator.status()


@router.get("/items")
def list_queue_items(
    queue_name: str | None = None,
    item_status: Annotated[
        str | None,
        Query(
            alias="status",
            pattern=r"^(queued|leased|completed|failed|cancelled)$",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    service: QueueService = Depends(get_queue_service),
) -> list[dict[str, Any]]:
    return service.list_items(
        queue_name=queue_name,
        status=item_status,
        limit=limit,
    )


@router.post(
    "/items/{item_id}/cancel",
    status_code=status.HTTP_202_ACCEPTED,
)
async def cancel_queue_item(
    item_id: str,
    service: QueueService = Depends(get_queue_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, str]:
    try:
        queue_status_value = service.request_cancel(item_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Queue item not found",
        ) from error
    await coordinator.notify("interactive")
    await coordinator.notify("knowledge")
    await coordinator.notify("operations")
    return {"id": item_id, "status": queue_status_value}
