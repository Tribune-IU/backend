from fastapi import APIRouter

from app.api.deps import DbDep
from app.schemas.v1 import TriggerMonitorResponse
from app.services.monitor_stub import trigger_monitor_stub

router = APIRouter(tags=["system"])


@router.post("/system:triggerMonitor", response_model=TriggerMonitorResponse)
async def trigger_monitor(db: DbDep) -> TriggerMonitorResponse:
    data = await trigger_monitor_stub(db)
    return TriggerMonitorResponse.model_validate(data)
