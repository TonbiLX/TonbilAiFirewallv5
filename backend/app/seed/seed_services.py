# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# AdGuard HostlistsRegistry'den servis tanimlarini indir ve
# blocked_services tablosuna + Redis'e yukle.

import logging

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.blocked_service import BlockedService

logger = logging.getLogger("tonbilai.seed_services")

SERVICES_URL = (
    "https://adguardteam.github.io/HostlistsRegistry/assets/services.json"
)

# Grup isimlerinin Turkce karsiliklari
GROUP_NAMES_TR = {
    "ai": "Yapay Zeka",
    "cdn": "CDN",
    "dating": "Tanisma",
    "gambling": "Kumar",
    "gaming": "Oyun",
    "hosting": "Hosting",
    "messenger": "Mesajlasma",
    "privacy": "Gizlilik",
    "shopping": "Alisveris",
    "social_network": "Sosyal Ag",
    "software": "Yazilim",
    "streaming": "Yayin",
}


def parse_rule_to_domain(rule: str) -> str | None:
    """AdBlock kural formatini domain'e cevir.
    ||domain.com^ -> domain.com
    |exactprefix^ -> exactprefix (bazi CDN pattern'leri için)
    """
    rule = rule.strip()
    if rule.startswith("||") and rule.endswith("^"):
        return rule[2:-1].lower()
    if rule.startswith("|") and rule.endswith("^") and not rule.startswith("||"):
        candidate = rule[1:-1].lower()
        # Wildcard iceren CDN pattern'lerini atla
        if "*" in candidate:
            return None
        return candidate
    return None


async def seed_blocked_services(redis_client: aioredis.Redis):
    """AdGuard services.json indir, DB ve Redis'e yukle."""
    try:
        logger.info("Servis tanimlari indiriliyor...")
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True
        ) as client:
            resp = await client.get(SERVICES_URL)
            resp.raise_for_status()
            data = resp.json()

        services = data.get("blocked_services", [])
        logger.info(f"{len(services)} servis indirildi")

        async with async_session_factory() as session:
            seeded = 0
            all_domains = []  # Tum servislerin domain'lerini topla
            for svc in services:
                service_id = svc.get("id", "")
                if not service_id:
                    continue

                rules = svc.get("rules", [])
                domains = []
                for r in rules:
                    d = parse_rule_to_domain(r)
                    if d:
                        domains.append(d)

                # Upsert
                existing = (
                    await session.execute(
                        select(BlockedService).where(
                            BlockedService.service_id == service_id
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.name = svc.get("name", service_id)
                    existing.group_name = svc.get("group", "other")
                    existing.icon_svg = svc.get("icon_svg", "")
                    existing.rules = rules
                    existing.domain_count = len(domains)
                else:
                    bs = BlockedService(
                        service_id=service_id,
                        name=svc.get("name", service_id),
                        group_name=svc.get("group", "other"),
                        icon_svg=svc.get("icon_svg", ""),
                        rules=rules,
                        domain_count=len(domains),
                    )
                    session.add(bs)
                    seeded += 1

                # Redis'e servis domain'lerini yukle
                redis_key = f"dns:service_domains:{service_id}"
                await redis_client.delete(redis_key)
                if domains:
                    await redis_client.sadd(redis_key, *domains)
                    # Tum servis domain'lerini birlesik SET'e ekle
                    all_domains.extend(domains)

            await session.commit()

            # Tum servis domain'lerini tek SET'e yukle (global blocklist'ten once kontrol için)
            await redis_client.delete("dns:all_service_domains")
            if all_domains:
                await redis_client.sadd("dns:all_service_domains", *all_domains)
                logger.info(
                    f"Toplam {len(all_domains)} servis domain'i "
                    f"dns:all_service_domains SET'ine yuklendi"
                )
            logger.info(
                f"Servis seed tamamlandi: {seeded} yeni, "
                f"{len(services)} toplam servis"
            )

    except httpx.HTTPError as e:
        logger.error(f"Servis tanimlari indirilemedi: {e}")
    except Exception as e:
        logger.error(f"Servis seed hatasi: {e}")
