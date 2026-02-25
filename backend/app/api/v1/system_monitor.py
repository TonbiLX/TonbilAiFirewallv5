# --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
# Sistem Monitörü API: donanım bilgileri, canlı metrikler, fan kontrolü.
# DB bagimliligi yok - tamamen bellek ici ve /proc, /sys dosya okuma.

import logging
from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.system_monitor import (
    SystemHardwareInfo,
    SystemMetricsResponse,
    SystemMetricsSnapshot,
    FanConfig,
    FanConfigUpdate,
)
from app.services import system_monitor_service as monitor

router = APIRouter()
logger = logging.getLogger("tonbilai.system_monitor_api")


@router.get("/info", response_model=SystemHardwareInfo)
async def get_hardware_info(
    current_user: User = Depends(get_current_user),
):
    """Statik donanım bilgileri (model, CPU, RAM, disk)."""
    info = monitor.read_hardware_info()
    return SystemHardwareInfo(**info)


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_metrics(
    current_user: User = Depends(get_current_user),
):
    """Anlik metrikler + son 5 dakikalik gecmis."""
    current = monitor.get_current_metrics()
    if current is None:
        raise HTTPException(
            status_code=503,
            detail="Metrikler henüz toplanmadi. Lütfen bekleyin.",
        )
    history = monitor.get_metrics_history()
    return SystemMetricsResponse(
        current=SystemMetricsSnapshot(**current),
        history=history,
    )


@router.get("/fan", response_model=FanConfig)
async def get_fan_config(
    current_user: User = Depends(get_current_user),
):
    """Fan kontrol ayarlarıni getir."""
    config = monitor.get_fan_config()
    return FanConfig(**config)


@router.put("/fan", response_model=FanConfig)
async def update_fan_config(
    req: FanConfigUpdate,
    current_user: User = Depends(get_current_user),
):
    """Fan kontrol ayarlarıni güncelle."""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="En az bir alan belirtilmeli.")

    if "mode" in updates and updates["mode"] not in ("auto", "manual"):
        raise HTTPException(
            status_code=400, detail="mode 'auto' veya 'manual' olmali."
        )

    config = monitor.update_fan_config(updates)
    logger.info(f"Fan config güncellendi: {config}")
    return FanConfig(**config)
