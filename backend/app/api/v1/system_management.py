# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Sistem Yönetimi API: servis kontrol, reboot, shutdown, boot bilgi, safe mode.

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.models.user import User
from app.services import system_management_service as sms

logger = logging.getLogger("tonbilai.api.system_management")

router = APIRouter()


class ConfirmAction(BaseModel):
    confirm: bool = False


# ============================================================================
# Sistem Genel Durum
# ============================================================================

@router.get("/overview")
async def get_system_overview(
    current_user: User = Depends(get_current_user),
):
    """Sistem genel durum: uptime, boot count, safe mode, watchdog."""
    return await sms.get_system_overview()


# ============================================================================
# Servis Yönetimi
# ============================================================================

@router.get("/services")
async def get_all_services(
    current_user: User = Depends(get_current_user),
):
    """Tum yonetilen servislerin durumu."""
    return await sms.get_all_services_status()


@router.post("/services/{service_name}/restart")
async def restart_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Servisi yeniden başlat."""
    try:
        result = await sms.restart_service(service_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/services/{service_name}/start")
async def start_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Servisi başlat."""
    try:
        result = await sms.start_service(service_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/services/{service_name}/stop")
async def stop_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Servisi durdur. SSH durdurulamaz."""
    try:
        result = await sms.stop_service(service_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ============================================================================
# Sistem İşlemleri
# ============================================================================

@router.post("/reboot")
async def reboot_system(
    data: ConfirmAction,
    current_user: User = Depends(get_current_user),
):
    """Sistemi 3sn içinde yeniden başlat. confirm=true gereklidir."""
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail="Onay gerekli: confirm=true gonderilmelidir",
        )
    result = await sms.reboot_system()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/shutdown")
async def shutdown_system(
    data: ConfirmAction,
    current_user: User = Depends(get_current_user),
):
    """Sistemi 3sn içinde kapat. confirm=true gereklidir."""
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail="Onay gerekli: confirm=true gonderilmelidir",
        )
    result = await sms.shutdown_system()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ============================================================================
# Boot & Safe Mode
# ============================================================================

@router.get("/boot-info")
async def get_boot_info(
    current_user: User = Depends(get_current_user),
):
    """Boot sayacı, safe mode durumu, watchdog, son boot zamanlari."""
    return await sms.get_boot_info()


@router.post("/reset-safe-mode")
async def reset_safe_mode(
    current_user: User = Depends(get_current_user),
):
    """Safe mode'dan cik: sayacı sıfırla, servisleri başlat."""
    result = await sms.reset_safe_mode()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ============================================================================
# Sistem Journal
# ============================================================================

@router.get("/journal")
async def get_journal(
    lines: int = Query(default=50, ge=10, le=200),
    current_user: User = Depends(get_current_user),
):
    """Son N satir sistem journal kaydi."""
    entries = await sms.get_systemd_journal_recent(lines)
    return {"lines": entries, "count": len(entries)}
