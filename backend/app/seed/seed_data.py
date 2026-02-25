# --- Ajan: MUHAFIZ (THE GUARDIAN) + ANALIST (THE ANALYST) ---
# Ana seeder scripti: MariaDB'yi gercekci test verisi ile doldurur.
# Calistirma: docker exec tonbilai-backend python -m app.seed.seed_data

import asyncio
import random
from datetime import datetime, timedelta

from app.db.session import engine, async_session_factory
from app.db.base import Base
from app.models.profile import Profile, ProfileType
from app.models.device import Device
from app.models.traffic_log import TrafficLog
from app.models.ai_insight import AiInsight, Severity
from app.models.blocklist import Blocklist, BlocklistFormat
from app.models.dns_rule import DnsRule, DnsRuleType
from app.models.dns_query_log import DnsQueryLog
from app.models.dhcp_pool import DhcpPool
from app.models.dhcp_lease import DhcpLease
from app.models.firewall_rule import FirewallRule
from app.models.vpn_peer import VpnPeer, VpnConfig
from app.models.user import User
from app.models.vpn_client import VpnClientServer
from app.models.tls_config import TlsConfig
from app.models.content_category import ContentCategory
from app.models.ai_config import AiConfig
from app.seed.scenarios import (
    PROFILES, DEVICES, SECURITY_SCENARIOS,
    DEFAULT_BLOCKLISTS, DEFAULT_DNS_RULES,
    DEFAULT_DHCP_POOLS, DEFAULT_STATIC_LEASES,
    DEFAULT_FIREWALL_RULES, DEFAULT_VPN_PEERS,
    DEFAULT_ADMIN_USER, DEFAULT_CONTENT_CATEGORIES, DEFAULT_VPN_CLIENT_SERVERS,
    DEFAULT_AI_CONFIG,
)


async def seed():
    """Veritabanini test verileri ile doldur."""

    # Tablolari oluştur
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # --- Profil Seed ---
        profile_map = {}
        for p_data in PROFILES:
            profile = Profile(
                name=p_data["name"],
                profile_type=ProfileType(p_data["profile_type"]),
                allowed_hours=p_data["allowed_hours"],
                content_filters=p_data["content_filters"],
                bandwidth_limit_mbps=p_data["bandwidth_limit_mbps"],
            )
            session.add(profile)
            await session.flush()
            profile_map[p_data["name"]] = profile.id

        # --- Cihaz Seed ---
        device_map = {}
        for d_data in DEVICES:
            device = Device(
                mac_address=d_data["mac"],
                ip_address=d_data["ip"],
                hostname=d_data["hostname"],
                manufacturer=d_data["manufacturer"],
                profile_id=profile_map.get(d_data["profile_name"]),
                is_online=True,
                is_blocked=False,
            )
            session.add(device)
            await session.flush()
            device_map[d_data["hostname"]] = device.id

        # --- Trafik Log Seed (son 24 saatlik simule veri) ---
        domains = {
            "youtube.com": "streaming",
            "netflix.com": "streaming",
            "instagram.com": "social",
            "tiktok.com": "social",
            "google.com": "search",
            "kumar-sitesi.bet": "gambling",
            "school-portal.edu.tr": "education",
            "malware-c2.evil": "malicious",
            "stackoverflow.com": "development",
        }
        now = datetime.utcnow()
        total_logs = 0

        for hours_ago in range(24):
            for _ in range(random.randint(10, 30)):
                domain, category = random.choice(list(domains.items()))
                device_hostname = random.choice(list(device_map.keys()))
                log = TrafficLog(
                    timestamp=now - timedelta(
                        hours=hours_ago,
                        minutes=random.randint(0, 59),
                    ),
                    device_id=device_map[device_hostname],
                    destination_domain=domain,
                    category=category,
                    bytes_sent=random.randint(1_000, 500_000),
                    bytes_received=random.randint(5_000, 5_000_000),
                    protocol=random.choice(["TCP", "UDP", "DNS"]),
                )
                session.add(log)
                total_logs += 1

        # --- Güvenlik Senaryo Icgoruleri ---
        for scenario in SECURITY_SCENARIOS:
            insight = AiInsight(
                timestamp=now - timedelta(hours=random.randint(0, 12)),
                severity=Severity(scenario["expected_severity"]),
                message=(
                    f"[SEED] {scenario['description']}: "
                    f"{scenario['device_hostname']} -> {scenario['domain']}"
                ),
                suggested_action=(
                    f"{scenario['domain']} adresini engelle ve "
                    f"{scenario['device_hostname']} cihazini incele"
                ),
                related_device_id=device_map.get(scenario["device_hostname"]),
                category=(
                    "security"
                    if scenario["expected_severity"] == "critical"
                    else "anomaly"
                ),
            )
            session.add(insight)

        # ===== FAZ 2: DNS ENGELLEME SEED =====

        # --- Blocklist Seed ---
        for bl_data in DEFAULT_BLOCKLISTS:
            blocklist = Blocklist(
                name=bl_data["name"],
                url=bl_data["url"],
                description=bl_data["description"],
                format=BlocklistFormat(bl_data["format"]),
                enabled=bl_data["enabled"],
                update_frequency_hours=bl_data["update_frequency_hours"],
            )
            session.add(blocklist)

        # --- DNS Kural Seed ---
        for rule_data in DEFAULT_DNS_RULES:
            rule = DnsRule(
                domain=rule_data["domain"],
                rule_type=DnsRuleType(rule_data["rule_type"]),
                reason=rule_data["reason"],
                profile_id=profile_map.get(rule_data["profile_name"]) if rule_data["profile_name"] else None,
                added_by="seed",
            )
            session.add(rule)

        # --- DNS Sorgu Log Seed (son 24 saatlik) ---
        blocked_domains = {
            "ad.doubleclick.net", "analytics.tiktok.com", "ad.facebook.com",
            "kumar-sitesi.bet", "malware-c2.evil", "adult-content-1.com",
            "analytics.google.com", "telemetry.microsoft.com",
        }
        dns_domains = [
            "youtube.com", "google.com", "ad.doubleclick.net", "instagram.com",
            "analytics.tiktok.com", "netflix.com", "ad.facebook.com",
            "kumar-sitesi.bet", "school-portal.edu.tr", "stackoverflow.com",
            "malware-c2.evil", "weather.com", "wikipedia.org",
            "analytics.google.com", "telemetry.microsoft.com",
        ]
        device_hostnames = list(device_map.keys())
        total_dns = 0

        for hours_ago in range(24):
            for _ in range(random.randint(20, 60)):
                domain = random.choice(dns_domains)
                device_hostname = random.choice(device_hostnames)
                is_blocked = domain in blocked_domains
                dns_log = DnsQueryLog(
                    timestamp=now - timedelta(hours=hours_ago, minutes=random.randint(0, 59)),
                    device_id=device_map[device_hostname],
                    client_ip=f"192.168.1.{100 + device_hostnames.index(device_hostname) + 1}",
                    domain=domain,
                    query_type=random.choice(["A", "AAAA", "CNAME"]),
                    blocked=is_blocked,
                    block_reason="blocklist" if is_blocked else None,
                    upstream_response_ms=1 if is_blocked else random.randint(5, 150),
                    answer_ip="0.0.0.0" if is_blocked else f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                )
                session.add(dns_log)
                total_dns += 1

        # ===== FAZ 2: DHCP SEED =====

        # --- DHCP Havuz Seed ---
        pool_map = {}
        for pool_data in DEFAULT_DHCP_POOLS:
            pool = DhcpPool(
                name=pool_data["name"],
                subnet=pool_data["subnet"],
                netmask=pool_data["netmask"],
                range_start=pool_data["range_start"],
                range_end=pool_data["range_end"],
                gateway=pool_data["gateway"],
                dns_servers=pool_data["dns_servers"],
                lease_time_seconds=pool_data["lease_time_seconds"],
                enabled=pool_data["enabled"],
            )
            session.add(pool)
            await session.flush()
            pool_map[pool_data["name"]] = pool.id

        # --- DHCP Lease Seed (tum cihazlar için) ---
        static_macs = {s["mac"] for s in DEFAULT_STATIC_LEASES}
        for d_data in DEVICES:
            is_static = d_data["mac"] in static_macs
            # Misafir cihazlar Misafir AG havuzunda
            pool_name = "Misafir AG" if d_data["profile_name"] == "Misafir" else "Ana AG"
            lease = DhcpLease(
                mac_address=d_data["mac"],
                ip_address=d_data["ip"],
                hostname=d_data["hostname"],
                lease_start=now - timedelta(hours=random.randint(1, 20)),
                lease_end=now + timedelta(hours=random.randint(4, 24)) if not is_static else None,
                is_static=is_static,
                device_id=device_map[d_data["hostname"]],
                pool_id=pool_map.get(pool_name),
            )
            session.add(lease)

        # ===== FAZ 2.5: FIREWALL SEED =====
        for fw_data in DEFAULT_FIREWALL_RULES:
            fw_rule = FirewallRule(
                name=fw_data["name"],
                description=fw_data.get("description"),
                direction=fw_data["direction"],
                protocol=fw_data["protocol"],
                port=fw_data.get("port"),
                port_end=fw_data.get("port_end"),
                source_ip=fw_data.get("source_ip"),
                dest_ip=fw_data.get("dest_ip"),
                action=fw_data["action"],
                enabled=fw_data.get("enabled", True),
                priority=fw_data.get("priority", 100),
                log_packets=fw_data.get("log_packets", False),
            )
            session.add(fw_rule)

        # ===== FAZ 3: KULLANICI SEED =====
        admin = User(
            username=DEFAULT_ADMIN_USER["username"],
            password_hash=User.hash_password(DEFAULT_ADMIN_USER["password"]),
            display_name=DEFAULT_ADMIN_USER["display_name"],
            is_admin=DEFAULT_ADMIN_USER["is_admin"],
        )
        session.add(admin)

        # ===== FAZ 3: ICERIK KATEGORI SEED =====
        for cat_data in DEFAULT_CONTENT_CATEGORIES:
            category = ContentCategory(
                key=cat_data["key"],
                name=cat_data["name"],
                description=cat_data["description"],
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
                example_domains=cat_data.get("example_domains"),
                domain_count=cat_data.get("domain_count", 0),
                enabled=True,
            )
            session.add(category)

        # ===== FAZ 3: DIS VPN ISTEMCI SEED =====
        for srv_data in DEFAULT_VPN_CLIENT_SERVERS:
            vpn_srv = VpnClientServer(
                name=srv_data["name"],
                country=srv_data["country"],
                country_code=srv_data["country_code"],
                endpoint=srv_data["endpoint"],
                public_key=srv_data["public_key"],
                interface_address=srv_data.get("interface_address"),
                allowed_ips=srv_data.get("allowed_ips", "0.0.0.0/0, ::/0"),
                dns_servers=srv_data.get("dns_servers"),
                mtu=srv_data.get("mtu", 1420),
            )
            session.add(vpn_srv)

        # ===== FAZ 3: TLS YAPILANDIRMA SEED =====
        tls_config = TlsConfig(
            domain=None,
            doh_enabled=False,
            dot_enabled=False,
            https_enabled=False,
            enabled=False,
        )
        session.add(tls_config)

        # ===== FAZ 3.5 v9: AI CONFIG SEED =====
        ai_config = AiConfig(**DEFAULT_AI_CONFIG)
        session.add(ai_config)

        # ===== FAZ 2.5: VPN SEED =====
        import base64, os
        vpn_config = VpnConfig(
            interface_name="wg0",
            listen_port=51820,
            server_private_key=base64.b64encode(os.urandom(32)).decode(),
            server_public_key=base64.b64encode(os.urandom(32)).decode(),
            server_address="10.0.0.1/24",
            dns_server="10.0.0.1",
            enabled=False,
            route_all_traffic=False,
        )
        session.add(vpn_config)

        for peer_data in DEFAULT_VPN_PEERS:
            priv_key = base64.b64encode(os.urandom(32)).decode()
            pub_key = base64.b64encode(os.urandom(32)).decode()
            peer = VpnPeer(
                name=peer_data["name"],
                public_key=pub_key,
                private_key=priv_key,
                allowed_ips=peer_data["allowed_ips"],
                dns_servers=peer_data.get("dns_servers", "10.0.0.1"),
                persistent_keepalive=peer_data.get("persistent_keepalive", 25),
                enabled=True,
                is_connected=False,
            )
            session.add(peer)

        await session.commit()

        print(
            f"Seed tamamlandi:\n"
            f"  1 admin kullanıcı ({DEFAULT_ADMIN_USER['username']})\n"
            f"  {len(PROFILES)} profil, {len(DEVICES)} cihaz\n"
            f"  ~{total_logs} trafik logu, {len(SECURITY_SCENARIOS)} AI icgorusu\n"
            f"  {len(DEFAULT_BLOCKLISTS)} blocklist, {len(DEFAULT_DNS_RULES)} DNS kural\n"
            f"  ~{total_dns} DNS sorgu logu\n"
            f"  {len(DEFAULT_DHCP_POOLS)} DHCP havuz, {len(DEVICES)} DHCP lease\n"
            f"  {len(DEFAULT_STATIC_LEASES)} statik IP ataması\n"
            f"  {len(DEFAULT_FIREWALL_RULES)} firewall kural\n"
            f"  1 VPN konfigürasyon, {len(DEFAULT_VPN_PEERS)} VPN peer\n"
            f"  {len(DEFAULT_CONTENT_CATEGORIES)} içerik filtre kategorisi\n"
            f"  {len(DEFAULT_VPN_CLIENT_SERVERS)} dis VPN sunucusu\n"
            f"  1 TLS yapılandirma\n"
            f"  1 AI yapılandirma"
        )


if __name__ == "__main__":
    asyncio.run(seed())
