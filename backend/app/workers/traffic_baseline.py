# --- Ajan: NOBETCI (THE SENTINEL) ---
"""
Traffic Baseline Anomaly Detection Worker

Welford online algorithm ile her metrik için adaptif ortalama ve standart sapma
hesaplar. 3-sigma kuralı ile anomali tespiti yapar ve AiInsight + Telegram
bildirimi gönderir.
"""

import asyncio
import json
import logging
import math
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.db.redis_client import get_redis
from app.db.session import async_session_factory
from app.models.ai_insight import AiInsight
from app.models.dns_query_log import DnsQueryLog
from app.services.telegram_service import notify_ai_insight
from app.services.timezone_service import format_local_time, now_local

logger = logging.getLogger("tonbilai.traffic_baseline")

# ─── Sabitler ──────────────────────────────────────────────────────────────────

POLL_INTERVAL = 10          # saniye
STARTUP_DELAY = 120         # saniye — bandwidth_monitor verisini bekle
PERSIST_EVERY = 60          # örnek sayısı (~10 dakika @ 10s)
Z_THRESHOLD = 3.0           # sigma eşiği — anomali tetikleme
Z_CRITICAL = 5.0            # sigma eşiği — kritik seviye
COOLDOWN_TTL = 1800         # saniye — aynı metrik için tekrar uyarı bekleme süresi
MIN_SAMPLES = 30            # z-score hesabı için minimum örnek sayısı (5 dk @ 10s)

REDIS_WELFORD_PREFIX = "baseline:welford:"
REDIS_COOLDOWN_PREFIX = "baseline:cooldown:"

METRICS = [
    "bw_upload_bps",
    "bw_download_bps",
    "dns_queries_per_min",
    "dns_blocked_per_min",
    "active_flows",
]


# ─── Welford Accumulator ───────────────────────────────────────────────────────

class WelfordAccumulator:
    """
    Welford online algoritması ile tek geçişte ortalama ve varyans hesaplar.
    Tam sayısal istikrar, sıfır harici bağımlılık.
    """

    def __init__(self) -> None:
        self.n: int = 0
        self.mean: float = 0.0
        self.M2: float = 0.0

    def update(self, x: float) -> None:
        """Yeni bir değerle istatistikleri güncelle (Welford online update)."""
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2

    def variance(self) -> float:
        """Örneklem varyansı (n > 1 ise M2/n, aksi hâlde 0)."""
        if self.n > 1:
            return self.M2 / self.n
        return 0.0

    def stddev(self) -> float:
        """Standart sapma."""
        return math.sqrt(self.variance())

    def z_score(self, x: float) -> float:
        """
        Z-skoru hesapla.
        Standart sapma < 1e-9 veya n < MIN_SAMPLES ise 0.0 döndür.
        """
        sd = self.stddev()
        if sd < 1e-9 or self.n < MIN_SAMPLES:
            return 0.0
        return (x - self.mean) / sd

    def to_dict(self) -> dict:
        """Redis'e kalıcı hâle getirmek için serileştir."""
        return {
            "n": self.n,
            "mean": self.mean,
            "M2": self.M2,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WelfordAccumulator":
        """Redis'ten yüklenen dict'ten WelfordAccumulator oluştur."""
        acc = cls()
        try:
            acc.n = int(d.get("n", 0))
            acc.mean = float(d.get("mean", 0.0))
            acc.M2 = float(d.get("M2", 0.0))
        except (TypeError, ValueError) as exc:
            logger.warning("WelfordAccumulator.from_dict parse hatası: %s — sıfırdan başlıyor", exc)
        return acc


# ─── Metrik Okuma Fonksiyonları ────────────────────────────────────────────────

async def _read_bw_metrics(redis) -> tuple[float, float]:
    """
    Redis bw:total HASH'inden upload_bps ve download_bps değerlerini oku.
    Değer yoksa 0.0 döndür.
    """
    try:
        raw = await redis.hgetall("bw:total")
        upload = float(raw.get(b"upload_bps", raw.get("upload_bps", 0)) or 0)
        download = float(raw.get(b"download_bps", raw.get("download_bps", 0)) or 0)
        return upload, download
    except Exception as exc:
        logger.error("Bandwidth metriği okunamadı: %s", exc)
        return 0.0, 0.0


async def _read_dns_metrics() -> tuple[float, float]:
    """
    Son 60 saniyedeki DNS sorgu ve engelleme sayısını veritabanından oku.
    """
    try:
        since = datetime.utcnow() - timedelta(seconds=60)
        async with async_session_factory() as session:
            total_result = await session.execute(
                select(func.count()).select_from(DnsQueryLog).where(
                    DnsQueryLog.timestamp >= since
                )
            )
            blocked_result = await session.execute(
                select(func.count()).select_from(DnsQueryLog).where(
                    DnsQueryLog.timestamp >= since,
                    DnsQueryLog.blocked == True,  # noqa: E712
                )
            )
            total = float(total_result.scalar() or 0)
            blocked = float(blocked_result.scalar() or 0)
            return total, blocked
    except Exception as exc:
        logger.error("DNS metriği okunamadı: %s", exc)
        return 0.0, 0.0


async def _read_active_flows(redis) -> float:
    """
    Redis flow:active_ids SET kardinalitesini oku.
    """
    try:
        count = await redis.scard("flow:active_ids")
        return float(count or 0)
    except Exception as exc:
        logger.error("Active flows metriği okunamadı: %s", exc)
        return 0.0


async def _collect_metrics(redis) -> dict[str, float]:
    """Tüm 5 metriği paralel olarak topla."""
    upload, download = await _read_bw_metrics(redis)
    dns_total, dns_blocked = await _read_dns_metrics()
    flows = await _read_active_flows(redis)

    return {
        "bw_upload_bps": upload,
        "bw_download_bps": download,
        "dns_queries_per_min": dns_total,
        "dns_blocked_per_min": dns_blocked,
        "active_flows": flows,
    }


# ─── Welford Durum Yönetimi (Redis Kalıcılığı) ────────────────────────────────

async def _load_welford_states(redis) -> dict[str, WelfordAccumulator]:
    """
    Soğuk başlangıç önleme: Redis'ten mevcut Welford durumlarını yükle.
    """
    accumulators: dict[str, WelfordAccumulator] = {}
    for metric in METRICS:
        key = f"{REDIS_WELFORD_PREFIX}{metric}"
        try:
            raw = await redis.hgetall(key)
            if raw:
                # bytes veya str anahtarları normalize et
                decoded = {}
                for k, v in raw.items():
                    dk = k.decode() if isinstance(k, bytes) else k
                    dv = v.decode() if isinstance(v, bytes) else v
                    decoded[dk] = dv
                acc = WelfordAccumulator.from_dict(decoded)
                if acc.n > 0:
                    logger.info(
                        "Welford durumu yüklendi — metrik=%s n=%d mean=%.2f",
                        metric, acc.n, acc.mean,
                    )
                    accumulators[metric] = acc
                    continue
        except Exception as exc:
            logger.warning("Welford durumu yüklenemedi — metrik=%s hata=%s", metric, exc)

        accumulators[metric] = WelfordAccumulator()

    return accumulators


async def _persist_welford_states(
    redis, accumulators: dict[str, WelfordAccumulator]
) -> None:
    """
    Tüm Welford durumlarını Redis HASH'e yaz.
    """
    for metric, acc in accumulators.items():
        key = f"{REDIS_WELFORD_PREFIX}{metric}"
        try:
            state = acc.to_dict()
            await redis.hset(key, mapping={k: str(v) for k, v in state.items()})
        except Exception as exc:
            logger.error("Welford durumu kaydedilemedi — metrik=%s hata=%s", metric, exc)


# ─── Anomali Tespiti ve Bildirim ───────────────────────────────────────────────

async def _check_cooldown(redis, metric: str) -> bool:
    """
    Soğuma süresi aktif mi kontrol et.
    True → soğuma aktif (bildirim gönderme).
    False → soğuma yok, bildirim gönderilebilir.
    """
    key = f"{REDIS_COOLDOWN_PREFIX}{metric}"
    try:
        exists = await redis.exists(key)
        return bool(exists)
    except Exception as exc:
        logger.error("Cooldown kontrolü başarısız — metrik=%s hata=%s", metric, exc)
        return True  # Hata durumunda güvenli taraf: bildirimi engelle


async def _set_cooldown(redis, metric: str) -> None:
    """30 dakikalık soğuma süresini başlat."""
    key = f"{REDIS_COOLDOWN_PREFIX}{metric}"
    try:
        await redis.set(key, "1", ex=COOLDOWN_TTL)
    except Exception as exc:
        logger.error("Cooldown ayarlanamadı — metrik=%s hata=%s", metric, exc)


def _build_insight_message(metric: str, value: float, z: float) -> tuple[str, str]:
    """
    Metrik adı ve z-skorundan okunabilir mesaj ve önerilen eylem üret.
    """
    metric_labels = {
        "bw_upload_bps": "Yükleme bant genişliği",
        "bw_download_bps": "İndirme bant genişliği",
        "dns_queries_per_min": "DNS sorgu hızı",
        "dns_blocked_per_min": "DNS engelleme hızı",
        "active_flows": "Aktif bağlantı sayısı",
    }
    metric_units = {
        "bw_upload_bps": "bps",
        "bw_download_bps": "bps",
        "dns_queries_per_min": "sorgu/dk",
        "dns_blocked_per_min": "engelleme/dk",
        "active_flows": "bağlantı",
    }

    label = metric_labels.get(metric, metric)
    unit = metric_units.get(metric, "")
    direction = "yüksek" if z > 0 else "düşük"
    abs_z = abs(z)

    message = (
        f"Trafik anomalisi tespit edildi: {label} anormalden {direction} "
        f"(değer={value:.1f} {unit}, z={abs_z:.1f}σ)"
    )

    suggested_actions = {
        "bw_upload_bps": "Ağ trafiğini inceleyin, olası veri sızıntısı veya bot aktivitesi kontrol edin.",
        "bw_download_bps": "Büyük indirme yapan cihazları kontrol edin, bandwidth limiti uygulayın.",
        "dns_queries_per_min": "DNS flood veya malware C2 iletişimi olabilir. DNS loglarını filtreleyin.",
        "dns_blocked_per_min": "Engellenmiş domain erişim denemeleri artıyor. İlgili cihazı izole edin.",
        "active_flows": "Aşırı bağlantı sayısı tespit edildi. Port taraması veya DDoS saldırısı olabilir.",
    }
    suggested = suggested_actions.get(metric, "Trafik loglarını manuel olarak inceleyin.")

    return message, suggested


async def _handle_anomaly(
    redis,
    metric: str,
    value: float,
    z: float,
) -> None:
    """
    Anomali tespit edildiğinde soğuma kontrolü yap, AiInsight kaydet ve
    Telegram bildirimi gönder.
    """
    in_cooldown = await _check_cooldown(redis, metric)
    if in_cooldown:
        logger.debug(
            "Anomali soğuma süresinde — metrik=%s z=%.2f (bildirim atlandı)",
            metric, z,
        )
        return

    severity = "critical" if abs(z) > Z_CRITICAL else "warning"
    message, suggested_action = _build_insight_message(metric, value, z)

    logger.warning(
        "ANOMALI [%s] metrik=%s değer=%.2f z=%.2f σ",
        severity.upper(), metric, value, z,
    )

    # AiInsight veritabanına yaz
    try:
        async with async_session_factory() as session:
            insight = AiInsight(
                severity=severity,
                message=message,
                suggested_action=suggested_action,
                category="anomaly",
            )
            session.add(insight)
            await session.commit()
    except Exception as exc:
        logger.error("AiInsight kaydedilemedi — metrik=%s hata=%s", metric, exc)

    # Telegram bildirimi gönder
    try:
        await notify_ai_insight(severity=severity, message=message, category="anomaly")
    except Exception as exc:
        logger.error("Telegram bildirimi gönderilemedi — metrik=%s hata=%s", metric, exc)

    # Soğuma süresini başlat
    await _set_cooldown(redis, metric)


# ─── Ana Worker Döngüsü ────────────────────────────────────────────────────────

async def start_traffic_baseline() -> None:
    """
    Trafik baseline anomali tespiti worker'ı.

    120 saniye başlangıç gecikmesiyle başlar (bandwidth_monitor verisini bekler),
    ardından her 10 saniyede bir 5 metriği okur, Welford istatistiklerini
    günceller ve 3-sigma eşiği aşıldığında anomali bildirimi gönderir.
    """
    logger.info(
        "Traffic baseline worker başlatılıyor — %d saniye başlangıç gecikmesi...",
        STARTUP_DELAY,
    )
    await asyncio.sleep(STARTUP_DELAY)
    logger.info("Traffic baseline worker aktif (Welford Z-score adaptif anomali tespiti).")

    # Redis bağlantısı al
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.critical("Redis bağlantısı kurulamadı — worker durduruluyor: %s", exc)
        return

    # Soğuk başlangıç önleme: mevcut Welford durumlarını yükle
    accumulators = await _load_welford_states(redis)

    sample_count = 0

    while True:
        loop_start = asyncio.get_event_loop().time()

        try:
            # ── (a) Mevcut metrikleri oku ───────────────────────────────────
            metrics = await _collect_metrics(redis)

            # ── (b) Welford akümülatörlerini güncelle ───────────────────────
            for metric, value in metrics.items():
                accumulators[metric].update(value)

            sample_count += 1

            # ── (c) Z-skorları hesapla ──────────────────────────────────────
            z_scores: dict[str, float] = {}
            for metric, value in metrics.items():
                z_scores[metric] = accumulators[metric].z_score(value)

            # ── (d) Anomali kontrolü ─────────────────────────────────────────
            for metric, z in z_scores.items():
                if abs(z) > Z_THRESHOLD:
                    await _handle_anomaly(
                        redis=redis,
                        metric=metric,
                        value=metrics[metric],
                        z=z,
                    )

            # ── (e) Her 60 örnekte bir Welford durumunu kalıcı hâle getir ───
            if sample_count % PERSIST_EVERY == 0:
                await _persist_welford_states(redis, accumulators)
                logger.debug(
                    "Welford durumu kaydedildi — örnek sayısı=%d", sample_count
                )

        except asyncio.CancelledError:
            logger.info("Traffic baseline worker iptal edildi — Welford durumu kaydediliyor.")
            await _persist_welford_states(redis, accumulators)
            raise
        except Exception as exc:
            logger.error("Traffic baseline döngü hatası: %s", exc, exc_info=True)

        # Bir sonraki döngüye kadar bekle (işlem süresini dikkate al)
        elapsed = asyncio.get_event_loop().time() - loop_start
        sleep_time = max(0.0, POLL_INTERVAL - elapsed)
        await asyncio.sleep(sleep_time)
