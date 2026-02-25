# --- Ajan: ANALIST (THE ANALYST) ---
# Periyodik LLM DNS log analiz worker'i.
# Son N DNS logunu LLM'e gönderir, bulguları AiInsight olarak yazar.

import asyncio
import json
import logging
import re
import traceback
import time
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func

from app.db.session import async_session_factory
from app.models.dns_query_log import DnsQueryLog
from app.models.ai_insight import AiInsight
from app.services import llm_service
from app.services.llm_providers import call_llm

logger = logging.getLogger("tonbilai.llm_log_analyzer")

LOG_ANALYSIS_PROMPT = """Asagida bir ev aginin son DNS sorgu loglari ve DDoS koruma istatistikleri bulunmaktadir.
Bu verileri analiz et ve bulgu varsa bildir.

Kontrol edilecek konular:
1. Şüpheli trafik desenleri (DGA, DNS tuneli, flood)
2. Bilinen zararli domainler, C2 bağlantılari, kripto mining
3. Takip domainleri, gizlilik riskleri
4. Gereksiz tekrarlayan sorgular
5. Belirli cihazlardan gelen anormal trafik
6. DDoS saldırı göstergeleri (yuksek drop sayilari, ani artislar)

ONEMLI: Yanitini SADECE bir JSON dizisi olarak dondur. Baska açıklama veya yorum EKLEME.
Eger bulgu yoksa sadece [] dondur.

JSON formati:
[
  {{
    "severity": "info",
    "category": "security",
    "message": "Turkce bulgu açıklamasi",
    "suggested_action": "Onerilecek aksiyon"
  }}
]

Gecerli severity degerleri: info, warning, critical
Gecerli category degerleri: security, privacy, optimization, anomaly

DNS LOGLARI:
{log_data}

DDOS KORUMA ISTATISTIKLERI:
{ddos_data}
"""


async def _get_analysis_config() -> dict | None:
    """AI config'ten log analiz ayarlarıni al."""
    config = await llm_service.get_ai_config()
    if not config:
        return None
    if not config.get("enabled") or not config.get("log_analysis_enabled"):
        return None
    if config.get("provider") == "none":
        return None
    return config


async def _fetch_recent_logs(max_logs: int) -> list[dict]:
    """Son N DNS log kaydini getir."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(DnsQueryLog)
                .order_by(desc(DnsQueryLog.timestamp))
                .limit(max_logs)
            )
            logs = result.scalars().all()

            return [
                {
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "",
                    "device_ip": log.device_id or "",
                    "domain": log.domain or "",
                    "query_type": log.query_type or "",
                    "blocked": log.blocked,
                    "block_reason": log.block_reason or "",
                }
                for log in logs
            ]
    except Exception as e:
        logger.error(f"DNS log getirme hatasi: {e}")
        return []


def _parse_findings_json(response_text: str) -> list[dict]:
    """LLM yanitindan bulgu JSON dizisini cikar.
    Gemini bazen markdown code fence icerisinde, bazen duz JSON dondurur.
    Tum olasi formatlar denenir."""
    if not response_text:
        return []

    text = response_text.strip()

    # 1) Markdown code fence içinden cikar: ```json ... ``` veya ``` ... ```
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # 2) Duz JSON olarak parse et
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            # Sadece dict elemanlarini al
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []
    except (json.JSONDecodeError, ValueError):
        pass

    # 3) Metin icerisindeki JSON dizisini bul: [ ... ]
    arr_match = re.search(r'\[[\s\S]*\]', text)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except (json.JSONDecodeError, ValueError):
            pass

    # 4) Metin icerisindeki tek JSON nesnesini bul: { ... }
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            if isinstance(parsed, dict):
                return [parsed]
        except (json.JSONDecodeError, ValueError):
            pass

    logger.warning(f"LLM yaniti JSON olarak parse edilemedi: {text[:300]}")
    return []


async def _fetch_ddos_counters() -> str:
    """DDoS drop counter verilerini metin formatinda getir."""
    try:
        from app.services.ddos_service import get_ddos_drop_summary
        summary = await get_ddos_drop_summary()
        if not summary or summary.get("total_dropped_packets", 0) == 0:
            return "DDoS koruma aktif, engellenen paket yok."

        lines = [f"Toplam engellenen: {summary['total_dropped_packets']} paket, {summary['total_dropped_bytes']} byte"]
        for prot, counters in summary.get("by_protection", {}).items():
            if counters["packets"] > 0:
                lines.append(f"  {prot}: {counters['packets']} paket, {counters['bytes']} byte")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"DDoS counter getirme hatasi: {e}")
        return "DDoS verileri alinamadi."


async def _analyze_logs(config: dict, logs: list[dict]) -> list[dict]:
    """LLM'e loglari ve DDoS verilerini gönderip analiz sonuçlarini al."""
    if not logs:
        return []

    # Log verisini metin formatina donustur
    log_lines = []
    for log in logs:
        status = "ENGEL" if log["blocked"] else "IZIN"
        reason = f" ({log['block_reason']})" if log["block_reason"] else ""
        log_lines.append(
            f"{log['timestamp']} | {log['device_ip']} | {log['domain']} | "
            f"{log['query_type']} | {status}{reason}"
        )
    log_data = "\n".join(log_lines)

    # DDoS counter verilerini al
    ddos_data = await _fetch_ddos_counters()

    prompt = LOG_ANALYSIS_PROMPT.format(log_data=log_data, ddos_data=ddos_data)

    messages = [
        {"role": "system", "content": "Sen bir ag güvenlik analizcisisin. DNS loglarını analiz edip SADECE JSON formatinda bulgu dondur. Baska açıklama ekleme."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await call_llm(
            provider=config["provider"],
            messages=messages,
            model=config.get("model") or "",
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=0.1,
            max_tokens=config.get("max_tokens", 1024),
        )
    except Exception as e:
        logger.error(f"LLM API cagri hatasi: {e}")
        return []

    if not response:
        logger.warning("LLM yanit bos dondu.")
        return []

    logger.info(f"LLM yanit alindi ({len(response)} karakter)")

    # JSON parse (kendi robust parser'imiz)
    findings = _parse_findings_json(response)

    # Gecerlilik kontrolü: her bulgunun message alani olmali
    valid = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        msg = f.get("message", "")
        if not msg or not isinstance(msg, str):
            continue
        # severity ve category normalize et
        sev = f.get("severity", "info")
        if sev not in ("info", "warning", "critical"):
            f["severity"] = "info"
        cat = f.get("category", "security")
        if cat not in ("security", "privacy", "optimization", "anomaly"):
            f["category"] = "security"
        valid.append(f)

    logger.info(f"LLM analiz sonuçu: {len(valid)} gecerli bulgu (toplam parse: {len(findings)})")
    return valid


async def _write_findings(findings: list[dict]):
    """Bulgulari AiInsight tablosuna yaz ve Telegram bildirimi gönder."""
    if not findings:
        return

    written = 0
    try:
        async with async_session_factory() as session:
            for finding in findings:
                message = finding.get("message", "")
                if not message:
                    continue

                severity = finding.get("severity", "info")
                category = finding.get("category", "security")
                action = finding.get("suggested_action", "")

                insight = AiInsight(
                    timestamp=datetime.utcnow(),
                    severity=severity,
                    message=f"[LLM Analiz] {message}",
                    suggested_action=action,
                    category=category,
                )
                session.add(insight)
                written += 1

            await session.commit()
            logger.info(f"LLM log analizi: {written} bulgu DB'ye yazildi.")

    except Exception as e:
        logger.error(f"LLM bulgu yazma hatasi: {e}")

    # Telegram bildirimi (DB işleminden bagimsiz)
    try:
        from app.services.telegram_service import notify_ai_insight
        for finding in findings:
            msg = finding.get("message", "")
            if msg:
                await notify_ai_insight(
                    severity=finding.get("severity", "info"),
                    message=f"[LLM Analiz] {msg}",
                    category=finding.get("category", "security"),
                )
    except Exception as e:
        logger.error(f"LLM analiz Telegram bildirimi hatasi: {e}")


async def start_llm_log_analyzer():
    """Periyodik LLM DNS log analiz dongusu."""
    logger.info("LLM Log Analyzer worker başlatiliyor...")

    # Başlangicta 60 saniye bekle (diger worker'lar yuklensin)
    await asyncio.sleep(60)

    while True:
        try:
            config = await _get_analysis_config()
            if not config:
                # Devre disi veya ayarlanmamis, 60 sn sonra tekrar kontrol
                await asyncio.sleep(60)
                continue

            interval = config.get("log_analysis_interval_minutes", 60)
            max_logs = config.get("log_analysis_max_logs", 100)

            logger.info(f"LLM log analizi basliyor ({max_logs} log, {interval} dk aralık)...")

            # Son loglari getir
            logs = await _fetch_recent_logs(max_logs)

            if logs:
                # LLM analiz
                findings = await _analyze_logs(config, logs)

                # Bulgulari yaz
                await _write_findings(findings)

                # Gunluk sayacı artir
                await llm_service._increment_daily_counter()
            else:
                logger.info("LLM log analizi: analiz edilecek log bulunamadı.")

            # Bir sonraki analiz için bekle
            await asyncio.sleep(interval * 60)

        except asyncio.CancelledError:
            logger.info("LLM Log Analyzer worker durduruluyor...")
            break
        except Exception as e:
            logger.error(f"LLM Log Analyzer hatasi: {e}\n{traceback.format_exc()}")
            # Hata durumunda normal aralık kadar bekle (5dk degil)
            await asyncio.sleep(interval * 60 if 'interval' in dir() else 3600)
