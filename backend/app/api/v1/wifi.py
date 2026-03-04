# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WiFi AP REST API: durum, konfigürasyon, kontrol, istemciler, kanal tarama,
# misafir agi, zamanlama, MAC filtre.

import json
import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.wifi_config import WifiConfig
from app.schemas.wifi import (
    WifiStatusResponse,
    WifiConfigResponse,
    WifiConfigUpdate,
    WifiGuestUpdate,
    WifiScheduleUpdate,
    WifiMacFilterUpdate,
    WifiClientResponse,
)
from app.hal.wifi_driver import (
    get_wifi_status,
    get_wifi_clients,
    scan_available_channels,
    write_hostapd_config,
    write_guest_config,
    start_wifi_ap,
    stop_wifi_ap,
    restart_wifi_ap,
    start_guest_ap,
    stop_guest_ap,
    set_mac_filter,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.wifi_api")


async def _ensure_config(db: AsyncSession) -> WifiConfig:
    """DB'de WiFi config varsa don, yoksa varsayilan olustur."""
    result = await db.execute(select(WifiConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = WifiConfig(
            ssid="TonbilAiOS",
            password="TonbilWiFi2026",
            channel=6,
            band="2.4GHz",
            tx_power=20,
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
        logger.info("WiFi varsayilan config olusturuldu")
    return config


def _config_to_response(config: WifiConfig) -> WifiConfigResponse:
    """DB config'ini response'a cevir (sifre maskelenmiyor — frontend maskeleyebilir)."""
    mac_list = []
    if config.mac_filter_list:
        try:
            mac_list = json.loads(config.mac_filter_list)
        except (json.JSONDecodeError, TypeError):
            mac_list = []

    return WifiConfigResponse(
        ssid=config.ssid or "TonbilAiOS",
        password=config.password,
        channel=config.channel or 6,
        band=config.band or "2.4GHz",
        tx_power=config.tx_power or 20,
        hidden_ssid=config.hidden_ssid or False,
        enabled=config.enabled or False,
        guest_enabled=config.guest_enabled or False,
        guest_ssid=config.guest_ssid,
        guest_password=config.guest_password,
        mac_filter_mode=config.mac_filter_mode or "disabled",
        mac_filter_list=mac_list,
        schedule_enabled=config.schedule_enabled or False,
        schedule_start=config.schedule_start,
        schedule_stop=config.schedule_stop,
    )


def _config_to_hostapd_dict(config: WifiConfig) -> dict:
    """DB config'ini hostapd yazma icin dict'e cevir."""
    mac_list = []
    if config.mac_filter_list:
        try:
            mac_list = json.loads(config.mac_filter_list)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "ssid": config.ssid,
        "password": config.password,
        "channel": config.channel,
        "band": config.band,
        "tx_power": config.tx_power,
        "hidden_ssid": config.hidden_ssid,
        "mac_filter_mode": config.mac_filter_mode or "disabled",
        "mac_filter_list": mac_list,
    }


# ===== ENDPOINTS =====

@router.get("/status", response_model=WifiStatusResponse)
async def wifi_status(
    current_user: User = Depends(get_current_user),
):
    """WiFi AP canli durum bilgisi."""
    status = await get_wifi_status()
    return WifiStatusResponse(**status)


@router.get("/config", response_model=WifiConfigResponse)
async def wifi_config_get(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WiFi AP kayitli ayarlarini getir."""
    config = await _ensure_config(db)
    return _config_to_response(config)


@router.put("/config", response_model=WifiConfigResponse)
async def wifi_config_update(
    data: WifiConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WiFi AP ana ag ayarlarini guncelle."""
    config = await _ensure_config(db)

    # Alanlari guncelle (sadece gonderilenleri)
    if data.ssid is not None:
        config.ssid = data.ssid
    if data.password is not None:
        config.password = data.password if data.password != "" else None
    if data.channel is not None:
        config.channel = data.channel
    if data.band is not None:
        config.band = data.band
    if data.tx_power is not None:
        config.tx_power = data.tx_power
    if data.hidden_ssid is not None:
        config.hidden_ssid = data.hidden_ssid

    await db.flush()
    await db.refresh(config)

    # Config dosyasini yaz ve AP calisiyorsa restart
    hostapd_dict = _config_to_hostapd_dict(config)
    await write_hostapd_config(hostapd_dict)
    if config.enabled:
        await restart_wifi_ap()
        logger.info("WiFi AP config guncellendi ve yeniden baslatildi")
    else:
        logger.info("WiFi AP config guncellendi (AP kapali, restart yapilmadi)")

    return _config_to_response(config)


@router.post("/enable")
async def wifi_enable(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WiFi AP baslat."""
    config = await _ensure_config(db)

    # Config dosyasini yaz
    hostapd_dict = _config_to_hostapd_dict(config)
    ok = await write_hostapd_config(hostapd_dict)
    if not ok:
        raise HTTPException(status_code=500, detail="hostapd config yazilamadi")

    # MAC filtre dosyalarini yaz
    mac_list = []
    if config.mac_filter_list:
        try:
            mac_list = json.loads(config.mac_filter_list)
        except (json.JSONDecodeError, TypeError):
            pass
    await set_mac_filter(config.mac_filter_mode or "disabled", mac_list)

    # AP baslat
    ok = await start_wifi_ap()
    if not ok:
        raise HTTPException(status_code=500, detail="WiFi AP baslatilamadi")

    # Misafir AP aktifse onu da baslat
    if config.guest_enabled:
        await write_guest_config({
            "guest_ssid": config.guest_ssid,
            "guest_password": config.guest_password,
            "channel": config.channel,
        })
        await start_guest_ap()

    config.enabled = True
    await db.flush()

    logger.info("WiFi AP baslatildi")
    return {"status": "enabled", "ssid": config.ssid}


@router.post("/disable")
async def wifi_disable(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WiFi AP durdur."""
    config = await _ensure_config(db)

    # Misafir AP durdur
    if config.guest_enabled:
        await stop_guest_ap()

    # Ana AP durdur
    await stop_wifi_ap()

    config.enabled = False
    await db.flush()

    logger.info("WiFi AP durduruldu")
    return {"status": "disabled"}


@router.get("/clients", response_model=list[WifiClientResponse])
async def wifi_clients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bagli WiFi istemcilerini listele (Device tablosu eslesmesi ile)."""
    from app.models.device import Device

    clients = await get_wifi_clients()

    # Device tablosundan hostname eslestirmesi
    if clients:
        macs = [c["mac_address"].upper() for c in clients]
        result = await db.execute(
            select(Device).where(Device.mac_address.in_(macs))
        )
        device_map = {d.mac_address.upper(): d for d in result.scalars().all()}

        for client in clients:
            device = device_map.get(client["mac_address"].upper())
            if device:
                client["hostname"] = device.hostname or device.custom_name

    return [WifiClientResponse(**c) for c in clients]


@router.get("/channels")
async def wifi_channels(
    current_user: User = Depends(get_current_user),
):
    """Kullanilabilir WiFi kanallarini listele."""
    return await scan_available_channels()


@router.put("/guest", response_model=WifiConfigResponse)
async def wifi_guest_update(
    data: WifiGuestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Misafir ag ayarlarini guncelle."""
    config = await _ensure_config(db)

    if data.guest_enabled is not None:
        config.guest_enabled = data.guest_enabled
    if data.guest_ssid is not None:
        config.guest_ssid = data.guest_ssid
    if data.guest_password is not None:
        config.guest_password = data.guest_password if data.guest_password != "" else None

    await db.flush()
    await db.refresh(config)

    # Misafir AP ayarlarini uygula
    if config.enabled:
        if config.guest_enabled:
            await write_guest_config({
                "guest_ssid": config.guest_ssid,
                "guest_password": config.guest_password,
                "channel": config.channel,
            })
            await stop_guest_ap()
            await start_guest_ap()
            logger.info("Misafir AP guncellendi ve yeniden baslatildi")
        else:
            await stop_guest_ap()
            logger.info("Misafir AP durduruldu")

    return _config_to_response(config)


@router.put("/schedule", response_model=WifiConfigResponse)
async def wifi_schedule_update(
    data: WifiScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Zamanlama ayarlarini guncelle."""
    config = await _ensure_config(db)

    if data.schedule_enabled is not None:
        config.schedule_enabled = data.schedule_enabled
    if data.schedule_start is not None:
        config.schedule_start = data.schedule_start
    if data.schedule_stop is not None:
        config.schedule_stop = data.schedule_stop

    await db.flush()
    await db.refresh(config)

    logger.info(f"WiFi zamanlama guncellendi: enabled={config.schedule_enabled}, "
                f"start={config.schedule_start}, stop={config.schedule_stop}")

    return _config_to_response(config)


@router.put("/mac-filter", response_model=WifiConfigResponse)
async def wifi_mac_filter_update(
    data: WifiMacFilterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """MAC filtre ayarlarini guncelle."""
    config = await _ensure_config(db)

    config.mac_filter_mode = data.mac_filter_mode
    config.mac_filter_list = json.dumps(data.mac_filter_list)

    await db.flush()
    await db.refresh(config)

    # MAC filtre dosyalarini yaz
    await set_mac_filter(data.mac_filter_mode, data.mac_filter_list)

    # AP calisiyorsa config yeniden yaz ve restart
    if config.enabled:
        hostapd_dict = _config_to_hostapd_dict(config)
        await write_hostapd_config(hostapd_dict)
        await restart_wifi_ap()
        logger.info("MAC filtre guncellendi ve AP yeniden baslatildi")
    else:
        logger.info("MAC filtre guncellendi (AP kapali)")

    return _config_to_response(config)
