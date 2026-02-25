# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DDoS koruma API endpoint'leri: config CRUD, apply, toggle, status, counter loglari.

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ddos_config import DdosConfig
from app.models.user import User
from app.models.ai_insight import AiInsight, Severity
from app.schemas.ddos_config import DdosConfigResponse, DdosConfigUpdate, DdosProtectionStatus
from app.services import ddos_service

logger = logging.getLogger("tonbilai.ddos")
router = APIRouter()

TOGGLE_FIELDS = {
    "syn_flood": "syn_flood_enabled",
    "udp_flood": "udp_flood_enabled",
    "icmp_flood": "icmp_flood_enabled",
    "conn_limit": "conn_limit_enabled",
    "invalid_packet": "invalid_packet_enabled",
    "http_flood": "http_flood_enabled",
    "kernel_hardening": "kernel_hardening_enabled",
    "uvicorn_workers": "uvicorn_workers_enabled",
}

TOGGLE_LABELS = {
    "syn_flood": "SYN Flood Korumasi",
    "udp_flood": "UDP Flood Korumasi",
    "icmp_flood": "ICMP Flood Korumasi",
    "conn_limit": "Bağlantı Limiti",
    "invalid_packet": "Geçersiz Paket Filtreleme",
    "http_flood": "HTTP Flood Korumasi",
    "kernel_hardening": "Kernel Sertlestirme",
    "uvicorn_workers": "Uvicorn Worker",
}


async def _get_or_create_config(db: AsyncSession) -> DdosConfig:
    """Singleton DdosConfig getir, yoksa default degerlerle oluştur."""
    result = await db.execute(select(DdosConfig))
    config = result.scalar_one_or_none()
    if not config:
        config = DdosConfig()
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def _log_ddos_event(db: AsyncSession, message: str, severity: str = "info"):
    """DDoS işlemlerini AiInsight tablosuna logla."""
    try:
        insight = AiInsight(
            severity=Severity(severity),
            message=message,
            category="security",
            suggested_action="DDoS koruma panelinden ayarları kontrol edin.",
        )
        db.add(insight)
        await db.commit()
    except Exception as e:
        logger.error(f"DDoS log yazma hatasi: {e}")


@router.get("/config", response_model=DdosConfigResponse)
async def get_ddos_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mevcut DDoS koruma yapılandirmasini getir."""
    config = await _get_or_create_config(db)
    return config


@router.put("/config", response_model=DdosConfigResponse)
async def update_ddos_config(
    data: DdosConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DDoS yapılandirmasini güncelle ve kurallari otomatik uygula."""
    config = await _get_or_create_config(db)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")

    # Değişiklikleri logla
    changes = []
    for field, value in update_data.items():
        old_val = getattr(config, field)
        if old_val != value:
            changes.append(f"{field}: {old_val} → {value}")
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    # Kuralları otomatik uygula
    try:
        await ddos_service.apply_all(config)
    except Exception as e:
        logger.error(f"DDoS kurallarini uygulama hatasi: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Config kaydedildi ancak kurallar uygulanamadi: {str(e)}"
        )

    if changes:
        await _log_ddos_event(
            db,
            f"DDoS yapılandirmasi güncellendi: {', '.join(changes)}",
            "info",
        )

    return config


@router.post("/apply")
async def apply_ddos_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum DDoS kurallarini yeniden uygula (force)."""
    config = await _get_or_create_config(db)
    results = await ddos_service.apply_all(config)
    await _log_ddos_event(db, f"DDoS kurallari yeniden uygulandi: {results}", "info")
    return {"status": "ok", "results": results}


@router.post("/toggle/{protection_name}")
async def toggle_ddos_protection(
    protection_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tek bir koruma mekanizmasini toggle et (aktif/pasif)."""
    if protection_name not in TOGGLE_FIELDS:
        raise HTTPException(
            status_code=404,
            detail=f"Bilinmeyen koruma: {protection_name}. Gecerli: {list(TOGGLE_FIELDS.keys())}"
        )

    config = await _get_or_create_config(db)
    field = TOGGLE_FIELDS[protection_name]
    new_value = not getattr(config, field)
    setattr(config, field, new_value)

    await db.commit()
    await db.refresh(config)

    # Kuralları yeniden uygula
    try:
        await ddos_service.apply_all(config)
    except Exception as e:
        logger.error(f"DDoS toggle uygulama hatasi: {e}")

    label = TOGGLE_LABELS.get(protection_name, protection_name)
    state = "AKTIF" if new_value else "DEVRE DISI"
    await _log_ddos_event(db, f"DDoS korumasi değiştirildi: {label} → {state}", "info")

    # Uvicorn workers toggle → otomatik backend restart (2 sn gecikme)
    if protection_name == "uvicorn_workers":
        try:
            await ddos_service.schedule_backend_restart()
        except Exception as e:
            logger.error(f"Backend restart zamanlama hatasi: {e}")

    return {
        "protection": protection_name,
        "enabled": new_value,
        "status": "ok",
    }


@router.get("/status", response_model=list[DdosProtectionStatus])
async def get_ddos_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Her koruma mekanizmasi için aktif/pasif durum."""
    config = await _get_or_create_config(db)
    statuses = await ddos_service.get_ddos_status(config)
    return statuses




@router.post("/flush-attackers")
async def flush_ddos_attackers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum DDoS engellenen IP setlerini temizle."""
    result = await ddos_service.flush_attacker_sets()
    total = result.get("total_cleared", 0)
    await _log_ddos_event(
        db,
        f"DDoS engellenen IP'ler temizlendi: {total} IP",
        "info",
    )
    return result



@router.get("/attack-map")
async def get_ddos_attack_map(
    current_user: User = Depends(get_current_user),
):
    """DDoS Attack Map verisi: saldırgan IP'ler + GeoIP + counter özeti."""
    data = await ddos_service.get_attack_map_data()
    return data

@router.get("/counters")
async def get_ddos_counters(
    current_user: User = Depends(get_current_user),
):
    """DDoS nftables drop counter istatistikleri."""
    summary = await ddos_service.get_ddos_drop_summary()
    return summary
