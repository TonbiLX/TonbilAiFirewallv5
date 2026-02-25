# --- Ajan: ANALIST (THE ANALYST) ---
# AI Sohbet API: NLP motoru ile Turkce dogal dil anlama.
# TF-IDF intent siniflandirma + fuzzy entity cikarma + coklu komut desteği.
# Cihaz alias sistemi, akilli cihaz cozumleme, iliski bazli eslestirme.

import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user, escape_like
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update

from app.db.session import get_db
from app.models.chat_message import ChatMessage
from app.models.device import Device
from app.models.profile import Profile
from app.models.dns_rule import DnsRule, DnsRuleType
from app.models.firewall_rule import FirewallRule
from app.models.blocklist import Blocklist
from app.models.ai_insight import AiInsight
from app.models.content_category import ContentCategory
from app.models.vpn_client import VpnClientServer
from app.models.vpn_peer import VpnConfig
from app.models.dhcp_pool import DhcpPool
from app.models.dhcp_lease import DhcpLease
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse
from app.models.dns_query_log import DnsQueryLog
from app.models.device_custom_rule import DeviceCustomRule, DeviceCustomRuleType
from app.models.blocked_service import BlockedService
from app.models.device_blocked_service import DeviceBlockedService
from app.api.v1.device_custom_rules import sync_device_custom_rules_to_redis
from app.api.v1.services import sync_device_services_to_redis
from app.db.redis_client import get_redis
from app.services import chat_formatter as fmt
from app.services.ai_engine import (
    get_engine, ParsedCommand, Entity, SERVICE_DOMAINS,
    load_aliases, add_alias, remove_alias, find_device_by_alias,
    normalize_turkish, levenshtein_ratio, fuzzy_match_best,
    extract_relationship_and_device_type, extract_time_reference,
    RELATIONSHIP_KEYWORDS, DEVICE_TYPE_KEYWORDS,
)
from app.services import llm_service

import logging
from typing import List

logger = logging.getLogger("tonbilai.chat")

router = APIRouter()


# =====================================================================
# DB Context: Cihaz, profil, kategori isimlerini NLP motoruna besle
# =====================================================================

async def _build_db_context(db: AsyncSession) -> dict:
    """NLP motorunun entity eslestirme için ihtiyac duydugu DB verisini topla."""
    # Cihazlar
    devices_result = await db.execute(select(Device))
    devices = [
        {"id": d.id, "hostname": d.hostname or "", "ip_address": d.ip_address,
         "manufacturer": d.manufacturer or "", "is_blocked": d.is_blocked}
        for d in devices_result.scalars().all()
    ]
    # Profiller
    profiles_result = await db.execute(select(Profile))
    profiles = [
        {"id": p.id, "name": p.name, "profile_type": p.profile_type}
        for p in profiles_result.scalars().all()
    ]
    # Kategoriler
    cats_result = await db.execute(select(ContentCategory))
    categories = [
        {"id": c.id, "key": c.key, "name": c.name, "enabled": c.enabled}
        for c in cats_result.scalars().all()
    ]
    # Firewall kurallari (LLM dinamik baglam için)
    fw_result = await db.execute(select(FirewallRule).where(FirewallRule.enabled == True))  # noqa: E712
    firewall_rules = [
        {"id": r.id, "name": r.name, "port": r.port,
         "protocol": r.protocol.value if hasattr(r.protocol, "value") else str(r.protocol),
         "action": r.action.value if hasattr(r.action, "value") else str(r.action),
         "direction": r.direction.value if hasattr(r.direction, "value") else str(r.direction),
         "enabled": r.enabled}
        for r in fw_result.scalars().all()
    ]
    return {"devices": devices, "profiles": profiles, "categories": categories, "firewall_rules": firewall_rules}


# =====================================================================
# Intent Handler: Her intent için aksiyon calistir
# =====================================================================

CONFIDENCE_THRESHOLD = 0.15  # Bu esik altindaki intent'ler reddedilir


async def execute_commands(commands: list[ParsedCommand], db: AsyncSession) -> ChatResponse:
    """Ayristirilmis komutlari calistir ve sonuçlari birlestir."""

    if not commands:
        return _unknown_response()

    # Tek komut durumu
    if len(commands) == 1:
        cmd = commands[0]
        if cmd.intent == "unknown" or cmd.confidence < CONFIDENCE_THRESHOLD:
            return _unknown_response()
        return await _execute_single(cmd, db)

    # Coklu komut (örneğin: facebook, netflix ve youtube engelle)
    results = []
    action_results = []
    overall_type = commands[0].intent

    for cmd in commands:
        resp = await _execute_single(cmd, db)
        results.append(resp.reply)
        if resp.action_result:
            action_results.append(resp.action_result)

    combined_reply = "\n".join(f"- {r}" for r in results)
    return ChatResponse(
        reply=f"**{len(commands)} işlem yapildi:**\n\n{combined_reply}",
        action_type=overall_type,
        action_result={"batch": True, "count": len(commands), "results": action_results},
    )


async def _execute_single(cmd: ParsedCommand, db: AsyncSession) -> ChatResponse:
    """Tek bir komutu calistir."""
    intent = cmd.intent
    entities = cmd.entities

    handlers = {
        "block_domain": _handle_block_domain,
        "unblock_domain": _handle_unblock_domain,
        "block_device_domain": _handle_block_device_domain,
        "unblock_device_domain": _handle_unblock_device_domain,
        "block_device": _handle_block_device,
        "unblock_device": _handle_unblock_device,
        "assign_profile": _handle_assign_profile,
        "list_devices": _handle_list_devices,
        "list_profiles": _handle_list_profiles,
        "system_status": _handle_system_status,
        "dns_stats": _handle_dns_stats,
        "open_port": _handle_open_port,
        "close_port": _handle_close_port,
        "list_rules": _handle_list_rules,
        "add_rule": _handle_add_rule,
        "delete_rule": _handle_delete_rule,
        "toggle_rule": _handle_toggle_rule,
        "block_category": _handle_block_category,
        "unblock_category": _handle_unblock_category,
        "vpn_status": _handle_vpn_status,
        "vpn_connect": _handle_vpn_connect,
        "vpn_disconnect": _handle_vpn_disconnect,
        "bandwidth_limit": _handle_bandwidth_limit,
        "dhcp_info": _handle_dhcp_info,
        "firewall_info": _handle_firewall_info,
        "threat_status": _handle_threat_status,
        "block_ip": _handle_block_ip,
        "unblock_ip": _handle_unblock_ip,
        "rename_device": _handle_rename_device,
        "find_device": _handle_find_device,
        "pin_ip": _handle_pin_ip,
        "query_logs": _handle_query_logs,
        "help": _handle_help,
        "greeting": _handle_greeting,
    }

    handler = handlers.get(intent)
    if handler:
        # query_logs handler'i orijinal metne ihtiyac duyar
        if intent == "query_logs":
            return await handler(entities, db, cmd.original_text)
        return await handler(entities, db)

    return _unknown_response()


# =====================================================================
# Aksiyon Fonksiyonlari
# =====================================================================

async def _handle_block_domain(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Domain veya servis engelle (DB + Redis sync)."""
    # Servis veya domain bul — servisler için TUM domainleri engelle
    domains_to_block = []
    for ent in entities:
        if ent.type == "service":
            service_domains = ent.metadata.get("domains", [])
            for sd in service_domains:
                domains_to_block.append((sd, ent.value))
        elif ent.type == "domain":
            domains_to_block.append((ent.value, ent.value))

    if not domains_to_block:
        return ChatResponse(reply="Hangi siteyi/servisi engellememi istiyorsun? Örneğin: `facebook engelle` veya `example.com engelle`")

    results = []
    blocked_domains = []
    display_name_first = domains_to_block[0][1] if domains_to_block else ""
    for domain, display_name in domains_to_block:
        existing = await db.execute(select(DnsRule).where(DnsRule.domain == domain))
        if existing.scalar_one_or_none():
            continue
        rule = DnsRule(
            domain=domain,
            rule_type=DnsRuleType.BLOCK,
            reason=f"AI asistan: {display_name} engellendi",
            added_by="ai_chat",
        )
        db.add(rule)
        blocked_domains.append(domain)

    await db.flush()

    # Redis sync — DNS proxy'nin hemen engellemesi için
    if blocked_domains:
        try:
            redis_client = await get_redis()
            await redis_client.sadd("dns:blocked_domains", *blocked_domains)
        except Exception as e:
            logger.error(f"Redis DNS block sync hatasi: {e}")

    # Kullanıcıya özet mesaj
    if blocked_domains:
        reply = fmt.format_action_result(
            action="engellendi",
            target=display_name_first,
            success=True,
            details=blocked_domains if len(blocked_domains) > 1 else None,
            detail_label="Engellenen domainler",
        )
    else:
        reply = fmt.result_badge(False, f"`{display_name_first}` zaten engelli")

    return ChatResponse(
        reply=reply,
        action_type="dns_block",
        action_result={"domains": blocked_domains},
    )


async def _handle_unblock_domain(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Domain veya servis engelini kaldir (DB + Redis sync)."""
    domains_to_unblock = []
    for ent in entities:
        if ent.type == "service":
            service_domains = ent.metadata.get("domains", [])
            for sd in service_domains:
                domains_to_unblock.append((sd, ent.value))
        elif ent.type == "domain":
            domains_to_unblock.append((ent.value, ent.value))

    if not domains_to_unblock:
        return ChatResponse(reply="Hangi sitenin engelini kaldirmami istiyorsun?")

    results = []
    unblocked_domains = []
    display_name_first = domains_to_unblock[0][1] if domains_to_unblock else ""
    for domain, display_name in domains_to_unblock:
        existing = await db.execute(select(DnsRule).where(DnsRule.domain == domain))
        rule = existing.scalar_one_or_none()
        if not rule:
            continue
        await db.delete(rule)
        unblocked_domains.append(domain)

    await db.flush()

    # Redis sync — DNS proxy'nin hemen engeli kaldirmasi için
    if unblocked_domains:
        try:
            redis_client = await get_redis()
            await redis_client.srem("dns:blocked_domains", *unblocked_domains)
        except Exception as e:
            logger.error(f"Redis DNS unblock sync hatasi: {e}")

    # Kullanıcıya özet mesaj
    if unblocked_domains:
        reply = fmt.format_action_result(
            action="engeli kaldırıldı",
            target=display_name_first,
            success=True,
            details=unblocked_domains if len(unblocked_domains) > 1 else None,
            detail_label="Engeli kaldirilan domainler",
        )
    else:
        reply = fmt.result_badge(False, f"`{display_name_first}` zaten engelli degil")

    return ChatResponse(
        reply=reply,
        action_type="dns_unblock",
        action_result={"domains": unblocked_domains},
    )


async def _find_service_by_name(service_name: str, db: AsyncSession) -> BlockedService | None:
    """AI engine servis adini blocked_services tablosundaki kayitla esle."""
    name_lower = service_name.lower()
    # Direkt esleme
    result = await db.execute(
        select(BlockedService).where(BlockedService.service_id == name_lower)
    )
    svc = result.scalar_one_or_none()
    if svc:
        return svc
    # Fuzzy esleme: "whatsapp" -> "whatsapp-messenger" gibi
    result = await db.execute(
        select(BlockedService).where(
            BlockedService.service_id.like(f"{escape_like(name_lower)}%")
        )
    )
    return result.scalars().first()


async def _handle_block_device_domain(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Belirli bir cihaz için domain/servis engelle.

    Bilinen servisler (youtube, netflix, vb.) device_blocked_services tablosuna,
    bilinmeyen domain'ler device_custom_rules tablosuna yazilir.
    """
    device, suggestion = await _resolve_device_smart(entities, db)
    if not device:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(reply="Hangi cihaz için engelleme yapmami istiyorsun? Cihaz adini veya IP adresini yaz.")

    blocked_items = []
    display_name_first = ""
    service_blocked = False
    custom_rule_blocked = False

    for ent in entities:
        if not display_name_first:
            display_name_first = ent.value

        if ent.type == "service":
            # Bilinen servis mi? blocked_services tablosunda ara
            svc = await _find_service_by_name(ent.value, db)
            if svc:
                # device_blocked_services tablosuna yaz (toggle sistemi)
                existing = await db.scalar(
                    select(DeviceBlockedService).where(
                        DeviceBlockedService.device_id == device.id,
                        DeviceBlockedService.service_id == svc.id,
                    )
                )
                if existing:
                    if existing.blocked:
                        continue  # Zaten engelli
                    existing.blocked = True
                else:
                    dbs = DeviceBlockedService(
                        device_id=device.id,
                        service_id=svc.id,
                        blocked=True,
                    )
                    db.add(dbs)
                blocked_items.append(svc.name)
                service_blocked = True
            else:
                # Bilinmeyen servis: eski yontem (device_custom_rules)
                service_domains = ent.metadata.get("domains", [])
                for sd in service_domains:
                    existing = await db.scalar(
                        select(DeviceCustomRule).where(
                            DeviceCustomRule.device_id == device.id,
                            DeviceCustomRule.domain == sd,
                        )
                    )
                    if existing:
                        continue
                    rule = DeviceCustomRule(
                        device_id=device.id,
                        domain=sd,
                        rule_type=DeviceCustomRuleType.BLOCK,
                        reason=f"AI asistan: {ent.value} engellendi",
                        added_by="ai_chat",
                    )
                    db.add(rule)
                    blocked_items.append(sd)
                    custom_rule_blocked = True

        elif ent.type == "domain":
            existing = await db.scalar(
                select(DeviceCustomRule).where(
                    DeviceCustomRule.device_id == device.id,
                    DeviceCustomRule.domain == ent.value,
                )
            )
            if existing:
                continue
            rule = DeviceCustomRule(
                device_id=device.id,
                domain=ent.value,
                rule_type=DeviceCustomRuleType.BLOCK,
                reason=f"AI asistan: {ent.value} engellendi",
                added_by="ai_chat",
            )
            db.add(rule)
            blocked_items.append(ent.value)
            custom_rule_blocked = True

    if not blocked_items and not display_name_first:
        return ChatResponse(reply=f"**{device.hostname or device.ip_address}** için hangi siteyi/servisi engellememi istiyorsun?")

    await db.flush()

    # Redis sync
    try:
        redis_client = await get_redis()
        if service_blocked:
            await sync_device_services_to_redis(device.id, db, redis_client)
        if custom_rule_blocked:
            await sync_device_custom_rules_to_redis(device.id, db, redis_client)
    except Exception as e:
        logger.error(f"Redis device block sync hatasi: {e}")

    device_name = device.hostname or device.ip_address
    if blocked_items:
        reply = fmt.format_device_action(
            device_name=device_name,
            action="engellendi",
            target=display_name_first,
            success=True,
            details=blocked_items if len(blocked_items) > 1 else None,
        )
    else:
        reply = fmt.result_badge(False, f"**{device_name}** için `{display_name_first}` zaten engelli")
    return ChatResponse(
        reply=reply,
        action_type="device_dns_block",
        action_result={"device_id": device.id, "blocked": blocked_items},
    )


async def _handle_unblock_device_domain(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Belirli bir cihaz için domain/servis engelini kaldir.

    HER IKI tabloyu da kontrol eder:
    - device_blocked_services (servis bazli toggle)
    - device_custom_rules (domain bazli özel kurallar)
    """
    device, suggestion = await _resolve_device_smart(entities, db)
    if not device:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(reply="Hangi cihaz için engel kaldirmami istiyorsun? Cihaz adini veya IP adresini yaz.")

    unblocked_items = []
    display_name_first = ""
    service_changed = False
    custom_rule_changed = False

    for ent in entities:
        if not display_name_first:
            display_name_first = ent.value

        if ent.type == "service":
            # 1) device_blocked_services tablosunu kontrol et
            svc = await _find_service_by_name(ent.value, db)
            if svc:
                existing = await db.scalar(
                    select(DeviceBlockedService).where(
                        DeviceBlockedService.device_id == device.id,
                        DeviceBlockedService.service_id == svc.id,
                    )
                )
                if existing and existing.blocked:
                    existing.blocked = False
                    unblocked_items.append(svc.name)
                    service_changed = True

            # 2) device_custom_rules tablosunu da temizle (cift engel durumu)
            service_domains = ent.metadata.get("domains", [])
            for sd in service_domains:
                rule = await db.scalar(
                    select(DeviceCustomRule).where(
                        DeviceCustomRule.device_id == device.id,
                        DeviceCustomRule.domain == sd,
                    )
                )
                if rule:
                    await db.delete(rule)
                    if svc and svc.name not in unblocked_items:
                        unblocked_items.append(svc.name)
                    elif not svc:
                        unblocked_items.append(sd)
                    custom_rule_changed = True

        elif ent.type == "domain":
            # device_custom_rules tablosundan sil
            rule = await db.scalar(
                select(DeviceCustomRule).where(
                    DeviceCustomRule.device_id == device.id,
                    DeviceCustomRule.domain == ent.value,
                )
            )
            if rule:
                await db.delete(rule)
                unblocked_items.append(ent.value)
                custom_rule_changed = True

    if not unblocked_items and not display_name_first:
        return ChatResponse(reply=f"**{device.hostname or device.ip_address}** için hangi sitenin engelini kaldirmami istiyorsun?")

    await db.flush()

    # Redis sync
    try:
        redis_client = await get_redis()
        if service_changed:
            await sync_device_services_to_redis(device.id, db, redis_client)
        if custom_rule_changed:
            await sync_device_custom_rules_to_redis(device.id, db, redis_client)
    except Exception as e:
        logger.error(f"Redis device unblock sync hatasi: {e}")

    device_name = device.hostname or device.ip_address
    if unblocked_items:
        reply = fmt.format_device_action(
            device_name=device_name,
            action="engeli kaldırıldı",
            target=display_name_first,
            success=True,
            details=unblocked_items if len(unblocked_items) > 1 else None,
        )
    else:
        reply = fmt.result_badge(False, f"**{device_name}** için `{display_name_first}` zaten engelli degil")
    return ChatResponse(
        reply=reply,
        action_type="device_dns_unblock",
        action_result={"device_id": device.id, "unblocked": unblocked_items},
    )


async def _handle_block_device(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihaz engelle."""
    device, suggestion = await _resolve_device_smart(entities, db)
    if not device:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(reply="Hangi cihazi engellememi istiyorsun? Cihaz adini veya IP adresini yaz.")

    device.is_blocked = True
    await db.flush()
    name = device.hostname or device.ip_address
    return ChatResponse(
        reply=fmt.result_badge(True, f"**{name}** (`{device.ip_address}`) internetten engellendi"),
        action_type="device_block",
        action_result={"device_id": device.id, "ip": device.ip_address, "blocked": True},
    )


async def _handle_unblock_device(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihaz engelini kaldir."""
    device, suggestion = await _resolve_device_smart(entities, db)
    if not device:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(reply="Hangi cihazin engelini kaldirmami istiyorsun?")

    device.is_blocked = False
    await db.flush()
    name = device.hostname or device.ip_address
    return ChatResponse(
        reply=fmt.result_badge(True, f"**{name}** (`{device.ip_address}`) engeli kaldırıldı, internete erisebilir"),
        action_type="device_unblock",
        action_result={"device_id": device.id, "ip": device.ip_address, "blocked": False},
    )


async def _handle_assign_profile(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihaza profil ata."""
    device, suggestion = await _resolve_device_smart(entities, db)
    profile_ent = next((e for e in entities if e.type == "profile"), None)

    if not device:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(reply="Hangi cihaza profil atamamı istiyorsun? Cihaz adini veya IP adresini yaz.")
    if not profile_ent:
        # Profilleri listele
        profiles_result = await db.execute(select(Profile))
        profiles = profiles_result.scalars().all()
        names = ", ".join(f"`{p.name}`" for p in profiles)
        return ChatResponse(reply=f"Hangi profili atamamı istiyorsun? Mevcut profiller: {names}")

    profile_id = int(profile_ent.value) if profile_ent.value.isdigit() else None
    profile = None
    if profile_id:
        result = await db.execute(select(Profile).where(Profile.id == profile_id))
        profile = result.scalar_one_or_none()

    if not profile:
        return ChatResponse(reply=f"`{profile_ent.original}` profili bulunamadı.")

    device.profile_id = profile.id
    await db.flush()
    name = device.hostname or device.ip_address
    return ChatResponse(
        reply=fmt.result_badge(True, f"**{name}** profili **{profile.name}** olarak ayarlandi"),
        action_type="device_update",
        action_result={"device_id": device.id, "profile_id": profile.id, "profile_name": profile.name},
    )


async def _handle_list_devices(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Bagli cihazlari listele."""
    result = await db.execute(select(Device).order_by(Device.ip_address))
    devices = result.scalars().all()
    if not devices:
        return ChatResponse(reply="Agda kayıtlı cihaz bulunamadı.")

    # Alias bilgilerini yukle
    aliases = load_aliases()
    # Ters alias map: device_id -> alias adi
    alias_by_device_id = {}
    alias_by_ip = {}
    for aname, ainfo in aliases.items():
        did = ainfo.get("device_id")
        aip = ainfo.get("ip")
        if did:
            alias_by_device_id[did] = aname
        if aip:
            alias_by_ip[aip] = aname

    # Profilleri toplu olarak al
    profile_map = {}
    profiles_result = await db.execute(select(Profile))
    for p in profiles_result.scalars().all():
        profile_map[p.id] = p.name

    device_dicts = []
    for d in devices:
        alias_name = alias_by_device_id.get(d.id) or alias_by_ip.get(d.ip_address)
        device_dicts.append({
            "hostname": d.hostname or "Bilinmeyen",
            "ip": d.ip_address,
            "manufacturer": d.manufacturer,
            "is_online": d.is_online,
            "profile_name": profile_map.get(d.profile_id) if d.profile_id else None,
            "alias_name": alias_name,
            "is_blocked": d.is_blocked,
        })

    online = sum(1 for d in devices if d.is_online)
    return ChatResponse(
        reply=fmt.format_device_list(device_dicts),
        action_type="list_devices",
        action_result={"total": len(devices), "online": online},
    )


async def _handle_list_profiles(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Profilleri listele."""
    result = await db.execute(select(Profile))
    profiles = result.scalars().all()
    if not profiles:
        return ChatResponse(reply="Tanimli profil bulunamadı.")

    profile_dicts = [
        {"name": p.name, "profile_type": p.profile_type, "bandwidth_limit": p.bandwidth_limit}
        for p in profiles
    ]
    return ChatResponse(
        reply=fmt.format_profile_list(profile_dicts),
        action_type="list_profiles",
        action_result={"total": len(profiles)},
    )


async def _handle_system_status(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Sistem durumu özeti."""
    device_count = await db.scalar(select(func.count(Device.id))) or 0
    online_count = await db.scalar(select(func.count(Device.id)).where(Device.is_online == True)) or 0  # noqa
    blocked_count = await db.scalar(select(func.count(Device.id)).where(Device.is_blocked == True)) or 0  # noqa
    rule_count = await db.scalar(select(func.count(DnsRule.id))) or 0
    fw_count = await db.scalar(select(func.count(FirewallRule.id))) or 0
    blocklist_count = await db.scalar(select(func.count(Blocklist.id))) or 0
    critical_count = await db.scalar(select(func.count(AiInsight.id)).where(AiInsight.severity == "critical")) or 0
    vpn_active = await db.scalar(select(func.count(VpnClientServer.id)).where(VpnClientServer.is_active == True)) or 0  # noqa

    stats = {
        "devices": device_count, "online": online_count, "blocked": blocked_count,
        "dns_rules": rule_count, "dns_blocks": 0, "dns_allows": 0,
        "blocklist_count": blocklist_count, "fw_rules": fw_count,
        "vpn_active": vpn_active > 0, "critical_count": critical_count,
    }
    return ChatResponse(
        reply=fmt.format_system_status(stats),
        action_type="status",
        action_result={
            "devices": device_count, "online": online_count,
            "dns_rules": rule_count, "fw_rules": fw_count,
            "vpn_active": vpn_active > 0,
        },
    )


async def _handle_dns_stats(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """DNS istatistikleri."""
    rule_count = await db.scalar(select(func.count(DnsRule.id))) or 0
    block_count = await db.scalar(select(func.count(DnsRule.id)).where(DnsRule.rule_type == DnsRuleType.BLOCK)) or 0
    allow_count = await db.scalar(select(func.count(DnsRule.id)).where(DnsRule.rule_type == DnsRuleType.ALLOW)) or 0
    blocklist_count = await db.scalar(select(func.count(Blocklist.id))) or 0

    # Son engellenen domainleri goster
    recent = await db.execute(
        select(DnsRule).where(DnsRule.rule_type == DnsRuleType.BLOCK).order_by(desc(DnsRule.id)).limit(5)
    )
    recent_domains = [r.domain for r in recent.scalars().all()]

    stats = {"rules": rule_count, "blocks": block_count, "allows": allow_count, "blocklist_count": blocklist_count}
    return ChatResponse(
        reply=fmt.format_dns_stats(stats, recent_domains),
        action_type="dns_stats",
        action_result={"rules": rule_count, "blocks": block_count, "allows": allow_count},
    )


MAX_FIREWALL_RULES = 1000  # Maksimum firewall kural sayısı


async def _check_firewall_rule_limit(db: AsyncSession) -> str | None:
    """Firewall kural limiti kontrolü. Limit asildiysa hata mesaji dondurur."""
    count = await db.scalar(select(func.count(FirewallRule.id))) or 0
    if count >= MAX_FIREWALL_RULES:
        return f"Maksimum firewall kural sayısına ulasildi ({MAX_FIREWALL_RULES}). Yeni kural eklemek için once mevcut kurallari silin."
    return None


async def _handle_open_port(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Port ac."""
    limit_msg = await _check_firewall_rule_limit(db)
    if limit_msg:
        return ChatResponse(reply=fmt.result_badge(False, limit_msg))

    port_ent = next((e for e in entities if e.type == "port"), None)
    proto_ent = next((e for e in entities if e.type == "protocol"), None)
    if not port_ent:
        return ChatResponse(reply="Hangi portu acmami istiyorsun? Örneğin: `port 8080 ac`")

    port = int(port_ent.value)
    protocol = proto_ent.value if proto_ent else "tcp"

    rule = FirewallRule(
        name=f"AI - Port {port} Açık",
        description="AI asistan tarafindan acildi",
        direction="inbound",
        protocol=protocol,
        port=port,
        action="accept",
        enabled=True,
        priority=50,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    # nftables'a sync (kritik: DB'ye yazmak yetmez, kuralı uygulamak lazim)
    from app.hal.driver_factory import _driver_instance
    if _driver_instance:
        await _driver_instance.add_port_rule({
            "id": rule.id, "port": port, "protocol": protocol,
            "action": "accept", "direction": "inbound",
            "name": rule.name, "log_packets": False,
        })

    return ChatResponse(
        reply=fmt.result_badge(True, f"Port **{port}/{protocol.upper()}** inbound trafik için acildi"),
        action_type="port_open",
        action_result={"port": port, "protocol": protocol, "rule_id": rule.id},
    )


async def _handle_close_port(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Port kapat."""
    limit_msg = await _check_firewall_rule_limit(db)
    if limit_msg:
        return ChatResponse(reply=fmt.result_badge(False, limit_msg))

    port_ent = next((e for e in entities if e.type == "port"), None)
    proto_ent = next((e for e in entities if e.type == "protocol"), None)
    if not port_ent:
        return ChatResponse(reply="Hangi portu kapatmami istiyorsun? Örneğin: `port 23 kapat`")

    port = int(port_ent.value)
    protocol = proto_ent.value if proto_ent else "tcp"

    rule = FirewallRule(
        name=f"AI - Port {port} Engelli",
        description="AI asistan tarafindan engellendi",
        direction="inbound",
        protocol=protocol,
        port=port,
        action="drop",
        enabled=True,
        priority=50,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    # nftables'a sync (kritik: DB'ye yazmak yetmez, kuralı uygulamak lazim)
    from app.hal.driver_factory import _driver_instance
    if _driver_instance:
        await _driver_instance.add_port_rule({
            "id": rule.id, "port": port, "protocol": protocol,
            "action": "drop", "direction": "inbound",
            "name": rule.name, "log_packets": False,
        })

    return ChatResponse(
        reply=fmt.result_badge(True, f"Port **{port}/{protocol.upper()}** inbound trafik için engellendi"),
        action_type="port_close",
        action_result={"port": port, "protocol": protocol, "rule_id": rule.id},
    )


async def _handle_list_rules(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Firewall kurallarini listele."""
    direction_ent = next((e for e in entities if e.type == "direction"), None)
    query = select(FirewallRule).order_by(FirewallRule.priority, FirewallRule.id)
    if direction_ent:
        query = query.where(FirewallRule.direction == direction_ent.value)
    result = await db.execute(query)
    rules = result.scalars().all()
    return ChatResponse(
        reply=fmt.format_firewall_rules(rules),
        action_type="list_rules",
        action_result={"count": len(rules)},
    )


async def _handle_add_rule(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Gelismis firewall kuralı ekle."""
    limit_msg = await _check_firewall_rule_limit(db)
    if limit_msg:
        return ChatResponse(reply=fmt.result_badge(False, limit_msg))

    port_ent = next((e for e in entities if e.type == "port"), None)
    proto_ent = next((e for e in entities if e.type == "protocol"), None)
    action_ent = next((e for e in entities if e.type == "fw_action"), None)
    direction_ent = next((e for e in entities if e.type == "direction"), None)
    name_ent = next((e for e in entities if e.type == "rule_name"), None)

    if not port_ent:
        return ChatResponse(
            reply="Kural için en az port numarasi gerekli. Ornek: `port 443 tcp accept kuralı ekle`"
        )

    port = int(port_ent.value)
    protocol = proto_ent.value if proto_ent else "tcp"
    action = action_ent.value if action_ent else "accept"
    direction = direction_ent.value if direction_ent else "inbound"
    name = name_ent.value if name_ent else f"AI - Port {port}"

    rule = FirewallRule(
        name=name,
        description="AI asistan tarafindan eklendi",
        direction=direction,
        protocol=protocol,
        port=port,
        action=action,
        enabled=True,
        priority=50,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    from app.hal.driver_factory import _driver_instance
    if _driver_instance:
        await _driver_instance.add_port_rule({
            "id": rule.id, "port": port, "protocol": protocol,
            "action": action, "direction": direction,
            "name": name, "log_packets": False,
        })

    return ChatResponse(
        reply=fmt.result_badge(
            True,
            f"Kural eklendi: **{name}** (Port {port}/{protocol} {direction} {action})"
        ),
        action_type="add_rule",
        action_result={"rule_id": rule.id, "port": port},
    )


async def _handle_delete_rule(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Firewall kuralı sil."""
    rule_id_ent = next((e for e in entities if e.type == "rule_id"), None)
    port_ent = next((e for e in entities if e.type == "port"), None)

    rule = None
    if rule_id_ent:
        rule = await db.get(FirewallRule, int(rule_id_ent.value))
    elif port_ent:
        result = await db.execute(
            select(FirewallRule).where(FirewallRule.port == int(port_ent.value))
        )
        rule = result.scalars().first()
    else:
        return ChatResponse(
            reply="Hangi kuralı silmemi istiyorsun? Kural ID veya port numarasi belirt. "
                  "Ornek: `kural #5 sil` veya `port 8080 kuralıni sil`"
        )

    if not rule:
        return ChatResponse(reply=fmt.result_badge(False, "Kural bulunamadı"))

    from app.hal.driver_factory import _driver_instance
    if _driver_instance:
        await _driver_instance.remove_port_rule(str(rule.id))

    rule_desc = f"#{rule.id} ({rule.name})"
    await db.delete(rule)
    return ChatResponse(
        reply=fmt.result_badge(True, f"Firewall kuralı **{rule_desc}** silindi"),
        action_type="delete_rule",
        action_result={"rule_id": rule.id},
    )


async def _handle_toggle_rule(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Firewall kuralıni ac/kapat."""
    rule_id_ent = next((e for e in entities if e.type == "rule_id"), None)
    port_ent = next((e for e in entities if e.type == "port"), None)

    rule = None
    if rule_id_ent:
        rule = await db.get(FirewallRule, int(rule_id_ent.value))
    elif port_ent:
        result = await db.execute(
            select(FirewallRule).where(FirewallRule.port == int(port_ent.value))
        )
        rule = result.scalars().first()
    else:
        return ChatResponse(reply="Hangi kuralı değiştirmemi istiyorsun?")

    if not rule:
        return ChatResponse(reply=fmt.result_badge(False, "Kural bulunamadı"))

    rule.enabled = not rule.enabled

    from app.hal.driver_factory import _driver_instance
    if _driver_instance:
        if rule.enabled:
            proto = rule.protocol.value if hasattr(rule.protocol, "value") else rule.protocol
            action = rule.action.value if hasattr(rule.action, "value") else rule.action
            direction = rule.direction.value if hasattr(rule.direction, "value") else rule.direction
            await _driver_instance.add_port_rule({
                "id": rule.id, "port": rule.port, "protocol": proto,
                "action": action, "direction": direction,
                "name": rule.name, "log_packets": rule.log_packets,
            })
        else:
            await _driver_instance.remove_port_rule(str(rule.id))

    state = "etkinlestirildi" if rule.enabled else "devre disi birakildi"
    return ChatResponse(
        reply=fmt.result_badge(True, f"Kural **#{rule.id}** ({rule.name}) {state}"),
        action_type="toggle_rule",
        action_result={"rule_id": rule.id, "enabled": rule.enabled},
    )


async def _handle_block_category(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """İçerik kategorisi engelle."""
    cat_ents = [e for e in entities if e.type == "category"]
    if not cat_ents:
        cats = (await db.execute(select(ContentCategory))).scalars().all()
        names = ", ".join(f"`{c.name}`" for c in cats)
        return ChatResponse(reply=f"Hangi kategoriyi engellememi istiyorsun? Mevcut kategoriler: {names}")

    results = []
    for ent in cat_ents:
        cat_id = ent.metadata.get("category_id")
        if cat_id:
            await db.execute(update(ContentCategory).where(ContentCategory.id == cat_id).values(enabled=False))
            results.append(ent.original)

    await db.flush()
    if results:
        reply = fmt.format_action_result(
            action="kategorisi engellendi",
            target=", ".join(results),
            success=True,
        )
    else:
        reply = fmt.result_badge(False, "İşlem yapilamadi")
    return ChatResponse(reply=reply, action_type="category_block", action_result={"categories": [e.value for e in cat_ents]})


async def _handle_unblock_category(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """İçerik kategorisi engelini kaldir."""
    cat_ents = [e for e in entities if e.type == "category"]
    if not cat_ents:
        return ChatResponse(reply="Hangi kategorinin engelini kaldirmami istiyorsun?")

    results = []
    for ent in cat_ents:
        cat_id = ent.metadata.get("category_id")
        if cat_id:
            await db.execute(update(ContentCategory).where(ContentCategory.id == cat_id).values(enabled=True))
            results.append(ent.original)

    await db.flush()
    if results:
        reply = fmt.format_action_result(
            action="kategorisi serbest birakildi",
            target=", ".join(results),
            success=True,
        )
    else:
        reply = fmt.result_badge(False, "İşlem yapilamadi")
    return ChatResponse(reply=reply, action_type="category_unblock", action_result={"categories": [e.value for e in cat_ents]})


async def _handle_vpn_status(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """VPN durumu goster."""
    # Dış VPN
    active = await db.execute(select(VpnClientServer).where(VpnClientServer.is_active == True))  # noqa
    active_server = active.scalar_one_or_none()
    total = await db.scalar(select(func.count(VpnClientServer.id))) or 0

    # Sunucu VPN
    vpn_cfg = (await db.execute(select(VpnConfig))).scalar_one_or_none()

    return ChatResponse(
        reply=fmt.format_vpn_status(
            external_active=active_server is not None,
            external_name=active_server.name if active_server else None,
            external_country=active_server.country if active_server else None,
            total_servers=total,
            local_active=vpn_cfg.enabled if vpn_cfg else False,
        ),
        action_type="vpn_status",
        action_result={"external_active": active_server is not None, "total_servers": total},
    )


async def _handle_vpn_connect(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """VPN sunucusuna baglan."""
    country_ent = next((e for e in entities if e.type == "country"), None)

    if country_ent:
        result = await db.execute(
            select(VpnClientServer).where(VpnClientServer.country_code == country_ent.value)
        )
        server = result.scalar_one_or_none()
        if server:
            # Onceki aktif sunucuyu kapat
            await db.execute(
                update(VpnClientServer).where(VpnClientServer.is_active == True).values(is_active=False)  # noqa
            )
            server.is_active = True
            await db.flush()
            return ChatResponse(
                reply=fmt.result_badge(True, f"**{server.name}** ({server.country}) VPN sunucusuna baglanildi"),
                action_type="vpn_connect",
                action_result={"server_id": server.id, "country": server.country},
            )
        return ChatResponse(reply=f"{country_ent.original} için VPN sunucusu bulunamadı.")

    # Ülke belirtilmemis, mevcut sunuculari goster
    servers = (await db.execute(select(VpnClientServer))).scalars().all()
    if not servers:
        return ChatResponse(reply="Tanimli VPN sunucusu yok. Once Dış VPN İstemci sayfasından bir sunucu ekle.")

    names = ", ".join(f"`{s.name}` ({s.country})" for s in servers)
    return ChatResponse(reply=f"Hangi VPN sunucusuna baglanmami istiyorsun? Mevcut sunucular: {names}")


async def _handle_vpn_disconnect(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """VPN bağlantısini kes."""
    await db.execute(
        update(VpnClientServer).where(VpnClientServer.is_active == True).values(is_active=False)  # noqa
    )
    await db.flush()
    return ChatResponse(
        reply=fmt.result_badge(True, "VPN bağlantısi kesildi"),
        action_type="vpn_disconnect",
        action_result={"disconnected": True},
    )


async def _handle_bandwidth_limit(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Bant genişliği sinirla (bilgilendirme)."""
    device, _ = await _resolve_device_smart(entities, db)
    if device:
        return ChatResponse(
            reply=f"**{device.hostname or device.ip_address}** için bant genisligi siniri ayarlamak için "
                  f"cihazin profilini düzenle. Profiller sayfasından `bandwidth_limit` degerini değiştirebilirsin.",
            action_type="info",
        )
    return ChatResponse(
        reply="Bant genişliği sinirlamasi profiller üzerinden yapilir. "
              "Profiller sayfasından ilgili profilin `Bant Genisligi Limiti` degerini ayarlayabilirsin.",
        action_type="info",
    )


async def _handle_dhcp_info(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """DHCP bilgileri."""
    pool_count = await db.scalar(select(func.count(DhcpPool.id))) or 0
    lease_count = await db.scalar(select(func.count(DhcpLease.id))) or 0
    static_count = await db.scalar(select(func.count(DhcpLease.id)).where(DhcpLease.is_static == True)) or 0  # noqa

    return ChatResponse(
        reply=fmt.format_dhcp_info(pool_count, lease_count, static_count),
        action_type="dhcp_info",
        action_result={"pools": pool_count, "leases": lease_count, "static": static_count},
    )


async def _handle_firewall_info(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Firewall bilgileri (detayli)."""
    total = await db.scalar(select(func.count(FirewallRule.id))) or 0
    enabled = await db.scalar(select(func.count(FirewallRule.id)).where(FirewallRule.enabled == True)) or 0  # noqa

    # Ilk 10 kuralı da goster
    result = await db.execute(
        select(FirewallRule).order_by(FirewallRule.priority, FirewallRule.id).limit(10)
    )
    rules = result.scalars().all()

    return ChatResponse(
        reply=fmt.format_firewall_info_detailed(total, enabled, rules),
        action_type="firewall_info",
        action_result={"total": total, "enabled": enabled},
    )


async def _handle_rename_device(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihaza alias (takma ad) ata."""
    # Cihaz bul (IP veya device entity ile)
    device, _ = await _resolve_device_smart(entities, db)

    # Alias bilgisini metinden cikar: iliski + cihaz tipi
    rel_ent = next((e for e in entities if e.type == "relationship"), None)
    rel_key = rel_ent.value if rel_ent else None
    dev_type = rel_ent.metadata.get("device_type") if rel_ent else None

    # Alias adi oluştur
    alias_name = None
    if rel_key and dev_type:
        # "babamin telefonu", "oglumun tableti" gibi
        alias_name = f"{rel_key} {dev_type}"
    elif rel_key:
        alias_name = rel_key

    if device and alias_name:
        # Cihaz bulundu VE alias adi var -> kaydet
        add_alias(alias_name, device.id, device.ip_address)
        name = device.hostname or device.ip_address
        return ChatResponse(
            reply=fmt.result_badge(True, f"**{name}** (`{device.ip_address}`) için alias kaydedildi: **{alias_name}**") + "\n\n"
                  + fmt.info_box(f"`{alias_name} engelle` gibi komutlar kullanabilirsin"),
            action_type="device_rename",
            action_result={"device_id": device.id, "ip": device.ip_address, "alias": alias_name},
        )
    elif device and not alias_name:
        # Cihaz var ama alias yok
        name = device.hostname or device.ip_address
        return ChatResponse(
            reply=f"**{name}** (`{device.ip_address}`) cihazina ne isim vermemi istersin?\n\n"
                  f"Örneğin: `bu babamin telefonu` veya `bu cihaza salon tv de`",
        )
    elif not device and alias_name:
        # Alias var ama cihaz yok -> cihaz listesi goster
        all_devices = (await db.execute(select(Device).order_by(Device.ip_address))).scalars().all()
        if all_devices:
            lines = []
            for d in all_devices[:10]:
                lines.append(f"- **{d.hostname or 'Bilinmeyen'}** (`{d.ip_address}`)")
            device_list = "\n".join(lines)
            extra = f"\n... ve {len(all_devices) - 10} cihaz daha" if len(all_devices) > 10 else ""
            return ChatResponse(
                reply=f"**{alias_name}** ismini hangi cihaza atamak istersin? IP veya cihaz adini belirt.\n\n"
                      f"Mevcut cihazlar:\n{device_list}{extra}",
            )
        return ChatResponse(reply="Agda kayıtlı cihaz bulunamadı. Once cihazlarin kesfedilmesini bekle.")
    else:
        # Ne cihaz ne alias bilgisi var
        return ChatResponse(
            reply="Bir cihaza takma ad vermek için cihazi ve ismi belirtmen gerekiyor.\n\n"
                  "Ornekler:\n"
                  "- `192.168.1.8 babamin telefonu olsun`\n"
                  "- `su cihaza salon tv de` (once IP yaz)\n"
                  "- `cihaza isim ver` dedikten sonra detayları belirt",
        )


async def _handle_find_device(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihaz ara: alias, hostname, IP ile cihaz bul."""
    results = []

    # 1. Alias'larda ara
    aliases = load_aliases()
    rel_ent = next((e for e in entities if e.type == "relationship"), None)
    rel_key = rel_ent.value if rel_ent else None
    dev_type = rel_ent.metadata.get("device_type") if rel_ent else None

    # Alias ile ara (genel metin)
    # Ham metni entity'lerden cikarmaya calis
    original_text = ""
    for ent in entities:
        if hasattr(ent, "original"):
            original_text += " " + ent.original
    original_text = original_text.strip()

    # Iliski + tip kombinasyonu ile alias ara
    search_terms = []
    if rel_key and dev_type:
        search_terms.append(f"{rel_key} {dev_type}")
    if rel_key:
        search_terms.append(rel_key)

    alias_found = None
    for term in search_terms:
        term_norm = normalize_turkish(term)
        for akey, ainfo in aliases.items():
            if term_norm in akey or akey in term_norm:
                alias_found = (akey, ainfo)
                break
            score = levenshtein_ratio(term_norm, akey)
            if score > 0.65:
                alias_found = (akey, ainfo)
                break
        if alias_found:
            break

    if alias_found:
        akey, ainfo = alias_found
        dev_id = ainfo.get("device_id")
        ip = ainfo.get("ip", "")
        # DB'den cihaz bilgisi al
        device = None
        if dev_id:
            result = await db.execute(select(Device).where(Device.id == dev_id))
            device = result.scalar_one_or_none()
        if not device and ip:
            result = await db.execute(select(Device).where(Device.ip_address == ip))
            device = result.scalar_one_or_none()

        if device:
            status = "çevrimiçi" if device.is_online else "çevrimdışı"
            blocked = " (ENGELLI)" if device.is_blocked else ""
            results.append(
                f"**{akey}** --> **{device.hostname or 'Bilinmeyen'}** (`{device.ip_address}`)\n"
                f"   Durum: {status}{blocked} | Uretici: {device.manufacturer or '?'}"
            )
        else:
            results.append(f"**{akey}** --> IP: `{ip}` (cihaz DB'de bulunamadı)")

    # 2. IP ile ara
    ip_ent = next((e for e in entities if e.type == "ip"), None)
    if ip_ent:
        result = await db.execute(select(Device).where(Device.ip_address == ip_ent.value))
        device = result.scalar_one_or_none()
        if device:
            status = "çevrimiçi" if device.is_online else "çevrimdışı"
            blocked = " (ENGELLI)" if device.is_blocked else ""
            # Bu IP için alias var mi?
            ip_alias = None
            for akey, ainfo in aliases.items():
                if ainfo.get("ip") == ip_ent.value or ainfo.get("device_id") == device.id:
                    ip_alias = akey
                    break
            alias_info = f" | Alias: _{ip_alias}_" if ip_alias else ""
            results.append(
                f"`{ip_ent.value}` --> **{device.hostname or 'Bilinmeyen'}**\n"
                f"   Durum: {status}{blocked} | Uretici: {device.manufacturer or '?'}{alias_info}"
            )
        else:
            results.append(f"`{ip_ent.value}` adresinde kayıtlı cihaz bulunamadı.")

    # 3. Device entity ile ara
    device_ent = next((e for e in entities if e.type == "device"), None)
    if device_ent and device_ent.metadata.get("device_id"):
        dev_id = device_ent.metadata["device_id"]
        result = await db.execute(select(Device).where(Device.id == dev_id))
        device = result.scalar_one_or_none()
        if device and not any(device.ip_address in r for r in results):
            status = "çevrimiçi" if device.is_online else "çevrimdışı"
            blocked = " (ENGELLI)" if device.is_blocked else ""
            results.append(
                f"**{device.hostname or 'Bilinmeyen'}** (`{device.ip_address}`)\n"
                f"   Durum: {status}{blocked} | Uretici: {device.manufacturer or '?'}"
            )

    if results:
        return ChatResponse(
            reply="**Bulunan cihaz(lar):**\n\n" + "\n\n".join(results),
            action_type="find_device",
            action_result={"found": len(results)},
        )

    # 4. Hicbir sey bulunamadı -> oneri
    if rel_key and dev_type:
        combo = f"{rel_key} {dev_type}"
        return ChatResponse(
            reply=f"**{combo}** için kayıtlı bir alias bulunamadı.\n\n"
                  f"Bu ismi bir cihaza atamak ister misin? Örneğin:\n"
                  f"- `192.168.1.X {combo} olsun` (IP adresini yaz)\n"
                  f"- `cihaza isim ver` komutuyla alias ekleyebilirsin",
            action_type="find_device",
            action_result={"found": 0},
        )

    return ChatResponse(
        reply="Aranacak cihaz bilgisi bulunamadı. Su sekilde arayabilirsin:\n\n"
              "- `babamin telefonu hangisi` (alias ile arama)\n"
              "- `192.168.1.8 kimin` (IP ile arama)\n"
              "- `cihaz bul` + cihaz adi",
        action_type="find_device",
        action_result={"found": 0},
    )


async def _handle_pin_ip(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Cihazin mevcut IP adresini sabitle (statik DHCP kiralama oluştur)."""
    from app.hal.driver_factory import _driver_instance

    device, suggestion = await _resolve_device_smart(entities, db)

    # IP entity'si varsa (kullanıcı farkli IP belirtmis olabilir)
    ip_ent = next((e for e in entities if e.type == "ip"), None)

    if not device and not ip_ent:
        if suggestion:
            return ChatResponse(reply=suggestion)
        return ChatResponse(
            reply="Hangi cihazin IP adresini sabitlememi istiyorsun?\n\n"
                  "Ornekler:\n"
                  "- `192.168.1.40 IP sabitle`\n"
                  "- `babamin telefonunun IP sini sabitle`\n"
                  "- `su cihaza 192.168.1.50 ata`",
        )

    # Cihaz varsa MAC ve IP bilgisini al
    if device:
        mac = device.mac_address
        ip = ip_ent.value if ip_ent else device.ip_address
        hostname = device.hostname or ""
    elif ip_ent:
        # IP var ama cihaz bulunamadı -> DB'den IP ile ara
        result = await db.execute(select(Device).where(Device.ip_address == ip_ent.value))
        device = result.scalar_one_or_none()
        if device:
            mac = device.mac_address
            ip = ip_ent.value
            hostname = device.hostname or ""
        else:
            return ChatResponse(reply=f"`{ip_ent.value}` adresinde kayıtlı cihaz bulunamadı. Once cihazin aga baglanmasi gerekiyor.")
    else:
        return ChatResponse(reply="Cihaz bilgisi alinamadi.")

    # Placeholder MAC kontrolü
    if mac.startswith("AA:00:") or mac.startswith("DD:0T:"):
        return ChatResponse(
            reply=f"**{hostname or ip}** cihazinin gercek MAC adresi henüz tespit edilemedi (placeholder: `{mac}`).\n\n"
                  "Cihaz DHCP ile IP aldiginda gercek MAC adresi otomatik güncellenecek. "
                  "Sonra tekrar `IP sabitle` diyebilirsin.",
        )

    # DhcpLease oluştur veya güncelle
    lease_result = await db.execute(
        select(DhcpLease).where(DhcpLease.mac_address == mac)
    )
    existing = lease_result.scalar_one_or_none()

    if existing:
        existing.ip_address = ip
        existing.hostname = hostname
        existing.is_static = True
        lease = existing
    else:
        lease = DhcpLease(
            mac_address=mac,
            ip_address=ip,
            hostname=hostname,
            is_static=True,
        )
        db.add(lease)

    # HAL driver ile dnsmasq config güncelle
    try:
        driver = _driver_instance
        if driver:
            await driver.add_static_lease(mac, ip, hostname)
    except Exception as e:
        return ChatResponse(
            reply=f"DB'ye kaydedildi ama dnsmasq config yazilirken hata oluştu: {e}",
            action_type="pin_ip",
        )

    await db.flush()

    name = hostname or mac
    return ChatResponse(
        reply=fmt.result_badge(True, f"**{name}** (`{mac}`) için IP adresi **{ip}** olarak sabitlendi") + "\n\n"
              + fmt.info_box(f"Bu cihaz artik her zaman `{ip}` adresini alacak"),
        action_type="pin_ip",
        action_result={"mac": mac, "ip": ip, "hostname": hostname},
    )


async def _handle_help(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Yardim mesaji."""
    return ChatResponse(reply=fmt.format_help())


async def _handle_greeting(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Selamlama."""
    online = await db.scalar(select(func.count(Device.id)).where(Device.is_online == True)) or 0  # noqa
    alias_count = len(load_aliases())
    return ChatResponse(reply=fmt.format_greeting(online, alias_count))


# =====================================================================
# Yardimci Fonksiyonlar
# =====================================================================

async def _resolve_device(entities: list[Entity], db: AsyncSession) -> Device | None:
    """Entity listesinden cihaz cozumle (IP veya isim ile). Eski uyumlu versiyon."""
    device, _ = await _resolve_device_smart(entities, db)
    return device


async def _resolve_device_smart(entities: list[Entity], db: AsyncSession) -> tuple[Device | None, str | None]:
    """
    Akilli cihaz cozumleme. Dondurur: (device, suggestion_text)
    1. IP entity ile ara
    2. Alias ile ara (device entity source=alias veya alias_combo)
    3. Fuzzy device name match ile ara
    4. Bulunamazsa oneri metni dondur
    """
    # 1. IP adresi ile cihaz bul
    ip_ent = next((e for e in entities if e.type == "ip"), None)
    if ip_ent:
        result = await db.execute(select(Device).where(Device.ip_address == ip_ent.value))
        device = result.scalar_one_or_none()
        if device:
            return device, None

    # 2. Alias ile eslesmis device entity (source=alias veya alias_combo)
    alias_device_ent = next(
        (e for e in entities if e.type == "device" and e.metadata.get("source") in ("alias", "alias_combo")),
        None,
    )
    if alias_device_ent:
        dev_id = alias_device_ent.metadata.get("device_id")
        if dev_id:
            result = await db.execute(select(Device).where(Device.id == dev_id))
            device = result.scalar_one_or_none()
            if device:
                return device, None
        # device_id ile bulunamadıysa IP ile dene
        if alias_device_ent.value:
            result = await db.execute(select(Device).where(Device.ip_address == alias_device_ent.value))
            device = result.scalar_one_or_none()
            if device:
                return device, None

    # 3. Fuzzy eslesmis cihaz (hostname match)
    device_ent = next(
        (e for e in entities if e.type == "device" and e.metadata.get("source") not in ("alias", "alias_combo")),
        None,
    )
    if device_ent and device_ent.metadata.get("device_id"):
        result = await db.execute(select(Device).where(Device.id == device_ent.metadata["device_id"]))
        device = result.scalar_one_or_none()
        if device:
            return device, None

    # 4. Bulunamadi -> iliski + cihaz tipi ile oneri oluştur
    rel_ent = next((e for e in entities if e.type == "relationship"), None)
    if rel_ent:
        rel_key = rel_ent.value
        dev_type = rel_ent.metadata.get("device_type", "")
        combo = f"{rel_key} {dev_type}" if dev_type else rel_key

        # En yakin cihazlari goster
        all_devices = (await db.execute(select(Device).order_by(Device.ip_address).limit(10))).scalars().all()
        if all_devices:
            lines = []
            for d in all_devices:
                name = d.hostname or "Bilinmeyen"
                lines.append(f"- {name} (`{d.ip_address}`)")
            device_list = "\n".join(lines)
            suggestion = (
                f"**{combo}** için kayıtlı cihaz bulunamadı. Sunlardan biri olabilir mi?\n\n"
                f"{device_list}\n\n"
                f"IP adresini yazarak işlem yapabilir veya `{combo} olsun` diyerek alias atayabilirsin."
            )
            return None, suggestion

    return None, None


# =====================================================================
# Tehdit Yönetimi Handler'lari
# =====================================================================

async def _handle_threat_status(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """Tehdit istatistiklerini goster."""
    from app.workers.threat_analyzer import get_threat_stats, get_blocked_ips

    stats = await get_threat_stats()
    blocked = await get_blocked_ips()

    return ChatResponse(
        reply=fmt.format_threat_status(stats, blocked),
        action_type="threat_status",
        action_result=stats,
    )


async def _handle_block_ip(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """IP adresini engelle."""
    from app.workers.threat_analyzer import manual_block_ip

    ip_ent = next((e for e in entities if e.type == "ip"), None)
    if not ip_ent:
        return ChatResponse(reply="Engellenecek IP adresi bulunamadı. Ornek: `1.2.3.4 IP engelle`")

    ip = ip_ent.value
    success = await manual_block_ip(ip, "AI Chat üzerinden manuel engelleme")

    if success:
        return ChatResponse(
            reply=fmt.result_badge(True, f"**{ip}** engellendi (24 saat). DNS sorgulari reddedilecek"),
            action_type="block_ip",
            action_result={"ip": ip, "blocked": True},
        )
    return ChatResponse(reply=fmt.result_badge(False, f"`{ip}` engellenirken hata oluştu"))


async def _handle_unblock_ip(entities: list[Entity], db: AsyncSession) -> ChatResponse:
    """IP engelini kaldir."""
    from app.workers.threat_analyzer import manual_unblock_ip

    ip_ent = next((e for e in entities if e.type == "ip"), None)
    if not ip_ent:
        return ChatResponse(reply="Engeli kaldirilacak IP adresi bulunamadı. Ornek: `1.2.3.4 engelini kaldir`")

    ip = ip_ent.value
    success = await manual_unblock_ip(ip)

    if success:
        return ChatResponse(
            reply=fmt.result_badge(True, f"**{ip}** engeli kaldırıldı"),
            action_type="unblock_ip",
            action_result={"ip": ip, "unblocked": True},
        )
    return ChatResponse(reply=fmt.result_badge(False, f"`{ip}` engeli kaldirilamadi veya zaten engelli degil"))


# =====================================================================
# Log Sorgulama Handler
# =====================================================================

async def _handle_query_logs(entities: list[Entity], db: AsyncSession, original_text: str = "") -> ChatResponse:
    """DNS sorgu loglarını dogal dil ile sorgula."""
    from datetime import timedelta

    raw_text = original_text

    # 2. Zaman referansi cikar
    time_ref = extract_time_reference(raw_text)
    now = datetime.now()

    if time_ref:
        if "days_ago" in time_ref:
            days = time_ref["days_ago"]
            if days == 0:
                time_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                time_from = now - timedelta(days=days)
                time_from = time_from.replace(hour=0, minute=0, second=0, microsecond=0)
            time_label = "bugun" if days == 0 else f"{days} gun once" if days == 1 else f"son {days} gun"
        elif "hours_ago" in time_ref:
            hours = time_ref["hours_ago"]
            time_from = now - timedelta(hours=hours)
            time_label = f"son {hours} saat"
        elif "minutes_ago" in time_ref:
            mins = time_ref["minutes_ago"]
            time_from = now - timedelta(minutes=mins)
            time_label = f"son {mins} dakika"
        else:
            time_from = now - timedelta(days=1)
            time_label = "son 24 saat"
    else:
        # Varsayilan: son 24 saat
        time_from = now - timedelta(days=1)
        time_label = "son 24 saat"

    # 3. Cihaz cozumle (alias, IP, hostname)
    device, _ = await _resolve_device_smart(entities, db)
    client_ip_filter = None
    device_label = None

    if device:
        client_ip_filter = device.ip_address
        # Alias bilgisi
        aliases = load_aliases()
        alias_name = None
        for akey, ainfo in aliases.items():
            if ainfo.get("device_id") == device.id or ainfo.get("ip") == device.ip_address:
                alias_name = akey
                break
        device_label = alias_name or device.hostname or device.ip_address

    # 4. Ek filtreler: engellenen mi? domain arama? kritik mi?
    text_norm = normalize_turkish(raw_text)

    only_blocked = any(kw in text_norm for kw in [
        "engellen", "engellenmis", "engellendi", "bloke", "bloklanan",
        "yasaklanan", "reddedilen", "blocked",
    ])

    is_critical = any(kw in text_norm for kw in [
        "kritik", "tehlikeli", "şüpheli", "critical", "suspicious",
    ])

    # Domain arama: entity'lerden veya metindeki servis adlarindan
    domain_search = None
    for ent in entities:
        if ent.type == "service":
            svc_domains = ent.metadata.get("domains", [])
            if svc_domains:
                domain_search = svc_domains[0].replace("www.", "")
            break
        elif ent.type == "domain":
            domain_search = ent.value
            break

    # "en cok engellenen" / "en cok sorgulanan" özel durumu
    wants_top_blocked = any(kw in text_norm for kw in ["en cok engellenen", "en fazla engellenen"])
    wants_top_queried = any(kw in text_norm for kw in ["en cok sorgulanan", "en fazla sorgulanan"])

    # 5. SQL sorgusu oluştur
    if wants_top_blocked or wants_top_queried:
        # Top N sorgusu
        stmt = (
            select(
                DnsQueryLog.domain,
                func.count(DnsQueryLog.id).label("cnt"),
            )
            .where(DnsQueryLog.timestamp >= time_from)
        )
        if wants_top_blocked:
            stmt = stmt.where(DnsQueryLog.blocked == True)  # noqa
        if client_ip_filter:
            stmt = stmt.where(DnsQueryLog.client_ip == client_ip_filter)
        stmt = stmt.group_by(DnsQueryLog.domain).order_by(desc("cnt")).limit(15)

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            label = "engellenen" if wants_top_blocked else "sorgulanan"
            return ChatResponse(
                reply=f"**{time_label}** içinde {'bu cihaz için ' if device_label else ''}en cok {label} domain bulunamadı.",
                action_type="query_logs",
            )

        label = "Engellenen" if wants_top_blocked else "Sorgulanan"
        row_dicts = [{"domain": row.domain, "count": row.cnt} for row in rows]
        return ChatResponse(
            reply=fmt.format_top_domains(row_dicts, label, device_label, time_label),
            action_type="query_logs",
            action_result={"type": f"top_{label.lower()}", "count": len(rows)},
        )

    # Normal log sorgusu
    stmt = (
        select(DnsQueryLog)
        .where(DnsQueryLog.timestamp >= time_from)
        .order_by(desc(DnsQueryLog.timestamp))
    )

    if client_ip_filter:
        stmt = stmt.where(DnsQueryLog.client_ip == client_ip_filter)

    if only_blocked:
        stmt = stmt.where(DnsQueryLog.blocked == True)  # noqa

    if is_critical:
        # Kritik = engellenmis + block_reason var
        stmt = stmt.where(DnsQueryLog.blocked == True)  # noqa
        stmt = stmt.where(DnsQueryLog.block_reason.isnot(None))

    if domain_search:
        stmt = stmt.where(DnsQueryLog.domain.contains(escape_like(domain_search)))

    stmt = stmt.limit(20)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    # 6. İstatistik sorgusu (özet için)
    count_stmt = (
        select(func.count(DnsQueryLog.id))
        .where(DnsQueryLog.timestamp >= time_from)
    )
    if client_ip_filter:
        count_stmt = count_stmt.where(DnsQueryLog.client_ip == client_ip_filter)

    total_count = await db.scalar(count_stmt) or 0

    blocked_count_stmt = (
        select(func.count(DnsQueryLog.id))
        .where(DnsQueryLog.timestamp >= time_from)
        .where(DnsQueryLog.blocked == True)  # noqa
    )
    if client_ip_filter:
        blocked_count_stmt = blocked_count_stmt.where(DnsQueryLog.client_ip == client_ip_filter)

    blocked_count = await db.scalar(blocked_count_stmt) or 0

    if not logs:
        filter_desc = ""
        if device_label:
            filter_desc += f" **{device_label}** için"
        if only_blocked:
            filter_desc += " engellenen"
        if domain_search:
            filter_desc += f" `{domain_search}` iceren"

        return ChatResponse(
            reply=f"**{time_label}** içinde{filter_desc} log kaydi bulunamadı.",
            action_type="query_logs",
            action_result={"total": 0},
        )

    # 7. Sonuçlari formatla
    from app.services.timezone_service import format_dt

    filter_info = ""
    if only_blocked:
        filter_info = "sadece engellenenler"
    elif is_critical:
        filter_info = "kritik/şüpheli"

    log_lines = []
    for log in logs:
        ts = format_dt(log.timestamp, "%d/%m %H:%M") if log.timestamp else "?"
        log_lines.append(fmt.log_line(
            timestamp=ts,
            ip=log.client_ip or "?",
            domain=log.domain,
            blocked=log.blocked,
            reason=log.block_reason,
        ))

    return ChatResponse(
        reply=fmt.format_log_results(
            log_lines=log_lines,
            total=total_count,
            blocked=blocked_count,
            shown=len(logs),
            device_label=device_label,
            time_label=time_label,
            filter_info=filter_info,
        ),
        action_type="query_logs",
        action_result={"total": total_count, "blocked": blocked_count, "shown": len(logs)},
    )


def _unknown_response() -> ChatResponse:
    """Anlasilamayan komut için yanit."""
    return ChatResponse(reply=fmt.format_unknown())


# =====================================================================
# LLM Entegrasyonu: Hibrit Cift Motor Yonlendirmesi
# =====================================================================

async def _try_llm_chat(
    message: str,
    db_context: dict,
    db: AsyncSession,
) -> ChatResponse | None:
    """
    LLM ile sohbet dene.
    - tfidf modunda: None dondurur (TF-IDF kullanilir).
    - llm modunda: LLM başarısızsa hata mesaji dondurur (fallback yok).
    - hybrid modunda: LLM başarısızsa None dondurur (TF-IDF fallback).
    """
    try:
        config = await llm_service.get_ai_config()
        if not config or not config["enabled"] or config["chat_mode"] == "tfidf":
            return None

        chat_mode = config["chat_mode"]

        # Son sohbet gecmisini al (LLM baglam için)
        history_result = await db.execute(
            select(ChatMessage)
            .order_by(desc(ChatMessage.id))
            .limit(6)
        )
        history_msgs = list(history_result.scalars().all())
        history_msgs.reverse()
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_msgs
        ]

        # LLM çağrısı
        result = await llm_service.chat(message, db_context, chat_history)

        if not result:
            if chat_mode == "llm":
                return ChatResponse(
                    reply="AI servisi su anda yanit veremiyor. Lütfen ayarları kontrol edin veya daha sonra tekrar deneyin.",
                    action_type="error",
                    action_result=None,
                )
            return None  # hybrid: TF-IDF fallback

        commands_data = result.get("commands", [])
        if not commands_data:
            if chat_mode == "llm":
                return ChatResponse(
                    reply=result.get("raw_response", "AI yanit isle nemedi."),
                    action_type="direct_reply",
                    action_result=None,
                )
            return None

        # direct_reply kontrolü (intent disinda kalan sorular)
        first_cmd = commands_data[0]
        if first_cmd.get("direct_reply"):
            return ChatResponse(
                reply=first_cmd.get("reply", result.get("raw_response", "")),
                action_type="direct_reply",
                action_result=None,
            )

        # JSON komutlari ParsedCommand'a donustur
        parsed_commands = []
        for cmd_data in commands_data:
            entities = []
            for ent in cmd_data.get("entities", []):
                ent_type = ent.get("type", "")
                ent_value = ent.get("value", "")
                ent_meta = dict(ent.get("metadata", {}))

                # LLM service entity'lerine SERVICE_DOMAINS'tan domain listesi ekle
                if ent_type == "service" and "domains" not in ent_meta:
                    svc_key = normalize_turkish(ent_value).lower()
                    if svc_key in SERVICE_DOMAINS:
                        ent_meta["domains"] = SERVICE_DOMAINS[svc_key]
                    else:
                        # Yakin esleme dene
                        for key in SERVICE_DOMAINS:
                            if svc_key in key or key in svc_key:
                                ent_meta["domains"] = SERVICE_DOMAINS[key]
                                break
                    # Hala bulunamadıysa, domain olarak dene (youtube -> youtube.com)
                    if "domains" not in ent_meta:
                        if "." in ent_value:
                            ent_meta["domains"] = [ent_value]
                        else:
                            ent_meta["domains"] = [f"{ent_value}.com"]

                # LLM domain entity: metadata'ya domains ekle
                if ent_type == "domain" and "domains" not in ent_meta:
                    ent_meta["domains"] = [ent_value]

                entities.append(Entity(
                    type=ent_type,
                    value=ent_value,
                    original=ent.get("original", ent_value),
                    confidence=1.0,
                    metadata=ent_meta,
                ))
            parsed_commands.append(ParsedCommand(
                intent=cmd_data.get("intent", "unknown"),
                confidence=1.0,
                entities=entities,
                original_text=message,
            ))

        if not parsed_commands:
            return None

        # Mevcut handler'lar ile calistir
        return await execute_commands(parsed_commands, db)

    except Exception as e:
        logger.error(f"LLM chat hatasi: {e}")
        try:
            config = await llm_service.get_ai_config()
            if config and config.get("chat_mode") == "llm":
                return ChatResponse(
                    reply="AI servisi hatasi oluştu. Hibrit veya TF-IDF moduna gecmeyi deneyin.",
                    action_type="error",
                    action_result=None,
                )
        except Exception as e2:
            logger.warning(f"LLM hata yaniti oluşturma hatasi: {e2}")
        return None  # hybrid/diger: TF-IDF fallback


# =====================================================================
# API Endpointleri
# =====================================================================

@router.post("/send", response_model=ChatResponse)
async def send_message(
    data: ChatRequest, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI asistana mesaj gönder - Hibrit motor: LLM + TF-IDF fallback."""
    # Kullanıcı mesajini kaydet
    user_msg = ChatMessage(
        role="user",
        content=data.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_msg)

    # DB baglam oluştur
    db_context = await _build_db_context(db)

    # LLM yonlendirme (llm veya hybrid modda)
    response = await _try_llm_chat(data.message, db_context, db)

    # LLM başarısız veya tfidf modda -> TF-IDF fallback
    if response is None:
        engine = get_engine()
        commands = engine.parse(data.message, db_context)
        response = await execute_commands(commands, db)

    # Asistan yanitini kaydet
    assistant_msg = ChatMessage(
        role="assistant",
        content=response.reply,
        action_type=response.action_type,
        action_result=json.dumps(response.action_result) if response.action_result else None,
        timestamp=datetime.utcnow(),
    )
    db.add(assistant_msg)

    return response


@router.get("/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sohbet gecmisini getir."""
    result = await db.execute(
        select(ChatMessage)
        .order_by(desc(ChatMessage.id))
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


@router.delete("/history")
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sohbet gecmisini temizle."""
    from sqlalchemy import delete
    await db.execute(delete(ChatMessage))
    return {"message": "Sohbet gecmisi temizlendi"}
