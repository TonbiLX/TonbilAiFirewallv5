# Execution Guide — Android App Complete Overhaul

## Seans Basinda Yapilacaklar

Her yeni seansta bu dosyayi oku ve kaldigin yerden devam et.

## Calisma Sirasi

### ADIM 1: ApiRoutes.kt Guncelleme ✅/❌
Tum eksik endpoint'leri ekle (~116 yeni endpoint). Dosya: `android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt`

Eklenecek gruplar:
- Auth: AUTH_CHECK, AUTH_SETUP, AUTH_PROFILE, AUTH_CHANGE_PASSWORD
- Devices: DEVICES_SCAN, deviceBandwidth(id)
- DNS: DNS_LOOKUP, DNS_EXTERNAL_SUMMARY, blocklistRefresh(id), BLOCKLISTS_REFRESH_ALL
- DHCP: dhcpLeaseDelete(mac), dhcpLeases
- Firewall: FIREWALL_SCAN, FIREWALL_CONNECTIONS
- VPN Client: VPN_CLIENT_SERVERS, VPN_CLIENT_STATUS, VPN_CLIENT_STATS, vpnClientServer*(id), vpnClientImport, vpnClientActivate(id), vpnClientDeactivate(id)
- DDoS: DDOS_CONFIG, DDOS_APPLY, ddosToggle(name), DDOS_FLUSH_ATTACKERS, DDOS_ATTACK_MAP
- Content Categories: (zaten var, sadece CRUD fonksiyonlari ekle)
- Services: SERVICES, SERVICES_GROUPS, deviceServices(id), deviceServiceToggle(id), deviceServiceBulk(id)
- Device Rules: DEVICE_RULES, deviceRuleCreate(id), deviceRuleDetail(id)
- IP Management: IP_MGMT_STATS, IP_MGMT_TRUSTED, IP_MGMT_BLOCKED, IP_MGMT_UNBLOCK, ipMgmtTrustedDelete(id), IP_MGMT_BULK_UNBLOCK, IP_MGMT_BULK_DURATION, IP_MGMT_DURATION
- IP Reputation: IP_REP_CONFIG, IP_REP_SUMMARY, IP_REP_IPS, IP_REP_CACHE, IP_REP_TEST, IP_REP_BLACKLIST, IP_REP_BLACKLIST_FETCH, IP_REP_BLACKLIST_CONFIG
- Security: SECURITY_DEFAULTS (zaten config/reload/reset var)
- System Monitor: SYSTEM_INFO, SYSTEM_FAN
- System Management: SYSTEM_OVERVIEW, SYSTEM_REBOOT, SYSTEM_SHUTDOWN, SYSTEM_BOOT_INFO, SYSTEM_SAFE_MODE, SYSTEM_JOURNAL, systemServiceAction(name, action)
- System Time: SYSTEM_TIME_STATUS, SYSTEM_TIME_TIMEZONES, SYSTEM_TIME_NTP_SERVERS, SYSTEM_TIME_SET_TZ, SYSTEM_TIME_SET_NTP, SYSTEM_TIME_SYNC
- TLS: TLS_CONFIG, TLS_VALIDATE, TLS_UPLOAD, TLS_LETSENCRYPT, TLS_TOGGLE
- AI Settings: AI_CONFIG, AI_TEST, AI_PROVIDERS, AI_STATS, AI_RESET_COUNTER
- System Logs: SYSTEM_LOGS, SYSTEM_LOGS_SUMMARY
- Insights: insightDismiss(id), INSIGHTS_THREAT_STATS, INSIGHTS_BLOCKED_IPS, INSIGHTS_BLOCK_IP, INSIGHTS_UNBLOCK_IP
- Traffic: TRAFFIC_PER_DEVICE, TRAFFIC_LARGE_TRANSFERS, TRAFFIC_HISTORY, deviceTrafficHistory(id), deviceTrafficConnections(id), deviceTopDestinations(id)
- Telegram: (zaten var)
- WiFi: WIFI_CHANNELS, WIFI_GUEST, WIFI_SCHEDULE, WIFI_MAC_FILTER
- Chat: CHAT_HISTORY_DELETE
- Push: PUSH_REGISTER, PUSH_CHANNELS, PUSH_CHANNEL_TOGGLE

### ADIM 2: Yeni DTO Dosyalari ✅/❌
Her yeni ekran icin DTO dosyasi olustur:
- `dto/VpnClientDtos.kt` — VpnClientServerDto, VpnClientStatsDto, VpnClientStatusDto, VpnClientCreateDto, VpnClientImportDto
- `dto/ContentCategoryDtos.kt` — ContentCategoryDto, ContentCategoryCreateDto, ContentCategoryUpdateDto
- `dto/DeviceServiceDtos.kt` — ServiceDto, ServiceGroupDto, DeviceServiceDto, ServiceToggleDto
- `dto/IpManagementDtos.kt` — IpMgmtStatsDto, TrustedIpDto, BlockedIpDto, TrustedIpCreateDto, BlockedIpCreateDto
- `dto/IpReputationDtos.kt` — IpRepConfigDto, IpRepSummaryDto, IpRepCheckDto, IpRepBlacklistDto, IpRepBlacklistConfigDto
- `dto/SystemDtos.kt` — SystemInfoDto, FanConfigDto, SystemOverviewFullDto, JournalDto, BootInfoDto
- `dto/SystemTimeDtos.kt` — TimeStatusDto, TimezoneDto, NtpServerDto
- `dto/TlsDtos.kt` — TlsConfigDto, TlsValidateDto
- `dto/AiSettingsDtos.kt` — AiConfigDto, AiProviderDto, AiStatsDto
- `dto/SystemLogsDtos.kt` — SystemLogDto, SystemLogSummaryDto
- `dto/InsightsDtos.kt` — (AiInsightDto zaten var, genislet: dismiss, threat-stats, blocked-ips)
- `dto/DdosFullDtos.kt` — DdosConfigDto (full), DdosAttackMapDto
- `dto/PushDtos.kt` — PushTokenDto, PushChannelDto

### ADIM 3: Repository Genisletme ✅/❌
Yeni repository'ler:
- `VpnClientRepository.kt`
- `ContentCategoryRepository.kt`
- `DeviceServiceRepository.kt`
- `IpManagementRepository.kt`
- `IpReputationRepository.kt`
- `SystemRepository.kt` (monitor + management + time + logs birlesik)
- `TlsRepository.kt`
- `AiSettingsRepository.kt`
- `InsightsRepository.kt`

Mevcut genisletmeler:
- `SecurityRepository.kt` — DDoS config CRUD, security settings full, firewall scan, firewall connections
- `DeviceRepository.kt` — scan, bandwidth patch
- `DashboardRepository.kt` — per-device traffic

### ADIM 4: NavRoutes.kt Guncelleme ✅/❌
~20 yeni rota ekle

### ADIM 5: AppNavHost.kt Guncelleme ✅/❌
Tum yeni composable destination'lari ekle

### ADIM 6: BottomNavBar.kt Guncelleme ✅/❌
4 tab → 5 tab: Panel, Cihaz, Ag, Guvenlik, Ayarlar
VEYA: Drawer navigation ile 10+ bolum

### ADIM 7: Yeni Ekranlar (paralel ajanlarla) ✅/❌
Her ekran = ViewModel + Screen composable
Toplam ~15 yeni ekran

### ADIM 8: Mevcut Ekran Duzeltmeleri ✅/❌
10 mevcut ozellik tamamlama

### ADIM 9: AppModule.kt DI Guncelleme ✅/❌
Tum yeni repository + ViewModel kayitlari

### ADIM 10: Build + Test ✅/❌
gradlew assembleDebug, hata duzeltme, APK

## Ilerleme Takibi

| Adim | Durum | Seans |
|------|-------|-------|
| 1. ApiRoutes | ✅ | 1 |
| 2. DTOs | ✅ | 1 |
| 3. Repos | ✅ | 1 |
| 4. NavRoutes | ✅ | 1 |
| 5. AppNavHost | ✅ (placeholder) | 1 |
| 6. BottomNav | ✅ | 1 |
| 7. Yeni Ekranlar | 🔄 ajanlar calisiyor | 1 |
| 8. Mevcut Fixes | ❌ | - |
| 9. DI Module | ✅ | 1 |
| 10. Build | ❌ | - |

## Notlar
- Pi'ye baglanma — tum dosyalar lokal guncel
- Her adim sonrasi git commit yap
- Paralel ajanlar kullan (sonnet 4.6)
- Push Notification sayfasi MUTLAKA eklenecek
