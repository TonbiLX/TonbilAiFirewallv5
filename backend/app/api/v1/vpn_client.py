# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Dış VPN İstemci API: WireGuard istemci olarak dis VPN sunucusuna baglanma.
# Native wg-quick komutlari ile dogrudan bağlantı yönetimi.

import asyncio
import logging
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.models.vpn_client import VpnClientServer
from app.schemas.vpn_client import (
    VpnClientServerCreate, VpnClientServerUpdate, VpnClientServerResponse,
    VpnClientImport, VpnClientStatsResponse,
)
from app.hal.linux_nftables import (
    ensure_nat_postrouting_chain,
    add_vpn_nft_rules,
    remove_vpn_nft_rules,
    persist_nftables,
    setup_vpn_client_routing,
    teardown_vpn_client_routing,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.vpn_client")

# Native WireGuard config dizini
WG_CLIENT_DIR = Path("/etc/wireguard")
WG_CLIENT_CONF = "wg-client"  # wg-client.conf
WG_CLIENT_INTERFACE = "wg-client"

# Redis key'leri
REDIS_VPN_CLIENT_PREFIX = "vpn_client:"
REDIS_VPN_CONNECTED_SINCE = f"{REDIS_VPN_CLIENT_PREFIX}connected_since"
REDIS_VPN_PREV_RX = f"{REDIS_VPN_CLIENT_PREFIX}prev_rx"
REDIS_VPN_PREV_TX = f"{REDIS_VPN_CLIENT_PREFIX}prev_tx"
REDIS_VPN_PREV_TIME = f"{REDIS_VPN_CLIENT_PREFIX}prev_time"
REDIS_VPN_SESSION_RX = f"{REDIS_VPN_CLIENT_PREFIX}session_rx"
REDIS_VPN_SESSION_TX = f"{REDIS_VPN_CLIENT_PREFIX}session_tx"


async def _run_cmd(cmd: list, check: bool = True) -> str:
    """Komut calistir."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if proc.returncode != 0 and check:
        logger.error(f"Komut hatasi: {' '.join(cmd)} -> {err}")
        raise RuntimeError(err)
    return out


def _generate_wg_config(server: VpnClientServer) -> str:
    """DB kaydından WireGuard .conf dosyasi oluştur."""
    lines = ["[Interface]"]

    if server.private_key:
        lines.append(f"PrivateKey = {server.private_key}")
    if server.interface_address:
        lines.append(f"Address = {server.interface_address}")
    if server.dns_servers:
        lines.append(f"DNS = {server.dns_servers}")
    if server.mtu and server.mtu != 1420:
        lines.append(f"MTU = {server.mtu}")

    # NOT: PostUp/PostDown KULLANILMAZ. nftables kurallari Python tarafindan
    # activate/deactivate endpoint'lerinde yonetilir (güvenli comment-bazli silme).

    lines.append("")
    lines.append("[Peer]")
    lines.append(f"PublicKey = {server.public_key}")
    if server.preshared_key:
        lines.append(f"PresharedKey = {server.preshared_key}")
    lines.append(f"Endpoint = {server.endpoint}")
    lines.append(f"AllowedIPs = {server.allowed_ips}")
    if server.persistent_keepalive:
        lines.append(f"PersistentKeepalive = {server.persistent_keepalive}")

    return "\n".join(lines) + "\n"


async def _write_client_config(server: VpnClientServer) -> str:
    """WireGuard istemci config dosyasini native dizine yaz."""
    config_text = _generate_wg_config(server)
    conf_path = WG_CLIENT_DIR / f"{WG_CLIENT_CONF}.conf"

    try:
        # sudo tee ile yaz (permission için)
        proc = await asyncio.create_subprocess_exec(
            "sudo", "tee", str(conf_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate(input=config_text.encode())

        # Izinleri ayarla
        await _run_cmd(["sudo", "chmod", "600", str(conf_path)], check=False)
        logger.info(f"WireGuard client config yazildi: {conf_path}")
        return config_text
    except Exception as e:
        logger.error(f"Config yazma hatasi: {e}")
        raise HTTPException(status_code=500, detail="Config dosyasi yazilamadi.")


async def _remove_client_config():
    """WireGuard istemci config dosyasini sil."""
    conf_path = WG_CLIENT_DIR / f"{WG_CLIENT_CONF}.conf"
    try:
        await _run_cmd(["sudo", "rm", "-f", str(conf_path)], check=False)
        logger.info(f"WireGuard client config silindi: {conf_path}")
    except Exception as e:
        logger.warning(f"Config silme hatasi: {e}")


async def _get_connection_status() -> dict:
    """Mevcut WireGuard client bağlantı durumunu kontrol et (canlı).

    Handshake kontrolü: interface varsa bile handshake yoksa connected=False.
    Redis ile hiz hesaplama ve session takibi.
    """
    result = {
        "connected": False,
        "interface_exists": False,
        "transfer_rx": 0,
        "transfer_tx": 0,
        "endpoint": None,
        "last_handshake": None,
        "connected_since": None,
        "speed_rx_bps": 0,
        "speed_tx_bps": 0,
    }

    try:
        out = await _run_cmd(["sudo", "wg", "show", WG_CLIENT_INTERFACE], check=False)
        if not out or "Unable to access" in out or "No such device" in out:
            # Interface yok — Redis temizle
            await _clear_vpn_redis()
            return result

        result["interface_exists"] = True

        # Handshake kontrolü — gercek bağlantı için handshake olmali
        hs_match = re.search(r"latest handshake:\s*(.+)", out)
        has_handshake = False
        if hs_match:
            hs_val = hs_match.group(1).strip()
            if hs_val and hs_val != "0":
                has_handshake = True
                result["last_handshake"] = hs_val

        result["connected"] = has_handshake

        # Transfer bilgileri
        rx_match = re.search(r"([\d.]+)\s+(\w+)\s+received", out)
        tx_match = re.search(r"([\d.]+)\s+(\w+)\s+sent", out)
        if rx_match:
            result["transfer_rx"] = _parse_transfer(rx_match.group(1), rx_match.group(2))
        if tx_match:
            result["transfer_tx"] = _parse_transfer(tx_match.group(1), tx_match.group(2))

        # Endpoint
        ep_match = re.search(r"endpoint:\s+(\S+)", out)
        if ep_match:
            result["endpoint"] = ep_match.group(1)

        # Redis: hiz hesaplama + connected_since takibi
        if has_handshake:
            await _update_vpn_redis(result)
        else:
            await _clear_vpn_redis()

    except Exception as e:
        logger.debug(f"wg show hatasi: {e}")

    return result


async def _update_vpn_redis(status: dict):
    """Redis ile VPN client hiz ve oturum bilgisini güncelle."""
    try:
        redis = await get_redis()
        now = time.time()
        current_rx = status["transfer_rx"]
        current_tx = status["transfer_tx"]

        # connected_since: ilk kez bağlanıldığında kaydet
        connected_since = await redis.get(REDIS_VPN_CONNECTED_SINCE)
        if not connected_since:
            await redis.set(REDIS_VPN_CONNECTED_SINCE, str(now))
            connected_since = str(now)
        status["connected_since"] = float(connected_since)

        # Hiz hesaplama: onceki degerlerle kiyasla
        prev_rx = await redis.get(REDIS_VPN_PREV_RX)
        prev_tx = await redis.get(REDIS_VPN_PREV_TX)
        prev_time = await redis.get(REDIS_VPN_PREV_TIME)

        if prev_rx and prev_tx and prev_time:
            dt = now - float(prev_time)
            if dt > 0.5:  # En az 0.5 saniye farki olmali
                drx = max(0, current_rx - int(prev_rx))
                dtx = max(0, current_tx - int(prev_tx))
                status["speed_rx_bps"] = int(drx * 8 / dt)  # bits per second
                status["speed_tx_bps"] = int(dtx * 8 / dt)

        # Onceki degerleri kaydet (sonraki hesap için)
        pipe = redis.pipeline(transaction=False)
        pipe.set(REDIS_VPN_PREV_RX, str(current_rx))
        pipe.set(REDIS_VPN_PREV_TX, str(current_tx))
        pipe.set(REDIS_VPN_PREV_TIME, str(now))
        await pipe.execute()
    except Exception as e:
        logger.debug(f"VPN Redis güncelleme hatasi: {e}")


async def _clear_vpn_redis():
    """VPN client Redis verilerini temizle (disconnect/interface down)."""
    try:
        redis = await get_redis()

        # Oturum verilerini kaydet (kalicilik için)
        prev_rx = await redis.get(REDIS_VPN_PREV_RX)
        prev_tx = await redis.get(REDIS_VPN_PREV_TX)
        if prev_rx and int(prev_rx) > 0:
            old_session_rx = await redis.get(REDIS_VPN_SESSION_RX)
            old_session_tx = await redis.get(REDIS_VPN_SESSION_TX)
            total_rx = int(old_session_rx or 0) + int(prev_rx)
            total_tx = int(old_session_tx or 0) + int(prev_tx)
            await redis.set(REDIS_VPN_SESSION_RX, str(total_rx))
            await redis.set(REDIS_VPN_SESSION_TX, str(total_tx))

        await redis.delete(
            REDIS_VPN_CONNECTED_SINCE,
            REDIS_VPN_PREV_RX,
            REDIS_VPN_PREV_TX,
            REDIS_VPN_PREV_TIME,
        )
    except Exception as e:
        logger.debug(f"VPN Redis temizleme hatasi: {e}")


def _parse_transfer(value: str, unit: str) -> int:
    """Transfer degerini byte'a cevir."""
    v = float(value)
    u = unit.lower()
    if "kib" in u or "kb" in u:
        return int(v * 1024)
    elif "mib" in u or "mb" in u:
        return int(v * 1024 * 1024)
    elif "gib" in u or "gb" in u:
        return int(v * 1024 * 1024 * 1024)
    elif "tib" in u or "tb" in u:
        return int(v * 1024 * 1024 * 1024 * 1024)
    return int(v)  # B (byte)


# ===== ENDPOINTS =====

@router.get("/servers", response_model=List[VpnClientServerResponse])
async def list_client_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tum dis VPN sunuculari listele."""
    result = await db.execute(
        select(VpnClientServer).order_by(VpnClientServer.country, VpnClientServer.name)
    )
    return result.scalars().all()


@router.post("/servers", response_model=VpnClientServerResponse, status_code=201)
async def add_client_server(
    data: VpnClientServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yeni dis VPN sunucusu ekle (manuel)."""
    server = VpnClientServer(**data.model_dump())
    db.add(server)
    await db.flush()
    await db.refresh(server)
    return server


@router.post("/servers/import", response_model=VpnClientServerResponse, status_code=201)
async def import_from_config(
    data: VpnClientImport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WireGuard .conf dosyasindan import et."""
    parsed = _parse_wireguard_config(data.config_text)

    if not parsed.get("public_key"):
        raise HTTPException(
            status_code=400,
            detail="Config dosyasinda [Peer] PublicKey bulunamadı"
        )

    server = VpnClientServer(
        name=data.name,
        country=data.country or "Bilinmiyor",
        country_code=data.country_code or "XX",
        endpoint=parsed.get("endpoint", ""),
        public_key=parsed.get("public_key", ""),
        private_key=parsed.get("private_key"),
        preshared_key=parsed.get("preshared_key"),
        interface_address=parsed.get("address"),
        allowed_ips=parsed.get("allowed_ips", "0.0.0.0/0, ::/0"),
        dns_servers=parsed.get("dns"),
        mtu=parsed.get("mtu", 1420),
        persistent_keepalive=parsed.get("persistent_keepalive", 25),
    )
    db.add(server)
    await db.flush()
    await db.refresh(server)
    return server


@router.patch("/servers/{server_id}", response_model=VpnClientServerResponse)
async def update_client_server(
    server_id: int,
    data: VpnClientServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış VPN sunucusunu güncelle."""
    server = await db.get(VpnClientServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Sunucu bulunamadı")

    was_active = server.is_active
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(server, key, value)
    await db.flush()
    await db.refresh(server)

    # Aktif sunucu güncellendiyse config'i yeniden yaz ve restart
    if was_active and server.is_active:
        await _run_cmd(["sudo", "wg-quick", "down", WG_CLIENT_INTERFACE], check=False)
        await _write_client_config(server)
        await _run_cmd(["sudo", "wg-quick", "up", WG_CLIENT_INTERFACE], check=False)

    return server


@router.delete("/servers/{server_id}", status_code=204)
async def delete_client_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış VPN sunucusunu sil."""
    server = await db.get(VpnClientServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Sunucu bulunamadı")
    if server.is_active:
        raise HTTPException(
            status_code=400,
            detail="Aktif sunucu silinemez. Once bağlantıyi kesin."
        )
    await db.delete(server)


@router.post("/servers/{server_id}/activate")
async def activate_client_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış VPN sunucusunu etkinlestir - gercek WireGuard bağlantısi kur."""
    server = await db.get(VpnClientServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Sunucu bulunamadı")

    if not server.private_key:
        raise HTTPException(
            status_code=400,
            detail="Bu sunucunun Private Key'i tanimlanmamis. Bağlantı kurulamaz."
        )

    if not server.endpoint:
        raise HTTPException(
            status_code=400,
            detail="Bu sunucunun Endpoint adresi tanimlanmamis."
        )

    # Mevcut VPN client'i durdur + eski kuralları temizle
    await _run_cmd(["sudo", "wg-quick", "down", WG_CLIENT_INTERFACE], check=False)
    await teardown_vpn_client_routing(WG_CLIENT_INTERFACE)

    # Diger aktif sunucuyu devre disi birak
    result = await db.execute(
        select(VpnClientServer).where(VpnClientServer.is_active == True)  # noqa
    )
    for active_server in result.scalars().all():
        active_server.is_active = False
    await db.flush()

    # postrouting chain'i garantile
    await ensure_nat_postrouting_chain()

    # IP forwarding ac
    await _run_cmd(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

    # WireGuard config dosyasini yaz
    await _write_client_config(server)

    # wg-quick up + bridge trafik yonlendirme kur
    connected = False
    message = ""
    try:
        await _run_cmd(["sudo", "wg-quick", "up", WG_CLIENT_INTERFACE])

        # Bridge trafiğini VPN tuneline yonlendir
        # (nftables bridge tablosu + forward/masquerade + kill switch + DNS redirect)
        endpoint_ip = server.endpoint.split(":")[0] if ":" in server.endpoint else server.endpoint
        await setup_vpn_client_routing(WG_CLIENT_INTERFACE, endpoint_ip=endpoint_ip)

        # Başarılı — DB'de aktif isaretle
        server.is_active = True
        await db.flush()

        # Redis: connected_since kaydet
        try:
            redis = await get_redis()
            await redis.set(REDIS_VPN_CONNECTED_SINCE, str(time.time()))
        except Exception:
            pass

        connected = True
        message = f"{server.name} VPN bağlantısi kuruldu!"
    except Exception as e:
        # Başarısız — temizle
        server.is_active = False
        await db.flush()
        await _run_cmd(["sudo", "wg-quick", "down", WG_CLIENT_INTERFACE], check=False)
        await teardown_vpn_client_routing(WG_CLIENT_INTERFACE)
        message = f"{server.name} VPN bağlantı hatasi: {str(e)}"
        logger.error(f"VPN Client başlatilamadi: {e}")

    logger.info(f"VPN Client {'aktif' if connected else 'hata'}: {server.name} ({server.endpoint})")

    return {
        "server_id": server_id,
        "name": server.name,
        "country": server.country,
        "endpoint": server.endpoint,
        "active": connected,
        "connected": connected,
        "message": message,
    }


@router.post("/servers/{server_id}/deactivate")
async def deactivate_client_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış VPN sunucusunu devre disi birak - WireGuard bağlantısini kes."""
    server = await db.get(VpnClientServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Sunucu bulunamadı")

    # Redis: oturum verilerini kaydet
    await _clear_vpn_redis()

    server.is_active = False
    await db.flush()

    # Bridge VPN routing'i temizle (vpn_redirect tablosu + forward/masquerade + kill switch)
    await teardown_vpn_client_routing(WG_CLIENT_INTERFACE)

    # WireGuard bağlantısini durdur
    await _run_cmd(["sudo", "wg-quick", "down", WG_CLIENT_INTERFACE], check=False)
    await _remove_client_config()

    logger.info(f"VPN Client deaktif: {server.name}")

    return {
        "server_id": server_id,
        "active": False,
        "message": f"{server.name} VPN bağlantısi kapatildi.",
    }


@router.get("/status")
async def vpn_client_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """VPN istemci bağlantı durumu (canlı wg show + Redis hiz/oturum)."""
    conn_status = await _get_connection_status()

    active_result = await db.execute(
        select(VpnClientServer).where(VpnClientServer.is_active == True)  # noqa
    )
    active_server = active_result.scalar_one_or_none()

    # DB is_active ama interface yoksa tutarsizligi duzelt
    if active_server and not conn_status["interface_exists"]:
        active_server.is_active = False
        await db.flush()
        logger.warning(f"VPN Client durum tutarsizligi duzeltildi: {active_server.name} is_active=False")

    # Oturum süresi
    uptime_seconds = 0
    if conn_status.get("connected_since"):
        uptime_seconds = int(time.time() - conn_status["connected_since"])

    # Toplam oturum transfer (Redis'ten)
    session_total_rx = conn_status["transfer_rx"]
    session_total_tx = conn_status["transfer_tx"]
    try:
        redis = await get_redis()
        prev_session_rx = await redis.get(REDIS_VPN_SESSION_RX)
        prev_session_tx = await redis.get(REDIS_VPN_SESSION_TX)
        if prev_session_rx:
            session_total_rx += int(prev_session_rx)
        if prev_session_tx:
            session_total_tx += int(prev_session_tx)
    except Exception:
        pass

    return {
        "connected": conn_status["connected"],
        "active_server": active_server.name if active_server else None,
        "active_endpoint": active_server.endpoint if active_server else None,
        "active_country": active_server.country if active_server else None,
        "active_country_code": active_server.country_code if active_server else None,
        "transfer_rx": conn_status.get("transfer_rx", 0),
        "transfer_tx": conn_status.get("transfer_tx", 0),
        "session_total_rx": session_total_rx,
        "session_total_tx": session_total_tx,
        "speed_rx_bps": conn_status.get("speed_rx_bps", 0),
        "speed_tx_bps": conn_status.get("speed_tx_bps", 0),
        "last_handshake": conn_status.get("last_handshake"),
        "uptime_seconds": uptime_seconds,
    }


@router.get("/stats", response_model=VpnClientStatsResponse)
async def client_vpn_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dış VPN istemci istatistikleri."""
    total = await db.scalar(select(func.count(VpnClientServer.id))) or 0

    active_result = await db.execute(
        select(VpnClientServer).where(VpnClientServer.is_active == True)  # noqa
    )
    active_server = active_result.scalar_one_or_none()

    conn_status = await _get_connection_status()

    return VpnClientStatsResponse(
        total_servers=total,
        active_server=active_server.name if active_server else None,
        active_country=active_server.country if active_server else None,
        client_connected=conn_status["connected"],
    )


@router.post("/servers/clear-mock")
async def clear_mock_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mock/test sunuculari temizle."""
    result = await db.execute(
        select(VpnClientServer).where(
            VpnClientServer.public_key.like("mock_%")
        )
    )
    count = 0
    for server in result.scalars().all():
        await db.delete(server)
        count += 1
    await db.flush()
    return {"deleted": count}


def _parse_wireguard_config(config_text: str) -> dict:
    """WireGuard .conf dosyasini parse et."""
    result = {}
    for line in config_text.strip().split("\n"):
        line = line.strip()
        if "=" not in line or line.startswith("#") or line.startswith("["):
            continue
        key, _, value = line.partition("=")
        key = key.strip().lower()
        value = value.strip()

        if key == "privatekey":
            result["private_key"] = value
        elif key == "publickey":
            result["public_key"] = value
        elif key == "presharedkey":
            result["preshared_key"] = value
        elif key == "endpoint":
            result["endpoint"] = value
        elif key == "address":
            result["address"] = value
        elif key == "allowedips":
            result["allowed_ips"] = value
        elif key == "dns":
            result["dns"] = value
        elif key == "mtu":
            try:
                result["mtu"] = int(value)
            except ValueError:
                pass
        elif key == "persistentkeepalive":
            try:
                result["persistent_keepalive"] = int(value)
            except ValueError:
                pass

    return result
