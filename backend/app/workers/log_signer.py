# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# 5651 Kanun Uyumu: Gunluk log imzalama ve saklama politikasi worker'i.
#
# Gorevler:
# 1. Her gun 00:05'te onceki gunun DNS/DHCP/bağlantı loglarını JSONL olarak yaz
# 2. Dosyanin SHA-256 hash'ini hesapla, HMAC-SHA256 ile imzala
# 3. log_signatures tablosuna kaydet
# 4. 30 gunden eski kayitlari temizle (retention)
# 5. Disk alan kontrolü

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import date, datetime, timedelta

from sqlalchemy import select, delete, func

from app.config import get_settings
from app.db.session import async_session_factory
from app.models.dns_query_log import DnsQueryLog
from app.models.dhcp_lease import DhcpLease
from app.models.device_connection_log import DeviceConnectionLog
from app.models.log_signature import LogSignature

logger = logging.getLogger("tonbilai.log_signer")

settings = get_settings()

LOG_ARCHIVE_PATH = os.environ.get("LOG_ARCHIVE_PATH", "/opt/tonbilaios/backend/logs/signed")
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "30"))


def _ensure_archive_dir():
    """Arsiv dizinini oluştur."""
    os.makedirs(LOG_ARCHIVE_PATH, exist_ok=True)


def _compute_sha256(file_path: str) -> str:
    """Dosyanin SHA-256 hash'ini hesapla."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_hmac(file_path: str, secret: str) -> str:
    """Dosyanin HMAC-SHA256 imzasini hesapla."""
    key = secret.encode("utf-8")
    h = hmac.new(key, digestmod=hashlib.sha256)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


async def _sign_dns_logs(target_date: date) -> dict | None:
    """Belirli bir gunun DNS sorgularini JSONL dosyasina yaz ve imzala."""
    date_str = target_date.isoformat()
    file_name = f"{date_str}_dns.jsonl"
    file_path = os.path.join(LOG_ARCHIVE_PATH, file_name)

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    async with async_session_factory() as session:
        result = await session.execute(
            select(DnsQueryLog)
            .where(DnsQueryLog.timestamp >= start_dt)
            .where(DnsQueryLog.timestamp < end_dt)
            .order_by(DnsQueryLog.id)
        )
        logs = result.scalars().all()

    if not logs:
        logger.info(f"5651 Imza: {date_str} için DNS log bulunamadı, atlanıyor.")
        return None

    record_count = 0
    with open(file_path, "w", encoding="utf-8") as f:
        for log in logs:
            record = {
                "id": log.id,
                "ts": log.timestamp.isoformat() if log.timestamp else "",
                "client_ip": log.client_ip or "",
                "mac": log.mac_address or "",
                "domain": log.domain,
                "query_type": log.query_type or "A",
                "blocked": log.blocked,
                "block_reason": log.block_reason or "",
                "answer_ip": log.answer_ip or "",
                "port": log.destination_port or 53,
                "wan_ip": log.wan_ip or "",
                "device_id": log.device_id,
                "upstream_ms": log.upstream_response_ms,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            record_count += 1

    sha256 = _compute_sha256(file_path)
    hmac_sig = _compute_hmac(file_path, settings.SECRET_KEY)
    file_size = os.path.getsize(file_path)

    return {
        "log_date": target_date,
        "log_type": "dns",
        "file_path": file_path,
        "record_count": record_count,
        "sha256_hash": sha256,
        "hmac_signature": hmac_sig,
        "file_size_bytes": file_size,
    }


async def _sign_dhcp_logs(target_date: date) -> dict | None:
    """Belirli bir gunun DHCP lease kayitlarini JSONL dosyasina yaz ve imzala."""
    date_str = target_date.isoformat()
    file_name = f"{date_str}_dhcp.jsonl"
    file_path = os.path.join(LOG_ARCHIVE_PATH, file_name)

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    async with async_session_factory() as session:
        result = await session.execute(
            select(DhcpLease)
            .where(DhcpLease.lease_start >= start_dt)
            .where(DhcpLease.lease_start < end_dt)
            .order_by(DhcpLease.id)
        )
        leases = result.scalars().all()

    if not leases:
        return None

    record_count = 0
    with open(file_path, "w", encoding="utf-8") as f:
        for lease in leases:
            record = {
                "id": lease.id,
                "mac_address": lease.mac_address or "",
                "ip_address": lease.ip_address or "",
                "hostname": lease.hostname or "",
                "lease_start": lease.lease_start.isoformat() if lease.lease_start else "",
                "lease_end": lease.lease_end.isoformat() if lease.lease_end else "",
                "is_static": lease.is_static,
                "device_id": lease.device_id,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            record_count += 1

    sha256 = _compute_sha256(file_path)
    hmac_sig = _compute_hmac(file_path, settings.SECRET_KEY)
    file_size = os.path.getsize(file_path)

    return {
        "log_date": target_date,
        "log_type": "dhcp",
        "file_path": file_path,
        "record_count": record_count,
        "sha256_hash": sha256,
        "hmac_signature": hmac_sig,
        "file_size_bytes": file_size,
    }


async def _sign_connection_logs(target_date: date) -> dict | None:
    """Belirli bir gunun cihaz bağlantı loglarını JSONL dosyasina yaz ve imzala."""
    date_str = target_date.isoformat()
    file_name = f"{date_str}_connection.jsonl"
    file_path = os.path.join(LOG_ARCHIVE_PATH, file_name)

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    async with async_session_factory() as session:
        result = await session.execute(
            select(DeviceConnectionLog)
            .where(DeviceConnectionLog.timestamp >= start_dt)
            .where(DeviceConnectionLog.timestamp < end_dt)
            .order_by(DeviceConnectionLog.id)
        )
        logs = result.scalars().all()

    if not logs:
        return None

    record_count = 0
    with open(file_path, "w", encoding="utf-8") as f:
        for log in logs:
            record = {
                "id": log.id,
                "device_id": log.device_id,
                "event_type": log.event_type or "",
                "ip_address": log.ip_address or "",
                "session_duration_seconds": log.session_duration_seconds,
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            record_count += 1

    sha256 = _compute_sha256(file_path)
    hmac_sig = _compute_hmac(file_path, settings.SECRET_KEY)
    file_size = os.path.getsize(file_path)

    return {
        "log_date": target_date,
        "log_type": "connection",
        "file_path": file_path,
        "record_count": record_count,
        "sha256_hash": sha256,
        "hmac_signature": hmac_sig,
        "file_size_bytes": file_size,
    }


async def _save_signature(sig_data: dict):
    """Imza kaydini DB'ye yaz."""
    async with async_session_factory() as session:
        # Ayni gun + tip için varsa güncelle
        existing = await session.scalar(
            select(LogSignature).where(
                LogSignature.log_date == sig_data["log_date"],
                LogSignature.log_type == sig_data["log_type"],
            )
        )
        if existing:
            existing.file_path = sig_data["file_path"]
            existing.record_count = sig_data["record_count"]
            existing.sha256_hash = sig_data["sha256_hash"]
            existing.hmac_signature = sig_data["hmac_signature"]
            existing.file_size_bytes = sig_data["file_size_bytes"]
        else:
            session.add(LogSignature(**sig_data))
        await session.commit()


async def _cleanup_old_logs():
    """2 yildan eski loglari temizle (DB + dosya)."""
    cutoff = date.today() - timedelta(days=LOG_RETENTION_DAYS)
    cutoff_dt = datetime.combine(cutoff, datetime.min.time())

    async with async_session_factory() as session:
        # Eski DNS loglarını sil
        deleted_dns = await session.execute(
            delete(DnsQueryLog).where(DnsQueryLog.timestamp < cutoff_dt)
        )
        dns_count = deleted_dns.rowcount

        # Eski bağlantı loglarını sil
        deleted_conn = await session.execute(
            delete(DeviceConnectionLog).where(
                DeviceConnectionLog.timestamp < cutoff_dt
            )
        )
        conn_count = deleted_conn.rowcount

        # Eski imza kayitlarini sil (dosyalari da temizle)
        old_sigs = await session.execute(
            select(LogSignature).where(LogSignature.log_date < cutoff)
        )
        file_count = 0
        for sig in old_sigs.scalars().all():
            if sig.file_path and os.path.exists(sig.file_path):
                try:
                    os.remove(sig.file_path)
                    file_count += 1
                except OSError:
                    pass

        await session.execute(
            delete(LogSignature).where(LogSignature.log_date < cutoff)
        )
        await session.commit()

    if dns_count or conn_count or file_count:
        logger.info(
            f"5651 Retention: {dns_count} DNS log, {conn_count} bağlantı log, "
            f"{file_count} arsiv dosyasi silindi (>{LOG_RETENTION_DAYS} gun)"
        )


def _check_disk_usage():
    """Arsiv dizini disk kullanımini kontrol et."""
    total_size = 0
    for dirpath, _, filenames in os.walk(LOG_ARCHIVE_PATH):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                pass
    size_mb = total_size / (1024 * 1024)
    if size_mb > 1024:
        logger.warning(f"5651 Disk: Log arsiv boyutu {size_mb:.0f} MB (>1GB uyari)")
    return size_mb


async def run_daily_signing():
    """Onceki gunun tum loglarını imzala."""
    yesterday = date.today() - timedelta(days=1)
    logger.info(f"5651 Imza: {yesterday} tarihi için imzalama basliyor...")

    _ensure_archive_dir()

    signed_count = 0
    for sign_func in (_sign_dns_logs, _sign_dhcp_logs, _sign_connection_logs):
        try:
            result = await sign_func(yesterday)
            if result:
                await _save_signature(result)
                signed_count += 1
                logger.info(
                    f"5651 Imza: {result['log_type']} - {result['record_count']} kayit, "
                    f"SHA256={result['sha256_hash'][:16]}..."
                )
        except Exception as e:
            logger.error(f"5651 Imza hatasi ({sign_func.__name__}): {e}")

    # Retention temizligi
    try:
        await _cleanup_old_logs()
    except Exception as e:
        logger.error(f"5651 Retention hatasi: {e}")

    # Disk kontrolü
    _check_disk_usage()

    logger.info(f"5651 Imza: {yesterday} tamamlandi ({signed_count} tip imzalandi)")


async def start_log_signer():
    """Log imzalama worker'i - her gun 00:05'te çalışır."""
    logger.info("5651 Log Imzalama Worker başlatildi.")

    # Ilk çalışmada: bugun için onceki gunun loglarını hemen imzala
    # (container yeni baslamissa gecmis gunleri yakala)
    try:
        await run_daily_signing()
    except Exception as e:
        logger.error(f"5651 Ilk imzalama hatasi: {e}")

    while True:
        # Bir sonraki 00:05'i hesapla
        now = datetime.utcnow()
        tomorrow_0005 = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time().replace(hour=0, minute=5),
        )
        wait_seconds = (tomorrow_0005 - now).total_seconds()
        if wait_seconds < 0:
            wait_seconds += 86400  # 24 saat ekle

        logger.info(f"5651 Imza: Sonraki çalışma {wait_seconds/3600:.1f} saat sonra")
        await asyncio.sleep(wait_seconds)

        try:
            await run_daily_signing()
        except Exception as e:
            logger.error(f"5651 Gunluk imzalama hatasi: {e}")
