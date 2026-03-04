# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Guvenlik ayarlari API: config CRUD, Redis hot-reload, canli istatistikler.

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.models.security_config import SecurityConfig
from app.models.user import User
from app.schemas.security_config import (
    SecurityConfigResponse,
    SecurityConfigUpdate,
    SecurityStatsResponse,
)

logger = logging.getLogger("tonbilai.security_settings")
router = APIRouter()

# Varsayilan degerler (reset ve defaults endpoint icin)
DEFAULTS = {
    "external_rate_threshold": 20,
    "local_rate_threshold": 300,
    "block_duration_sec": 3600,
    "dga_detection_enabled": True,
    "dga_entropy_threshold": 3.5,
    "insight_cooldown_sec": 1800,
    "subnet_flood_enabled": True,
    "subnet_flood_threshold": 5,
    "subnet_window_sec": 300,
    "subnet_block_duration_sec": 3600,
    "scan_pattern_enabled": True,
    "scan_pattern_threshold": 3,
    "scan_pattern_window_sec": 300,
    "threat_score_auto_block": 15,
    "threat_score_ttl": 3600,
    "aggregated_cooldown_sec": 1800,
    "dns_rate_limit_per_sec": 5,
    "dns_blocked_qtypes": "10,252,255",
    "sinkhole_ipv4": "192.168.1.2",
    "sinkhole_ipv6": "::",
    "ddos_alert_syn_flood": 100,
    "ddos_alert_udp_flood": 200,
    "ddos_alert_icmp_flood": 50,
    "ddos_alert_conn_limit": 500,
    "ddos_alert_invalid_packet": 100,
    "ddos_alert_cooldown_sec": 1800,
    "fingerprint_ttl": 3600,
    "fingerprint_min_matches": 1,
    "fingerprint_update_cooldown": 300,
}


async def _get_or_create_config(db: AsyncSession) -> SecurityConfig:
    """Singleton SecurityConfig getir, yoksa default degerlerle olustur."""
    result = await db.execute(select(SecurityConfig))
    config = result.scalar_one_or_none()
    if not config:
        config = SecurityConfig()
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def _push_config_to_redis(config: SecurityConfig, redis=None):
    """Tum config degerlerini Redis security:config HASH'e yaz."""
    if redis is None:
        redis = await get_redis()
    mapping = {}
    for key in DEFAULTS:
        val = getattr(config, key, DEFAULTS[key])
        mapping[key] = str(val)
    await redis.hset("security:config", mapping=mapping)
    logger.info("Guvenlik ayarlari Redis'e push edildi")


@router.get("/config", response_model=SecurityConfigResponse)
async def get_security_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mevcut guvenlik ayarlarini getir."""
    config = await _get_or_create_config(db)
    return config


@router.put("/config", response_model=SecurityConfigResponse)
async def update_security_config(
    data: SecurityConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Guvenlik ayarlarini guncelle + Redis hot-reload."""
    config = await _get_or_create_config(db)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Guncellenecek alan yok")

    changes = []
    for field, value in update_data.items():
        old_val = getattr(config, field)
        if old_val != value:
            changes.append(f"{field}: {old_val} -> {value}")
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    # Redis hot-reload
    try:
        await _push_config_to_redis(config)
    except Exception as e:
        logger.error(f"Redis push hatasi: {e}")

    if changes:
        logger.info(f"Guvenlik ayarlari guncellendi: {', '.join(changes)}")

    return config


@router.post("/reload")
async def reload_security_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manuel Redis push (restart yerine)."""
    config = await _get_or_create_config(db)
    await _push_config_to_redis(config)
    return {"status": "ok", "message": "Guvenlik ayarlari Redis'e yeniden yuklendi"}


@router.get("/stats", response_model=SecurityStatsResponse)
async def get_security_stats(
    current_user: User = Depends(get_current_user),
):
    """Canli guvenlik istatistikleri (Redis'ten)."""
    try:
        redis = await get_redis()
        stats = await redis.hgetall("dns:threat:stats") or {}
        blocked_count = await redis.scard("dns:threat:blocked")

        # Engelli subnet sayisi
        subnet_count = 0
        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor, match="dns:threat:subnet_blocked:*", count=100
            )
            subnet_count += len(keys)
            if cursor == 0:
                break

        return SecurityStatsResponse(
            blocked_ip_count=blocked_count,
            total_auto_blocks=int(stats.get("total_auto_blocks", 0)),
            total_external_blocked=int(stats.get("total_external_blocked", 0)),
            total_suspicious=int(stats.get("total_suspicious", 0)),
            dga_detections=int(stats.get("dga_detections", 0)),
            blocked_subnet_count=subnet_count,
            last_threat_time=stats.get("last_threat_time"),
        )
    except Exception as e:
        logger.error(f"Guvenlik istatistik hatasi: {e}")
        return SecurityStatsResponse()


@router.get("/defaults")
async def get_security_defaults(
    current_user: User = Depends(get_current_user),
):
    """Varsayilan degerleri dondur (reset UI icin)."""
    return DEFAULTS


@router.post("/reset", response_model=SecurityConfigResponse)
async def reset_security_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum ayarlari varsayilana dondur + Redis push."""
    config = await _get_or_create_config(db)

    for field, value in DEFAULTS.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    await _push_config_to_redis(config)
    logger.info("Guvenlik ayarlari varsayilana donduruld")

    return config
