# --- Ajan: ANALIST (THE ANALYST) ---
# Periyodik LLM DNS log analiz worker'i.
# Son N DNS logunu istatistiksel ozet olarak LLM'e gönderir, bulguları AiInsight olarak yazar.

import asyncio
import json
import logging
import math
import re
import traceback
import time
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func, case

from app.db.session import async_session_factory
from app.models.dns_query_log import DnsQueryLog
from app.models.ai_insight import AiInsight
from app.services import llm_service
from app.services.llm_providers import call_llm

logger = logging.getLogger("tonbilai.llm_log_analyzer")

LOG_ANALYSIS_PROMPT = """Asagida bir ev aginin DNS analiz verileri ve DDoS koruma istatistikleri bulunmaktadir.
Bu verileri analiz et ve bulgu varsa bildir.

Asagidaki veriler istatistiksel ozet formatindadir. Ham log satiri yerine agregat veriler sunulmaktadir.

Kontrol edilecek konular:
1. Şüpheli trafik desenleri (DGA, DNS tuneli, flood)
2. Bilinen zararli domainler, C2 bağlantılari, kripto mining
3. Takip domainleri, gizlilik riskleri
4. Gereksiz tekrarlayan sorgular
5. Belirli cihazlardan gelen anormal trafik
6. DDoS saldırı göstergeleri (yuksek drop sayilari, ani artislar)
7. Yuksek entropi degerine sahip domainler (DGA/DNS-tunnel adaylari)

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

DNS ANALIZ VERILERI:
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


def _shannon_entropy(s: str) -> float:
    """Shannon entropy hesapla (DGA tespiti icin)."""
    if not s:
        return 0.0
    freq = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


async def _build_statistical_summary(interval_minutes: int, max_logs: int) -> str:
    """DNS loglarindan istatistiksel ozet olustur.

    Ham log satirlari yerine agregat veriler LLM'e gonderilir; bu sayede
    token kullanimi %80-90 azalir.
    """
    async with async_session_factory() as session:
        since = datetime.utcnow() - timedelta(minutes=interval_minutes)

        # --- Toplam sorgu ve engelleme sayisi ---
        total_result = await session.execute(
            select(
                func.count(DnsQueryLog.id).label("total"),
                func.sum(case((DnsQueryLog.blocked == True, 1), else_=0)).label("blocked_count"),
            ).where(DnsQueryLog.timestamp >= since)
        )
        total_row = total_result.one()
        total = int(total_row.total or 0)
        blocked_count = int(total_row.blocked_count or 0)
        block_pct = (blocked_count / total * 100) if total else 0.0

        lines = [
            f"DNS ISTATISTIKSEL OZET (son {interval_minutes} dakika):",
            f"Toplam sorgu: {total}, Engellenen: {blocked_count} (%{block_pct:.1f})",
            "",
        ]

        # --- En cok sorgulanan 10 domain ---
        top_domains_result = await session.execute(
            select(DnsQueryLog.domain, func.count(DnsQueryLog.id).label("cnt"))
            .where(DnsQueryLog.timestamp >= since)
            .group_by(DnsQueryLog.domain)
            .order_by(desc("cnt"))
            .limit(10)
        )
        top_domains = top_domains_result.all()
        if top_domains:
            lines.append("EN COK SORGULANAN (Top 10):")
            for i, row in enumerate(top_domains, 1):
                lines.append(f"  {i}. {row.domain} ({row.cnt})")
            lines.append("")

        # --- En cok engellenen 10 domain ---
        top_blocked_result = await session.execute(
            select(DnsQueryLog.domain, func.count(DnsQueryLog.id).label("cnt"))
            .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == True)
            .group_by(DnsQueryLog.domain)
            .order_by(desc("cnt"))
            .limit(10)
        )
        top_blocked = top_blocked_result.all()
        if top_blocked:
            lines.append("EN COK ENGELLENEN (Top 10):")
            for i, row in enumerate(top_blocked, 1):
                lines.append(f"  {i}. {row.domain} ({row.cnt})")
            lines.append("")

        # --- Cihaz dagilimi: top 10 ---
        device_result = await session.execute(
            select(
                DnsQueryLog.device_id,
                func.count(DnsQueryLog.id).label("total"),
                func.sum(case((DnsQueryLog.blocked == True, 1), else_=0)).label("blocked"),
            )
            .where(DnsQueryLog.timestamp >= since)
            .group_by(DnsQueryLog.device_id)
            .order_by(desc("total"))
            .limit(10)
        )
        device_rows = device_result.all()
        if device_rows:
            lines.append("CIHAZ DAGILIMI (Top 10):")
            for row in device_rows:
                lines.append(f"  {row.device_id}: {row.total} sorgu, {int(row.blocked or 0)} engel")
            lines.append("")

        # --- Sorgu tipi dagilimi ---
        qtype_result = await session.execute(
            select(DnsQueryLog.query_type, func.count(DnsQueryLog.id).label("cnt"))
            .where(DnsQueryLog.timestamp >= since)
            .group_by(DnsQueryLog.query_type)
            .order_by(desc("cnt"))
        )
        qtype_rows = qtype_result.all()
        if qtype_rows:
            parts = [f"{row.query_type}: {row.cnt}" for row in qtype_rows if row.query_type]
            if parts:
                lines.append("SORGU TIPLERI:")
                lines.append("  " + ", ".join(parts))
                lines.append("")

        # --- Engelleme sebebi dagilimi ---
        reason_result = await session.execute(
            select(DnsQueryLog.block_reason, func.count(DnsQueryLog.id).label("cnt"))
            .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == True)
            .group_by(DnsQueryLog.block_reason)
            .order_by(desc("cnt"))
        )
        reason_rows = reason_result.all()
        if reason_rows:
            parts = [f"{row.block_reason}: {row.cnt}" for row in reason_rows if row.block_reason]
            if parts:
                lines.append("ENGELLEME SEBEPLERI:")
                lines.append("  " + ", ".join(parts))
                lines.append("")

        # --- Yuksek entropi domainler (DGA adaylari) ---
        # Son 200 izin verilen sorgudan entropy hesapla; >= 3.5 olanlari raporla
        entropy_sample_result = await session.execute(
            select(DnsQueryLog.domain, DnsQueryLog.device_id)
            .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == False)
            .order_by(desc(DnsQueryLog.timestamp))
            .limit(200)
        )
        entropy_rows = entropy_sample_result.all()
        high_entropy = []
        seen_domains: set[str] = set()
        for row in entropy_rows:
            domain = row.domain or ""
            if not domain or domain in seen_domains:
                continue
            seen_domains.add(domain)
            # Sadece subdomain kismindan entropy hesapla (TLD cikar)
            parts = domain.split(".")
            label = parts[0] if len(parts) >= 2 else domain
            ent = _shannon_entropy(label)
            if ent >= 3.5:
                high_entropy.append((domain, ent, row.device_id or "?"))

        # En yuksek entropi degerlerine gore sirala, max 10 goster
        high_entropy.sort(key=lambda x: x[1], reverse=True)
        if high_entropy:
            lines.append("YUKSEK ENTROPILI DOMAINLER (DGA adayi):")
            for domain, ent, device in high_entropy[:10]:
                lines.append(f"  {domain} (entropy={ent:.2f}, cihaz={device})")
            lines.append("")

        return "\n".join(lines)


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
    """LLM'e istatistiksel ozet (veya fallback: ham log satirlari) gonderip analiz sonuçlarini al."""
    if not logs:
        return []

    interval = config.get("log_analysis_interval_minutes", 60)
    max_logs = config.get("log_analysis_max_logs", 100)

    # Oncelikle istatistiksel ozet olusturmaya calis (token tasarrufu %80-90)
    log_data: str
    try:
        log_data = await _build_statistical_summary(interval, max_logs)
        logger.info("LLM analizi: istatistiksel ozet modu kullaniliyor.")
    except Exception as e:
        logger.warning(f"Istatistiksel ozet olusturulamadi, ham log moduna geciliyor: {e}")
        # Fallback: eski ham log satiri formati
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
