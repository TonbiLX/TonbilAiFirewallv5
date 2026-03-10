# --- Ajan: MIMAR (THE ARCHITECT) ---
# v1 API Router: tum route modüllerini birlestirir.

from fastapi import APIRouter
from app.api.v1 import (
    profiles, devices, traffic, insights, dashboard, ws,
    dns, dhcp, firewall, vpn, wifi,
    auth, chat, vpn_client, tls, content_categories,
    services, system_logs, system_time, telegram,
    ip_management, system_monitor, device_custom_rules,
    ai_settings, ddos, system_management, security_settings,
    ip_reputation, push,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Kimlik Doğrulama"])
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["Profiller"])
api_v1_router.include_router(devices.router, prefix="/devices", tags=["Cihazlar"])
api_v1_router.include_router(traffic.router, prefix="/traffic", tags=["Trafik"])
api_v1_router.include_router(insights.router, prefix="/insights", tags=["AI Icgoruler"])
api_v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_v1_router.include_router(dns.router, prefix="/dns", tags=["DNS Engelleme"])
api_v1_router.include_router(dhcp.router, prefix="/dhcp", tags=["DHCP Sunucu"])
api_v1_router.include_router(firewall.router, prefix="/firewall", tags=["Güvenlik Duvarı"])
api_v1_router.include_router(ip_management.router, prefix="/ip-management", tags=["IP Yönetimi"])
api_v1_router.include_router(vpn.router, prefix="/vpn", tags=["VPN - WireGuard"])
api_v1_router.include_router(vpn_client.router, prefix="/vpn-client", tags=["Dış VPN İstemci"])
api_v1_router.include_router(tls.router, prefix="/tls", tags=["TLS Şifreleme"])
api_v1_router.include_router(content_categories.router, prefix="/content-categories", tags=["İçerik Filtreleri"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["AI Asistan"])
api_v1_router.include_router(services.router, prefix="/services", tags=["Servis Engelleme"])
api_v1_router.include_router(system_logs.router, prefix="/system-logs", tags=["Sistem Logları"])
api_v1_router.include_router(system_time.router, prefix="/system-time", tags=["Saat ve Tarih"])
api_v1_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram Bot"])
api_v1_router.include_router(system_monitor.router, prefix="/system-monitor", tags=["Sistem Monitörü"])
api_v1_router.include_router(device_custom_rules.router, prefix="/device-rules", tags=["Cihaz Özel Kuralları"])
api_v1_router.include_router(ai_settings.router, prefix="/ai-settings", tags=["Yapay Zeka Ayarları"])
api_v1_router.include_router(ddos.router, prefix="/ddos", tags=["DDoS Koruma"])
api_v1_router.include_router(system_management.router, prefix="/system-management", tags=["Sistem Yönetimi"])
api_v1_router.include_router(wifi.router, prefix="/wifi", tags=["WiFi AP"])
api_v1_router.include_router(security_settings.router, prefix="/security", tags=["Güvenlik Ayarları"])
api_v1_router.include_router(ip_reputation.router, prefix="/ip-reputation", tags=["IP İtibar"])
api_v1_router.include_router(push.router, prefix="/push", tags=["Push Bildirimler"])
api_v1_router.include_router(ws.router, tags=["WebSocket"])
