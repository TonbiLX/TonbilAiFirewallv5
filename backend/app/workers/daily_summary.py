# --- Ajan: MUHABIR (THE REPORTER) ---
# Gunluk Telegram guvenlik ozeti worker'i.
# Her sabah 08:00 yerel saatte 24 saatlik istatistikleri toplar ve raporlar.

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc

from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.ai_insight import AiInsight
from app.models.device import Device
from app.models.device_traffic_snapshot import DeviceTrafficSnapshot
from app.models.dns_query_log import DnsQueryLog
from app.services.telegram_service import notify_hourly_summary, send_message
from app.services.timezone_service import format_local_time, now_local

logger = logging.getLogger("tonbilai.daily_summary")


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------


def _format_bytes(b: int) -> str:
    """Byte degerini insan okunakli formata cevir (KB/MB/GB)."""
    if b is None or b < 0:
        b = 0
    if b < 1024:
        return f"{b} B"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    else:
        return f"{b / 1024 ** 3:.2f} GB"


async def _get_dns_stats_24h() -> dict:
    """Son 24 saatin DNS istatistiklerini veritabanindan topla."""
    cutoff = now_local() - timedelta(hours=24)
    # now_local() timezone-aware dondurur; DB'deki timestamp timezone-naive olabilir
    cutoff_naive = cutoff.replace(tzinfo=None)

    try:
        async with async_session_factory() as session:
            # Toplam sorgu sayisi
            total_result = await session.execute(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= cutoff_naive
                )
            )
            total_queries = total_result.scalar() or 0

            # Engellenen sorgu sayisi
            blocked_result = await session.execute(
                select(func.count(DnsQueryLog.id)).where(
                    DnsQueryLog.timestamp >= cutoff_naive,
                    DnsQueryLog.blocked == True,
                )
            )
            blocked_queries = blocked_result.scalar() or 0

            # Aktif cihaz sayisi (distinct device_id)
            active_result = await session.execute(
                select(func.count(func.distinct(DnsQueryLog.device_id))).where(
                    DnsQueryLog.timestamp >= cutoff_naive,
                    DnsQueryLog.device_id.isnot(None),
                )
            )
            active_devices = active_result.scalar() or 0

            # En aktif 5 cihaz (device_id bazli, hostname join ile)
            top_devices_raw = await session.execute(
                select(
                    DnsQueryLog.device_id,
                    func.count(DnsQueryLog.id).label("query_count"),
                )
                .where(
                    DnsQueryLog.timestamp >= cutoff_naive,
                    DnsQueryLog.device_id.isnot(None),
                )
                .group_by(DnsQueryLog.device_id)
                .order_by(desc("query_count"))
                .limit(5)
            )
            top_devices_rows = top_devices_raw.fetchall()

            # Hostname cozumleme
            top_devices = []
            for row in top_devices_rows:
                device_id, query_count = row
                hostname_result = await session.execute(
                    select(Device.hostname, Device.ip_address).where(
                        Device.id == device_id
                    )
                )
                dev = hostname_result.first()
                if dev:
                    label = dev.hostname or dev.ip_address or f"ID:{device_id}"
                else:
                    label = f"ID:{device_id}"
                top_devices.append({"label": label, "count": query_count})

            # En cok engellenen 5 domain
            top_blocked_raw = await session.execute(
                select(
                    DnsQueryLog.domain,
                    func.count(DnsQueryLog.id).label("block_count"),
                )
                .where(
                    DnsQueryLog.timestamp >= cutoff_naive,
                    DnsQueryLog.blocked == True,
                )
                .group_by(DnsQueryLog.domain)
                .order_by(desc("block_count"))
                .limit(5)
            )
            top_blocked = [
                {"domain": row.domain, "count": row.block_count}
                for row in top_blocked_raw.fetchall()
            ]

        block_rate = (blocked_queries / total_queries * 100) if total_queries > 0 else 0.0

        return {
            "total_queries": total_queries,
            "blocked_queries": blocked_queries,
            "block_rate": round(block_rate, 1),
            "active_devices": active_devices,
            "top_devices": top_devices,
            "top_blocked": top_blocked,
        }

    except Exception as e:
        logger.error(f"DNS istatistikleri alinamadi: {e}")
        return {
            "total_queries": 0,
            "blocked_queries": 0,
            "block_rate": 0.0,
            "active_devices": 0,
            "top_devices": [],
            "top_blocked": [],
        }


async def _get_traffic_stats_24h() -> dict:
    """Son 24 saatin trafik istatistiklerini veritabanindan topla."""
    cutoff = now_local() - timedelta(hours=24)
    cutoff_naive = cutoff.replace(tzinfo=None)

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(
                    func.sum(DeviceTrafficSnapshot.upload_bytes).label("total_upload"),
                    func.sum(DeviceTrafficSnapshot.download_bytes).label("total_download"),
                ).where(
                    DeviceTrafficSnapshot.timestamp >= cutoff_naive,
                )
            )
            row = result.first()
            total_upload = row.total_upload or 0
            total_download = row.total_download or 0

        return {
            "total_upload_bytes": total_upload,
            "total_download_bytes": total_download,
            "total_upload_human": _format_bytes(total_upload),
            "total_download_human": _format_bytes(total_download),
        }

    except Exception as e:
        logger.error(f"Trafik istatistikleri alinamadi: {e}")
        return {
            "total_upload_bytes": 0,
            "total_download_bytes": 0,
            "total_upload_human": "0 B",
            "total_download_human": "0 B",
        }


async def _get_welford_status() -> dict:
    """Redis'ten Welford baseline istatistiklerini oku."""
    try:
        redis = await get_redis()
        keys = await redis.keys("baseline:welford:*")

        metrics = {}
        for key in keys:
            raw_key = key if isinstance(key, str) else key.decode("utf-8")
            metric_name = raw_key.replace("baseline:welford:", "")

            data = await redis.hgetall(raw_key)
            if not data:
                continue

            # hgetall bytes veya str dondurebilir
            decoded = {}
            for k, v in data.items():
                dk = k if isinstance(k, str) else k.decode("utf-8")
                dv = v if isinstance(v, str) else v.decode("utf-8")
                decoded[dk] = dv

            mean = float(decoded.get("mean", 0))
            stddev = float(decoded.get("stddev", 0))
            metrics[metric_name] = {"mean": mean, "stddev": stddev}

        return {"metrics": metrics, "available": len(metrics) > 0}

    except Exception as e:
        logger.warning(f"Welford baseline okunamadi: {e}")
        return {"metrics": {}, "available": False}


async def _get_anomaly_count_24h() -> int:
    """Son 24 saatteki anomali sayisini veritabanindan getir."""
    cutoff = now_local() - timedelta(hours=24)
    cutoff_naive = cutoff.replace(tzinfo=None)

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count(AiInsight.id)).where(
                    AiInsight.category == "anomaly",
                    AiInsight.timestamp >= cutoff_naive,
                )
            )
            return result.scalar() or 0

    except Exception as e:
        logger.error(f"Anomali sayisi alinamadi: {e}")
        return 0


# ---------------------------------------------------------------------------
# Guncelleme: Saglik durumu tespiti
# ---------------------------------------------------------------------------


def _determine_health_status(block_rate: float, anomaly_count: int) -> tuple[str, str]:
    """Genel saglik durumunu belirle.

    Returns:
        (status_key, display_text): ornegin ("green", "NORMAL")
    """
    if block_rate > 30 or anomaly_count > 15:
        return ("red", "KRITIK")
    elif block_rate > 15 or anomaly_count > 5:
        return ("yellow", "DIKKAT")
    else:
        return ("green", "NORMAL")


def _health_emoji(status_key: str) -> str:
    """Saglik durumuna gore emoji sec."""
    return {
        "green": "\U0001f7e2",   # yesil daire
        "yellow": "\U0001f7e1",  # sari daire
        "red": "\U0001f534",     # kirmizi daire
    }.get(status_key, "\U0001f535")


# ---------------------------------------------------------------------------
# Detayli HTML mesaj olusturma
# ---------------------------------------------------------------------------


def _build_detailed_message(
    dns: dict,
    traffic: dict,
    ddos: dict,
    welford: dict,
    anomaly_count: int,
) -> str:
    """Gunluk ozet icin detayli HTML mesaji olustur."""

    # DNS bolumu
    block_rate = dns["block_rate"]
    if block_rate > 30:
        rate_emoji = "\U0001f534"
    elif block_rate > 15:
        rate_emoji = "\U0001f7e0"
    else:
        rate_emoji = "\U0001f7e2"

    dns_section = (
        "\U0001f4e8 <b>DNS İstatistikleri (24 saat)</b>\n"
        f"• Toplam sorgu: {dns['total_queries']:,}\n"
        f"• Engellenen: {dns['blocked_queries']:,} ({rate_emoji} %{block_rate:.1f})\n"
        f"• Aktif cihaz: {dns['active_devices']}"
    )

    # En aktif cihazlar bolumu
    if dns["top_devices"]:
        lines = []
        for i, item in enumerate(dns["top_devices"], 1):
            lines.append(f"{i}. {item['label']} ({item['count']:,} sorgu)")
        top_devices_section = "\U0001f3c6 <b>En Aktif Cihazlar</b>\n" + "\n".join(lines)
    else:
        top_devices_section = "\U0001f3c6 <b>En Aktif Cihazlar</b>\n• Veri yok"

    # En cok engellenen domainler bolumu
    if dns["top_blocked"]:
        lines = []
        for i, item in enumerate(dns["top_blocked"], 1):
            lines.append(f"{i}. {item['domain']} ({item['count']:,})")
        top_blocked_section = "\U0001f6ab <b>En Çok Engellenen</b>\n" + "\n".join(lines)
    else:
        top_blocked_section = "\U0001f6ab <b>En Çok Engellenen</b>\n• Veri yok"

    # Trafik bolumu
    traffic_section = (
        "\U0001f4e1 <b>Trafik Özeti</b>\n"
        f"• Upload: {traffic['total_upload_human']}\n"
        f"• Download: {traffic['total_download_human']}"
    )

    # DDoS bolumu
    total_dropped = ddos.get("total_dropped_packets", 0)
    total_dropped_bytes = ddos.get("total_dropped_bytes", 0)
    by_prot = ddos.get("by_protection", {})

    ddos_lines = [
        "\U0001f6e1 <b>DDoS Durumu</b>",
        f"• Engellenen: {total_dropped:,} paket ({_format_bytes(total_dropped_bytes)})",
    ]
    if by_prot:
        for prot_name, counters in list(by_prot.items())[:3]:
            pkt = counters.get("packets", 0)
            if pkt > 0:
                ddos_lines.append(f"  - {prot_name}: {pkt:,} paket")
    ddos_section = "\n".join(ddos_lines)

    # Welford / anomali bolumu
    anomaly_lines = [
        "\U0001f4c8 <b>Anomali Tespiti (Welford)</b>",
        f"• Son 24 saatte: {anomaly_count} anomali",
    ]
    if welford["available"]:
        metrics = welford["metrics"]
        # BW upload ve download vurgula
        for key in ("bw_upload", "bw_download", "bw_total"):
            if key in metrics:
                m = metrics[key]
                label = {
                    "bw_upload": "BW Upload ort",
                    "bw_download": "BW Download ort",
                    "bw_total": "BW Toplam ort",
                }.get(key, key)
                # bps → Mbps donusumu (eger ham deger bps ise)
                mean_mbps = m["mean"] / 1_000_000 if m["mean"] > 1_000 else m["mean"]
                std_mbps = m["stddev"] / 1_000_000 if m["stddev"] > 1_000 else m["stddev"]
                anomaly_lines.append(
                    f"• {label}: {mean_mbps:.1f} Mbps (\u03c3={std_mbps:.1f})"
                )
    else:
        anomaly_lines.append("• Baseline verisi henuz olusturulmadi")
    anomaly_section = "\n".join(anomaly_lines)

    # Genel saglik durumu
    health_key, health_text = _determine_health_status(block_rate, anomaly_count)
    health_emoji = _health_emoji(health_key)
    health_section = f"{health_emoji} <b>Genel Durum: {health_text}</b>"

    separator = "\u2501" * 21

    message = (
        "\U0001f4ca <b>GÜNLÜK GÜVENLİK ÖZETİ</b>\n"
        f"{separator}\n"
        "\n"
        f"{dns_section}\n"
        "\n"
        f"{top_devices_section}\n"
        "\n"
        f"{top_blocked_section}\n"
        "\n"
        f"{traffic_section}\n"
        "\n"
        f"{ddos_section}\n"
        "\n"
        f"{anomaly_section}\n"
        "\n"
        f"{health_section}\n"
        "\n"
        f"\U0001f550 {format_local_time()}\n"
        "\U0001f6e1 TonbilAiOS Günlük Rapor"
    )
    return message


# ---------------------------------------------------------------------------
# Ana worker dongusu
# ---------------------------------------------------------------------------


async def start_daily_summary() -> None:
    """Gunluk ozet worker'ini baslat.

    Her gun 08:00 yerel saatte calisir, gecen 24 saatin DNS,
    trafik, DDoS ve anomali istatistiklerini Telegram'a gonder.
    """
    logger.info("Gunluk ozet worker'i baslatildi.")

    while True:
        try:
            # 08:00 yerel saate kadar bekle
            now = now_local()
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()

            logger.info(
                f"Sonraki gunluk ozet: {target.strftime('%d/%m/%Y %H:%M')} "
                f"({wait_seconds / 3600:.1f} saat sonra)"
            )
            await asyncio.sleep(wait_seconds)

        except asyncio.CancelledError:
            logger.info("Gunluk ozet worker'i durduruldu (bekleme asamasi).")
            return
        except Exception as e:
            logger.error(f"Bekleme hesaplama hatasi: {e}")
            # Bir sonraki girisimde 1 saat bekle
            await asyncio.sleep(3600)
            continue

        # 08:00 oldu — ozeti hazirla ve gonder
        logger.info("Gunluk guvenlik ozeti hazirlaniyor...")
        try:
            await _run_daily_summary()
        except asyncio.CancelledError:
            logger.info("Gunluk ozet worker'i durduruldu (ozet asamasi).")
            return
        except Exception as e:
            logger.error(f"Gunluk ozet gonderilemedi: {e}")

        # Bir sonraki tetiklemeyi 24 saat sonraya ayarla
        # (kucuk sapmalari dengelemek icin loop basi yeniden hesaplanir)
        await asyncio.sleep(60)  # Ayni dakika icinde tekrar tetiklenmeyi onle


async def _run_daily_summary() -> None:
    """Tek bir ozet dongusu: veri topla, formatlayip gonder."""

    # 1. DNS istatistikleri
    dns_stats = await _get_dns_stats_24h()
    logger.debug(
        f"DNS stats: toplam={dns_stats['total_queries']}, "
        f"engellenen={dns_stats['blocked_queries']}, "
        f"oran=%{dns_stats['block_rate']}"
    )

    # 2. Trafik istatistikleri
    traffic_stats = await _get_traffic_stats_24h()
    logger.debug(
        f"Trafik stats: upload={traffic_stats['total_upload_human']}, "
        f"download={traffic_stats['total_download_human']}"
    )

    # 3. DDoS ozeti
    ddos_summary: dict = {}
    try:
        from app.services.ddos_service import get_ddos_drop_summary
        ddos_summary = await get_ddos_drop_summary()
        logger.debug(
            f"DDoS stats: {ddos_summary.get('total_dropped_packets', 0)} paket engellendi"
        )
    except Exception as e:
        logger.warning(f"DDoS ozeti alinamadi: {e}")

    # 4. Welford baseline durumu
    welford_status = await _get_welford_status()

    # 5. Anomali sayisi
    anomaly_count = await _get_anomaly_count_24h()
    logger.debug(f"Son 24h anomali sayisi: {anomaly_count}")

    # 6. notify_hourly_summary ile ozet gonder (mevcut fonksiyonu yeniden kullan)
    top_devices_lines = []
    for i, item in enumerate(dns_stats["top_devices"], 1):
        top_devices_lines.append(f"{i}. {item['label']} ({item['count']:,} sorgu)")
    top_devices_text = "\n".join(top_devices_lines) if top_devices_lines else "-"

    top_blocked_lines = []
    for i, item in enumerate(dns_stats["top_blocked"], 1):
        top_blocked_lines.append(f"{i}. {item['domain']} ({item['count']:,})")
    top_blocked_text = "\n".join(top_blocked_lines) if top_blocked_lines else "-"

    summary_stats = {
        "total_queries": dns_stats["total_queries"],
        "blocked_queries": dns_stats["blocked_queries"],
        "block_rate": dns_stats["block_rate"],
        "active_devices": dns_stats["active_devices"],
        "top_devices_text": top_devices_text,
        "top_blocked_text": top_blocked_text,
    }
    await notify_hourly_summary(summary_stats)

    # 7. Detayli HTML mesaj gonder
    detailed_msg = _build_detailed_message(
        dns=dns_stats,
        traffic=traffic_stats,
        ddos=ddos_summary,
        welford=welford_status,
        anomaly_count=anomaly_count,
    )
    sent = await send_message(detailed_msg, use_html=True)
    if sent:
        logger.info("Gunluk guvenlik ozeti basariyla gonderildi.")
    else:
        logger.warning(
            "Gunluk guvenlik ozeti gonderilemedi "
            "(Telegram yapilandirmasi eksik veya devre disi olabilir)."
        )
