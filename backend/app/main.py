# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Uygulama giriş noktasi: lifespan olaylari, CORS, güvenlik middleware,
# router baglama ve arka plan isci başlatma.
# TEST MODU: Sanal trafik/DHCP simulatorleri DEVRE DISI.
# Sadece gercek ev agi trafiği islenir.

import asyncio
import logging
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings
from app.api.v1.router import api_v1_router
from app.db.session import engine
from app.db.base import Base
from app.db.redis_client import get_redis, redis_pool
from app.hal.driver_factory import get_network_driver
from app.workers.blocklist_worker import (
    start_blocklist_worker,
    rebuild_all_category_domains,
    rebuild_all_profile_domains,
    rebuild_device_profile_cache,
)
from app.workers.dns_proxy import start_dns_proxy
from app.workers.device_discovery import start_device_discovery_worker
from app.workers.dhcp_worker import start_dhcp_worker
from app.workers.threat_analyzer import start_threat_analyzer_worker
from app.workers.telegram_worker import start_telegram_worker
from app.workers.llm_log_analyzer import start_llm_log_analyzer
from app.workers.mac_resolver_worker import start_mac_resolver_worker
from app.workers.log_signer import start_log_signer
from app.workers.traffic_monitor import start_traffic_monitor
from app.workers.bandwidth_monitor import start_bandwidth_monitor
from app.workers.flow_tracker import start_flow_tracker
from app.services.system_monitor_service import start_system_monitor_worker
from app.workers.wifi_monitor import start_wifi_monitor
from app.workers.db_retention import start_db_retention_worker
from app.workers.traffic_baseline import start_traffic_baseline
from app.workers.daily_summary import start_daily_summary
from app.workers.ip_reputation import start_ip_reputation

# Tum modelleri import et (tablo oluşturma için)
from app.models import (  # noqa: F401
    Profile, Device, TrafficLog, AiInsight,
    Blocklist, DnsRule, DnsQueryLog,
    DhcpPool, DhcpLease,
    FirewallRule, VpnPeer, VpnConfig,
    User, VpnClientServer, ChatMessage, TlsConfig, ContentCategory,
    BlockedService, DeviceBlockedService, TelegramConfig, DeviceConnectionLog, CategoryBlocklist,
    TrustedIp, BlockedIp, DeviceCustomRule, AiConfig,
    LogSignature,
    DeviceTrafficSnapshot,
    DdosConfig,
    ConnectionFlow,
    WifiConfig,
    SecurityConfig,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tonbilai")

settings = get_settings()


async def _sync_firewall_on_startup(driver):
    """Başlangicta nftables tablolari ve engellenmis cihazlari senkronize et."""
    from app.hal import linux_nftables as nft
    from app.db.session import async_session_factory as AsyncSessionLocal
    from sqlalchemy import select

    try:
        # 1. nftables tonbilai tablosunu oluştur (DDoS korumasi dahil)
        if hasattr(driver, 'initialize'):
            await driver.initialize()
            logger.info("nftables tonbilai tablosu hazir")

        # 2. Engellenmis cihazlari DB'den nftables'a senkronize et
        from app.models.device import Device
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Device).where(Device.is_blocked == True)
            )
            blocked_devices = result.scalars().all()
            blocked_macs = [d.mac_address for d in blocked_devices if d.mac_address]

            if blocked_macs:
                await nft.sync_blocked_macs(blocked_macs)
                logger.info(f"{len(blocked_macs)} engellenmis cihaz nftables'a eklendi")

            # 2b. Engelli cihaz ID'lerini Redis'e yaz (DNS proxy block page icin)
            try:
                from app.db.redis_client import get_redis
                redis = await get_redis()
                await redis.delete("dns:blocked_device_ids")
                if blocked_devices:
                    blocked_ids = [str(d.id) for d in blocked_devices]
                    await redis.sadd("dns:blocked_device_ids", *blocked_ids)
                    logger.info(f"{len(blocked_ids)} engelli cihaz ID'si Redis'e yazildi (block page)")
            except Exception as e:
                logger.warning(f"Redis blocked device sync hatasi: {e}")

        # 3. Firewall kurallarini DB'den nftables'a senkronize et
        from app.models.firewall_rule import FirewallRule
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(FirewallRule).where(FirewallRule.enabled == True)
            )
            rules = result.scalars().all()
            rule_dicts = []
            for rule in rules:
                rule_dicts.append({
                    "id": rule.id,
                    "name": rule.name,
                    "direction": rule.direction.value if hasattr(rule.direction, 'value') else rule.direction,
                    "protocol": rule.protocol.value if hasattr(rule.protocol, 'value') else rule.protocol,
                    "port": rule.port,
                    "port_end": rule.port_end,
                    "source_ip": rule.source_ip,
                    "dest_ip": rule.dest_ip,
                    "action": rule.action.value if hasattr(rule.action, 'value') else rule.action,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                    "log_packets": rule.log_packets,
                })

            if rule_dicts:
                await nft.sync_firewall_rules(rule_dicts)
                logger.info(f"{len(rule_dicts)} firewall kuralı nftables'a senkronize edildi")

    except Exception as e:
        logger.error(f"Firewall başlangıç senkronizasyon hatasi: {e}")
        import traceback
        traceback.print_exc()


async def _restore_bandwidth_limits():
    """Başlangicta DB'deki bant genisligi limitlerini tc kurallarini ile yeniden uygula."""
    await asyncio.sleep(5)  # Diger servislerin hazir olmasini bekle
    try:
        from app.db.session import async_session_factory as AsyncSessionLocal
        from app.models.device import Device
        from app.hal import linux_tc as tc
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Device).where(
                    Device.bandwidth_limit_mbps.isnot(None),
                    Device.bandwidth_limit_mbps > 0,
                )
            )
            devices = result.scalars().all()

            if not devices:
                return

            for device in devices:
                try:
                    await tc.add_device_limit(
                        device.mac_address, device.bandwidth_limit_mbps
                    )
                    logger.info(
                        f"BW limit geri yuklendi: {device.mac_address} "
                        f"-> {device.bandwidth_limit_mbps}Mbps"
                    )
                except Exception as e:
                    logger.error(
                        f"BW limit geri yüklenemedi ({device.mac_address}): {e}"
                    )

            logger.info(f"{len(devices)} cihazin bant genisligi limiti yeniden uygulandi")
    except Exception as e:
        logger.error(f"BW limit geri yükleme hatasi: {e}")


async def _sync_vpn_on_startup():
    """wg0 calisiyorsa nftables masquerade kurallarini kontrol et / ekle."""
    from app.hal.linux_nftables import (
        ensure_nat_postrouting_chain, add_vpn_nft_rules, persist_nftables, run_nft
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "link", "show", "wg0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            return  # wg0 yok, VPN başlatilmamis
        # Masquerade kuralı zaten var mi?
        out = await run_nft(["list", "table", "inet", "nat"], check=False)
        if "vpn_wg0_masq" in out:
            logger.info("VPN başlangıç sync: masquerade kurallari zaten mevcut")
            return
        await ensure_nat_postrouting_chain()
        await add_vpn_nft_rules("wg0", "10.13.13.0/24")
        await persist_nftables()
        logger.info("VPN başlangıç sync: wg0 masquerade kurallari eklendi")
    except Exception as e:
        logger.error(f"VPN başlangıç sync hatasi: {e}")


async def _ddos_anomaly_monitor():
    """DDoS counter delta izleme — her 60 saniyede kontrol, threshold asiminda uyari."""
    await asyncio.sleep(120)  # Başlangicta 2 dakika bekle
    logger.info("DDoS anomali izleme worker başlatildi (60sn aralık)")
    while True:
        try:
            from app.services.ddos_service import check_ddos_anomaly_and_alert
            alerts = await check_ddos_anomaly_and_alert()
            if alerts:
                logger.warning(f"DDoS anomali tespit edildi: {len(alerts)} koruma tetiklendi")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"DDoS anomali monitor hatasi: {e}")
        await asyncio.sleep(60)


def _sd_notify(msg: str):
    """systemd notify gönder (NOTIFY_SOCKET varsa)."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            if addr.startswith("@"):
                addr = "\0" + addr[1:]
            sock.connect(addr)
            sock.sendall(msg.encode())
        finally:
            sock.close()
    except Exception:
        pass


async def _watchdog_kick_worker():
    """Her 30 saniyede systemd watchdog'a kick gönder."""
    if not os.environ.get("NOTIFY_SOCKET"):
        return  # systemd notify yok, worker başlatma
    logger.info("systemd watchdog kick worker başlatildi (30sn aralık)")
    while True:
        try:
            _sd_notify("WATCHDOG=1")
        except asyncio.CancelledError:
            break
        except Exception:
            pass
        await asyncio.sleep(30)


async def _sync_wifi_on_startup():
    """WiFi config DB'den oku, enabled ise hostapd baslat."""
    try:
        from app.models.wifi_config import WifiConfig
        from app.hal.wifi_driver import write_hostapd_config, start_wifi_ap, set_mac_filter
        from app.db.session import async_session_factory
        from sqlalchemy import select as sel
        import json as _json

        async with async_session_factory() as db:
            result = await db.execute(sel(WifiConfig).limit(1))
            config = result.scalar_one_or_none()
            if config and config.enabled:
                mac_list = []
                if config.mac_filter_list:
                    try:
                        mac_list = _json.loads(config.mac_filter_list)
                    except Exception:
                        pass
                hostapd_dict = {
                    "ssid": config.ssid,
                    "password": config.password,
                    "channel": config.channel,
                    "band": config.band,
                    "tx_power": config.tx_power,
                    "hidden_ssid": config.hidden_ssid,
                    "mac_filter_mode": config.mac_filter_mode or "disabled",
                    "mac_filter_list": mac_list,
                }
                await write_hostapd_config(hostapd_dict)
                await set_mac_filter(config.mac_filter_mode or "disabled", mac_list)
                await start_wifi_ap()
                logger.info("WiFi AP baslatildi (startup recovery)")
    except Exception as e:
        logger.error(f"WiFi startup sync hatasi: {e}")


async def _wifi_schedule_worker():
    """WiFi zamanlama worker: Her 60s kontrol, schedule araliginda AP ac/kapat."""
    await asyncio.sleep(60)  # Baslangicta 1 dakika bekle
    logger.info("WiFi zamanlama worker baslatildi (60sn aralik)")
    while True:
        try:
            from app.models.wifi_config import WifiConfig
            from app.hal.wifi_driver import start_wifi_ap, stop_wifi_ap, write_hostapd_config
            from app.db.session import async_session_factory
            from sqlalchemy import select as sel
            from datetime import datetime
            import json as _json

            async with async_session_factory() as db:
                result = await db.execute(sel(WifiConfig).limit(1))
                config = result.scalar_one_or_none()

                if config and config.schedule_enabled and config.schedule_start and config.schedule_stop:
                    now = datetime.now().strftime("%H:%M")
                    start = config.schedule_start
                    stop = config.schedule_stop

                    # Aralik icinde mi? (start < stop: normal, start > stop: gece arasi)
                    if start <= stop:
                        in_range = start <= now < stop
                    else:
                        in_range = now >= start or now < stop

                    if in_range and not config.enabled:
                        # Zamanlamaya gore ac
                        mac_list = []
                        if config.mac_filter_list:
                            try:
                                mac_list = _json.loads(config.mac_filter_list)
                            except Exception:
                                pass
                        hostapd_dict = {
                            "ssid": config.ssid,
                            "password": config.password,
                            "channel": config.channel,
                            "band": config.band,
                            "tx_power": config.tx_power,
                            "hidden_ssid": config.hidden_ssid,
                            "mac_filter_mode": config.mac_filter_mode or "disabled",
                            "mac_filter_list": mac_list,
                        }
                        await write_hostapd_config(hostapd_dict)
                        await start_wifi_ap()
                        config.enabled = True
                        await db.commit()
                        logger.info(f"WiFi AP zamanlama ile acildi ({now})")
                    elif not in_range and config.enabled:
                        # Zamanlamaya gore kapat
                        await stop_wifi_ap()
                        config.enabled = False
                        await db.commit()
                        logger.info(f"WiFi AP zamanlama ile kapatildi ({now})")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"WiFi zamanlama worker hatasi: {e}")
        await asyncio.sleep(60)


async def _sync_security_config_on_startup():
    """DB'deki SecurityConfig'i oku, Redis security:config HASH'e push et."""
    try:
        from app.models.security_config import SecurityConfig
        from app.api.v1.security_settings import _push_config_to_redis, _get_or_create_config
        from app.db.session import async_session_factory

        async with async_session_factory() as db:
            config = await _get_or_create_config(db)
            await _push_config_to_redis(config)
            logger.info("Guvenlik ayarlari baslangic sync tamamlandi")
    except Exception as e:
        logger.error(f"Guvenlik ayarlari baslangic sync hatasi: {e}")
        import traceback
        traceback.print_exc()


async def _sync_ddos_on_startup():
    """DB'deki DDoS config'ini oku, nftables/sysctl/nginx kurallarini uygula."""
    try:
        from app.services.ddos_service import apply_all
        from app.models.ddos_config import DdosConfig
        from app.db.session import async_session_factory
        from sqlalchemy import select as sel

        async with async_session_factory() as db:
            result = await db.execute(sel(DdosConfig))
            config = result.scalar_one_or_none()
            if not config:
                config = DdosConfig()
                db.add(config)
                await db.commit()
                await db.refresh(config)

            results = await apply_all(config)
            logger.info(f"DDoS başlangıç sync tamamlandi: {results}")
    except Exception as e:
        logger.error(f"DDoS başlangıç sync hatasi: {e}")
        import traceback
        traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yasam dongusu: başlangıç ve kapanma olaylari."""
    logger.info("TonbilAiOS Backend başlatiliyor... (TEST MODU - sanal veri YOK)")
    logger.info(f"Ortam: {settings.ENVIRONMENT}")

    # Tablolari oluştur (ilk calistirmada)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Veritabani tablolari oluşturuldu/dogrulandi.")

    # Migration: connection_flows tablosuna direction + dst_device_id sutunlari
    from sqlalchemy import text
    async with engine.begin() as conn:
        for stmt in [
            "ALTER TABLE connection_flows ADD COLUMN direction VARCHAR(10) DEFAULT NULL",
            "ALTER TABLE connection_flows ADD COLUMN dst_device_id INT DEFAULT NULL",
        ]:
            try:
                await conn.execute(text(stmt))
                logger.info(f"Migration OK: {stmt[:60]}...")
            except Exception:
                pass  # Sutun zaten varsa hata verir, sessizce gec
        # Index'ler (create_all ile de olusabilir ama garanti olsun)
        for idx_stmt in [
            "CREATE INDEX IF NOT EXISTS idx_cf_direction ON connection_flows (direction)",
            "CREATE INDEX IF NOT EXISTS idx_cf_dst_device ON connection_flows (dst_device_id)",
        ]:
            try:
                await conn.execute(text(idx_stmt))
            except Exception:
                pass

        # Migration: devices tablosuna is_iptv sutunu
        try:
            await conn.execute(text("ALTER TABLE devices ADD COLUMN is_iptv BOOLEAN DEFAULT FALSE"))
            logger.info("Migration OK: devices.is_iptv sutunu eklendi")
        except Exception:
            pass  # Sutun zaten varsa sessizce gec

    # Redis ve HAL surucusunu başlat
    redis_client = await get_redis()
    driver = await get_network_driver(redis_client)

    # App state'e kaydet (dependency injection için)
    app.state.redis = redis_client
    app.state.driver = driver

    # Servis tanimlarini seed et (AdGuard registry'den)
    from app.seed.seed_services import seed_blocked_services
    asyncio.create_task(seed_blocked_services(redis_client))

    # Cihaz-servis Redis mapping'lerini yeniden oluştur
    from app.api.v1.services import rebuild_all_device_services_redis
    asyncio.create_task(rebuild_all_device_services_redis(redis_client))

    # Cihaz özel kural Redis mapping'lerini yeniden oluştur
    from app.api.v1.device_custom_rules import rebuild_all_device_custom_rules_redis
    asyncio.create_task(rebuild_all_device_custom_rules_redis(redis_client))

    # Güvenilir IP'leri DB'den threat_analyzer'a yukle
    # ONEMLI: DNS Proxy baslamadan ONCE yuklenmeli (race condition onleme)
    from app.api.v1.ip_management import sync_trusted_ips_on_startup
    await sync_trusted_ips_on_startup()

    # Firewall başlangıç senkronizasyonu: nftables tablolari + engellenmis cihazlar
    await _sync_firewall_on_startup(driver)

    # Engelli IP'leri Redis'ten nftables'a senkronize et
    from app.workers.threat_analyzer import sync_blocked_ips_to_nftables
    await sync_blocked_ips_to_nftables()

    # VPN (wg0) calisiyorsa masquerade kurallarini ekle
    await _sync_vpn_on_startup()

    # DDoS koruma kurallarini DB'den oku ve uygula
    await _sync_ddos_on_startup()

    # Guvenlik ayarlarini DB'den Redis'e push et (worker hot-reload icin)
    await _sync_security_config_on_startup()

    # WiFi AP: DB'de enabled ise hostapd baslat
    await _sync_wifi_on_startup()

    # Bridge isolation: router modu — modem sadece Pi MAC'ini gorur
    # L2 forwarding drop + NAT MASQUERADE + sysctl/modules/nftables persistence
    try:
        from app.hal.linux_nftables import ensure_bridge_isolation, ensure_bridge_isolation_persistence
        await ensure_bridge_isolation()
        await ensure_bridge_isolation_persistence()
        logger.info("Bridge isolation ve persistence kurallari hazir (router modu)")
    except Exception as e:
        logger.error(f"Bridge isolation kurulum hatasi: {e}")

    # IPTV nftables kurallari + Redis sync
    try:
        from app.hal.linux_nftables import ensure_iptv_rules
        await ensure_iptv_rules()
        # IPTV cihaz IP'lerini Redis'e yukle
        from app.models.device import Device as DeviceModel
        from sqlalchemy import select as sa_select
        from app.db.session import async_session_factory as _iptv_session_factory
        async with _iptv_session_factory() as _iptv_session:
            _iptv_result = await _iptv_session.execute(
                sa_select(DeviceModel).where(DeviceModel.is_iptv == True)  # noqa: E712
            )
            _iptv_devices = _iptv_result.scalars().all()
            if _iptv_devices:
                _iptv_ips = [d.ip_address for d in _iptv_devices if d.ip_address]
                if _iptv_ips:
                    await redis_client.delete("iptv:device_ids")
                    await redis_client.sadd("iptv:device_ids", *_iptv_ips)
                    logger.info(f"IPTV cihazlar Redis'e yuklendi: {len(_iptv_ips)} cihaz")
        logger.info("IPTV nftables kurallari ve Redis sync hazir")
    except Exception as e:
        logger.error(f"IPTV kurulum hatasi: {e}")

    # Kategori/profil DNS domain setlerini blocklist cache hazir olduktan sonra olustur
    async def _build_category_profile_cache():
        """Blocklist cache hazir olduktan sonra kategori/profil domain setlerini olustur."""
        await asyncio.sleep(10)  # Blocklist worker'in ilk yuklemeyi bitirmesini bekle
        try:
            await rebuild_all_category_domains(redis_client)
            await rebuild_all_profile_domains(redis_client)
            await rebuild_device_profile_cache(redis_client)
            logger.info("Kategori/profil DNS cache basariyla olusturuldu")
        except Exception as e:
            logger.error(f"Kategori/profil DNS cache hatasi: {e}")

    asyncio.create_task(_build_category_profile_cache())

    # Arka plan iscilerini başlat
    # SADECE blocklist worker ve DNS proxy - sanal simulator YOK
    blocklist_task = asyncio.create_task(start_blocklist_worker(driver))

    # DNS Proxy - gercek DNS sinkhole (port 53)
    dns_proxy_task = asyncio.create_task(start_dns_proxy(settings.REDIS_URL))
    logger.info("DNS Proxy iscisi başlatildi (port 53).")

    # Cihaz kesfi worker - offline cihazlari isaretler
    discovery_task = asyncio.create_task(start_device_discovery_worker())

    # DHCP worker - dnsmasq lease senkronizasyonu
    dhcp_task = asyncio.create_task(start_dhcp_worker())

    # Tehdit analizci worker - dis IP flood, DGA, şüpheli sorgu tespiti
    threat_task = asyncio.create_task(start_threat_analyzer_worker())

    # Telegram Bot worker - mesaj polling
    telegram_task = asyncio.create_task(start_telegram_worker())

    # Sistem Monitörü worker - RPi5 donanım metrikleri
    system_monitor_task = asyncio.create_task(start_system_monitor_worker())

    # LLM Log Analyzer worker - periyodik DNS log analizi
    llm_analyzer_task = asyncio.create_task(start_llm_log_analyzer())

    # MAC Resolver worker - placeholder MAC cozumleme (ARP tablosu)
    mac_resolver_task = asyncio.create_task(start_mac_resolver_worker())

    # 5651 Kanun Uyumu: Gunluk log imzalama worker
    log_signer_task = asyncio.create_task(start_log_signer())

    # Trafik izleme worker - conntrack tabanli gercek trafik olcumu
    traffic_monitor_task = asyncio.create_task(start_traffic_monitor())

    # Bandwidth izleme worker - nftables bridge counter ile gercek zamanli hiz olcumu
    bandwidth_monitor_task = asyncio.create_task(start_bandwidth_monitor())

    # Flow tracker worker - per-flow baglanti takibi (conntrack -> Redis + DB)
    flow_tracker_task = asyncio.create_task(start_flow_tracker())

    # Kayıtlı bant genisligi limitlerini yeniden uygula (tc kurallarini başlat)
    asyncio.create_task(_restore_bandwidth_limits())

    # DDoS anomali izleme worker - periyodik counter kontrolü + uyari
    ddos_monitor_task = asyncio.create_task(_ddos_anomaly_monitor())

    # WiFi zamanlama worker - schedule'a gore AP ac/kapat
    wifi_schedule_task = asyncio.create_task(_wifi_schedule_worker())

    # WiFi monitor worker - bagli istemci bilgilerini Redis'e yaz (30sn)
    wifi_monitor_task = asyncio.create_task(start_wifi_monitor())

    # Veritabani retention worker - eski kayitlari periyodik temizler (6sa)
    db_retention_task = asyncio.create_task(start_db_retention_worker())

    # Welford Z-score adaptif anomali tespiti (10s aralik, 120s baslangic gecikmesi)
    baseline_task = asyncio.create_task(start_traffic_baseline())

    # Gunluk Telegram guvenlik ozeti (her gun 08:00)
    daily_summary_task = asyncio.create_task(start_daily_summary())

    # Lokal IP blocklist sync worker — ucretsiz IP listelerini indirir (60s baslangic, 1h aralik)
    from app.workers.ip_blocklist_sync import start_blocklist_sync as start_ip_blocklist_sync
    ip_blocklist_task = asyncio.create_task(start_ip_blocklist_sync())

    # IP itibar kontrolu — AbuseIPDB + GeoIP (5dk aralik, 180s baslangic gecikmesi)
    ip_reputation_task = asyncio.create_task(start_ip_reputation())

    # systemd watchdog kick worker
    watchdog_task = asyncio.create_task(_watchdog_kick_worker())

    logger.info("Arka plan iscileri başlatildi (blocklist + DNS proxy + cihaz kesfi + DHCP + tehdit analizci + telegram + sistem monitörü + LLM log analyzer + MAC resolver + 5651 log imzalama + trafik izleme + bandwidth monitor + flow tracker + DDoS monitor + WiFi schedule + WiFi monitor + DB retention + Welford baseline + gunluk ozet + IP reputation + watchdog).")

    # systemd'ye hazir sinyali gönder
    _sd_notify("READY=1")
    logger.info("systemd READY=1 sinyali gönderildi")

    yield  # Uygulama calisiyor

    # Kapanma
    logger.info("TonbilAiOS Backend kapaniyor...")
    # HTTP connection pool temizligi
    from app.services.http_pool import close_all as close_http_pool
    await close_http_pool()
    blocklist_task.cancel()
    dns_proxy_task.cancel()
    discovery_task.cancel()
    dhcp_task.cancel()
    threat_task.cancel()
    telegram_task.cancel()
    system_monitor_task.cancel()
    llm_analyzer_task.cancel()
    mac_resolver_task.cancel()
    log_signer_task.cancel()
    traffic_monitor_task.cancel()
    bandwidth_monitor_task.cancel()
    flow_tracker_task.cancel()
    ddos_monitor_task.cancel()
    wifi_schedule_task.cancel()
    wifi_monitor_task.cancel()
    db_retention_task.cancel()
    baseline_task.cancel()
    daily_summary_task.cancel()
    ip_blocklist_task.cancel()
    ip_reputation_task.cancel()
    watchdog_task.cancel()
    await redis_pool.aclose()
    await engine.dispose()


class CSRFMiddleware(BaseHTTPMiddleware):
    """State-değiştiren isteklerde Origin header kontrol et (CSRF korumasi)."""

    async def dispatch(self, request: Request, call_next):
        # Sadece state-değiştiren HTTP metodlari için kontrol
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            # Browser disindaki istemciler Origin göndermez - bunlari gecir
            if origin:
                allowed = settings.CORS_ORIGINS.split(",")
                if origin not in allowed:
                    logger.warning(f"CSRF: Reddedilen origin: {origin}")
                    return Response(
                        content='{"detail":"CSRF: Geçersiz origin"}',
                        status_code=403,
                        media_type="application/json",
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Tum HTTP yanitlarina güvenlik basliklarini ekler."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        is_api = request.url.path.startswith("/api/")

        # Clickjacking korunmasi
        response.headers["X-Frame-Options"] = "DENY"
        # MIME type sniffing onleme
        response.headers["X-Content-Type-Options"] = "nosniff"
        # XSS filtresi
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer bilgisi kontrolü
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Cache-Control: hassas veri icerebilecek API yanitlari için
        if is_api:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        # HSTS (HTTPS zorlama) - uzaktan erişim için
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Permissions-Policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Content-Security-Policy (CSP) - SADECE HTML sayfalari için
        # API yanitlarinda CSP gereksiz ve dis erişimde sorun cikarabilir
        if not is_api:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://wall.tonbilx.com https://guard.tonbilx.com wss: ws:; "
                "font-src 'self' data:; "
                "frame-ancestors 'none'"
            )
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        # Ek güvenlik basliklari
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return response


app = FastAPI(
    title="TonbilAiOS",
    description="Yapay Zeka Destekli Router Isletim Sistemi",
    version="0.3.0",
    lifespan=lifespan,
)

# Güvenlik baslik middleware'i (en ustte - tum yanitlara uygulanir)
app.add_middleware(SecurityHeadersMiddleware)

# CSRF korumasi (state-değiştiren isteklerde Origin kontrolü)
app.add_middleware(CSRFMiddleware)

# CORS - yalnizca gerekli HTTP metodlari ve basliklar
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# API router'larini bagla
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Saglik kontrolü endpoint'i (hassas bilgi icermez)."""
    return {"status": "healthy"}
