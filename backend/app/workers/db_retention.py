# --- Ajan: TEMIZLIKCI (THE JANITOR) ---
# Veritabani retention worker — eski kayitlari periyodik olarak temizler.
# Her 6 saatte bir calisir; batch DELETE kullanarak DB yukunu minimize eder.

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from app.db.session import async_session_factory

logger = logging.getLogger("tonbilai.db_retention")

# Retention sureleri (gun)
RETENTION_DAYS = {
    "connection_flows":    7,
    "dns_query_logs":      14,
    "traffic_logs":        30,
    "ip_reputation_checks": 30,
    "ip_blacklist_entries": 7,
}

# Her tablodaki timestamp sutun isimleri
TIMESTAMP_COLUMNS = {
    "connection_flows":    "first_seen",
    "dns_query_logs":      "timestamp",
    "traffic_logs":        "timestamp",
    "ip_reputation_checks": "checked_at",
    "ip_blacklist_entries": "fetched_at",
}

BATCH_SIZE     = 10_000  # Her seferde silinecek maksimum satir
PURGE_INTERVAL = 6 * 3600  # 6 saat (saniye)


async def purge_old_records():
    """
    Tanim: Tum retention tablolarinda eskimis kayitlari batch halinde siler.
    Tek seferde tum satiri silmez; LIMIT kullanarak DB'yi asiri yuklememek icin
    batch'ler arasinda 1 saniye bekler.
    """
    try:
        async with async_session_factory() as session:
            for table, days in RETENTION_DAYS.items():
                col = TIMESTAMP_COLUMNS[table]
                cutoff = datetime.utcnow() - timedelta(days=days)
                total_deleted = 0

                while True:
                    result = await session.execute(
                        text(
                            f"DELETE FROM `{table}` "
                            f"WHERE `{col}` < :cutoff "
                            f"LIMIT :batch"
                        ),
                        {"cutoff": cutoff, "batch": BATCH_SIZE},
                    )
                    await session.commit()
                    deleted = result.rowcount
                    total_deleted += deleted

                    if deleted < BATCH_SIZE:
                        # Son batch — tamamlandi
                        break

                    # Batch'ler arasi kisa mola (SD kart/DB yuku azalt)
                    await asyncio.sleep(1)

                if total_deleted > 0:
                    logger.info(
                        f"DB retention: `{table}` tablosundan {total_deleted:,} "
                        f"eski kayit silindi ({days} gunluk retention)"
                    )
                else:
                    logger.debug(
                        f"DB retention: `{table}` tablosunda silinecek kayit yok "
                        f"(cutoff: {cutoff.strftime('%Y-%m-%d %H:%M')})"
                    )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"DB retention purge hatasi: {e}", exc_info=True)


async def start_db_retention_worker():
    """
    Ana worker dongusu.
    Baslangicta 60 saniye bekler (startup tamamlansin),
    ardindan her 6 saatte bir purge_old_records() calistirir.
    """
    logger.info(
        "DB retention worker baslatildi — "
        f"connection_flows:{RETENTION_DAYS['connection_flows']}g, "
        f"dns_query_logs:{RETENTION_DAYS['dns_query_logs']}g, "
        f"traffic_logs:{RETENTION_DAYS['traffic_logs']}g | "
        f"interval: {PURGE_INTERVAL // 3600}sa"
    )

    # Ilk calistirmada startup'in bitmesini bekle
    await asyncio.sleep(60)

    while True:
        try:
            await purge_old_records()
        except asyncio.CancelledError:
            logger.info("DB retention worker durduruldu")
            break
        except Exception as e:
            logger.error(f"DB retention worker dongu hatasi: {e}", exc_info=True)

        try:
            await asyncio.sleep(PURGE_INTERVAL)
        except asyncio.CancelledError:
            logger.info("DB retention worker durduruldu")
            break
