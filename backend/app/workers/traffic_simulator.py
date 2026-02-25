# --- Ajan: ANALIST (THE ANALYST) ---
# Gelistirme modunda sahte trafik verisi ureten simulasyon iscisi.
# DNS sorgulari ve trafik loglari veritabanina kaydedilir.
# AI icgoruleri belirli senaryolarda (çocuk-kumar, gece aktivitesi, zararli domain) uretilir.

import asyncio
import random
import logging
from datetime import datetime

from app.services.timezone_service import now_local

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.device import Device
from app.models.traffic_log import TrafficLog
from app.models.ai_insight import AiInsight, Severity
from app.models.dns_query_log import DnsQueryLog
from app.hal.base_driver import BaseNetworkDriver
from app.config import get_settings

logger = logging.getLogger("tonbilai.traffic_simulator")
settings = get_settings()

# Domain-kategori eslesmesi
DOMAIN_CATEGORIES = {
    "youtube.com": "streaming",
    "netflix.com": "streaming",
    "twitch.tv": "streaming",
    "instagram.com": "social",
    "tiktok.com": "social",
    "twitter.com": "social",
    "google.com": "search",
    "bing.com": "search",
    "kumar-sitesi.bet": "gambling",
    "online-casino.com": "gambling",
    "school-portal.edu.tr": "education",
    "khanacademy.org": "education",
    "malware-c2.evil": "malicious",
    "phishing-bank.fake": "malicious",
    "stackoverflow.com": "development",
    "github.com": "development",
}

# DNS sorgusu için ek domainler (reklam/izleyici - engellenmeli)
DNS_EXTRA_DOMAINS = [
    "ad.doubleclick.net", "analytics.tiktok.com", "online-casino.com",
    "analytics.google.com", "telemetry.microsoft.com", "pixel.facebook.com",
    "ad.facebook.com", "weather.com", "wikipedia.org", "reddit.com",
]


async def generate_traffic_entry(device: Device) -> TrafficLog:
    """Bir cihaz için sahte trafik girişi oluştur."""
    domain, category = random.choice(list(DOMAIN_CATEGORIES.items()))
    return TrafficLog(
        device_id=device.id,
        destination_domain=domain,
        category=category,
        bytes_sent=random.randint(1_000, 500_000),
        bytes_received=random.randint(5_000, 5_000_000),
        protocol=random.choice(["TCP", "UDP", "DNS"]),
    )


async def generate_dns_query(device: Device, driver: BaseNetworkDriver) -> DnsQueryLog:
    """Bir cihaz için sahte DNS sorgu logu oluştur."""
    all_domains = list(DOMAIN_CATEGORIES.keys()) + DNS_EXTRA_DOMAINS
    domain = random.choice(all_domains)
    query_type = random.choice(["A", "AAAA", "CNAME"])

    resolution = await driver.resolve_dns(domain, query_type)

    return DnsQueryLog(
        device_id=device.id,
        client_ip=device.ip_address,
        domain=domain,
        query_type=query_type,
        blocked=resolution["blocked"],
        block_reason=resolution.get("block_reason"),
        upstream_response_ms=resolution["response_ms"],
        answer_ip=resolution["answer"],
    )


async def maybe_generate_insight(device: Device, log: TrafficLog) -> AiInsight | None:
    """Trafik desenlerine göre AI icgoruleri uret."""

    # Çocuk cihazi kumar sitesine erisiyor -> KRITIK
    if log.category == "gambling" and device.hostname and "Çocuk" in device.hostname:
        return AiInsight(
            severity=Severity.CRITICAL,
            message=(
                f"UYARI: Çocuk cihazi '{device.hostname}' kumar sitesine "
                f"erisme girişiminde bulundu: {log.destination_domain}"
            ),
            suggested_action=(
                f"{log.destination_domain} adresini {device.hostname} "
                f"ile iliskili profil için engelle"
            ),
            related_device_id=device.id,
            category="security",
        )

    # Elif-Tablet veya Çocuk cihaz kumar sitesine erisiyor -> KRITIK
    if log.category == "gambling" and device.hostname and "Elif" in device.hostname:
        return AiInsight(
            severity=Severity.CRITICAL,
            message=(
                f"UYARI: Çocuk cihazi '{device.hostname}' kumar sitesine "
                f"erisme girişiminde bulundu: {log.destination_domain}"
            ),
            suggested_action=(
                f"{log.destination_domain} adresini {device.hostname} "
                f"ile iliskili profil için engelle"
            ),
            related_device_id=device.id,
            category="security",
        )

    # Gece aktivitesi -> UYARI
    current_hour = now_local().hour
    if current_hour >= 23 or current_hour < 6:
        if random.random() < 0.1:
            return AiInsight(
                severity=Severity.WARNING,
                message=(
                    f"Olagandisi gece aktivitesi: '{device.hostname}' "
                    f"cihazindan {log.destination_domain} erişimi"
                ),
                suggested_action="Cihaz erişim zamanlamaisni gozden gecir",
                related_device_id=device.id,
                category="anomaly",
            )

    # Zararli domain -> KRITIK
    if log.category == "malicious":
        return AiInsight(
            severity=Severity.CRITICAL,
            message=(
                f"GUVENLIK: '{device.hostname}' cihazi şüpheli domaine "
                f"bağlantı kurdu: {log.destination_domain}"
            ),
            suggested_action=(
                f"{log.destination_domain} adresini derhal engelle "
                f"ve cihazi incele"
            ),
            related_device_id=device.id,
            category="security",
        )

    return None


async def start_traffic_simulator(driver: BaseNetworkDriver):
    """Ana trafik simulasyon dongusu (sadece gelistirme modu)."""
    logger.info("Trafik simulatoru başlatildi (gelistirme modu).")

    while True:
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Device).where(Device.is_blocked == False)  # noqa: E712
                )
                devices = result.scalars().all()

                if devices:
                    # Her dongude 3-8 trafik girişi oluştur
                    for _ in range(random.randint(3, 8)):
                        device = random.choice(devices)
                        log = await generate_traffic_entry(device)
                        session.add(log)

                        # Belki bir AI icgorusu oluştur
                        insight = await maybe_generate_insight(device, log)
                        if insight:
                            session.add(insight)
                            logger.info(
                                f"Icgoru oluşturuldu: {insight.message[:60]}..."
                            )

                    # DNS sorgu loglari oluştur (her dongude 5-12 sorgu)
                    for _ in range(random.randint(5, 12)):
                        device = random.choice(devices)
                        dns_log = await generate_dns_query(device, driver)
                        session.add(dns_log)

                    await session.commit()
        except Exception as e:
            logger.error(f"Trafik simulatoru hatasi: {e}")

        await asyncio.sleep(settings.MOCK_TRAFFIC_INTERVAL_SECONDS)
