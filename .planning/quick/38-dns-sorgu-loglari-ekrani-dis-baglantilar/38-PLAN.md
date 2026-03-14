# Quick Task 38: DNS Sorgu Logları + Dış Bağlantılar Tespiti

## Hedef
1. Android'e DNS sorgu log ekranı ekle (DnsBlockingScreen'e yeni "Sorgular" tab'ı)
2. Hem Android hem web panele "Dış Bağlantılar" bölümü ekle (DoT/DoH bypass tespiti)

## Bağlam
- Backend `/api/v1/dns/queries` endpoint'i var (limit, offset, blocked_only, domain_search, device_id, source_type, client_ip filtreleri destekliyor)
- Mevcut DnsBlockingScreen 3 tab içeriyor: İstatistikler, Engelleme Listeleri, Kurallar
- Dış bağlantı tespiti için backend'de `/api/v1/traffic/flows/live` endpoint'i var (port/domain bilgisi mevcut)
- DoT = port 853, DoH = port 443 + bilinen DoH sunucularına bağlantı (8.8.8.8, 1.1.1.1, 9.9.9.9, 208.67.222.222, 94.140.14.14 vb.)
- DNS bypass = Pi'nin IP'si (192.168.1.2) yerine başka DNS sunucusu kullanan cihaz (port 53 dışarıya gidiyor)

## Görevler

### Görev 1: Android DNS Sorgu Log Ekranı
**Yapılacaklar:**
1. `DnsQueryLogDto` DTO'yu `SecurityDtos.kt`'ye ekle
2. `SecurityRepository.getDnsQueries()` metodunu ekle (limit, blockedOnly, domainSearch parametreleri)
3. `DnsBlockingViewModel`'e query log state + yükleme metodu ekle
4. `DnsBlockingScreen`'e 4. tab olarak "Sorgular" ekle — liste görünümü:
   - Domain adı (büyük font)
   - Cihaz IP'si + timestamp (küçük font)
   - Engellendi/İzin verildi badge (neon-red / neon-green)
   - source_type badge (INTERNAL/EXTERNAL/DOT)
   - Arama çubuğu + "Sadece engellenenler" toggle

**Dosyalar:**
- `android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/SecurityDtos.kt`
- `android/app/src/main/java/com/tonbil/aifirewall/data/repository/SecurityRepository.kt`
- `android/app/src/main/java/com/tonbil/aifirewall/feature/dnsblocking/DnsBlockingViewModel.kt`
- `android/app/src/main/java/com/tonbil/aifirewall/feature/dnsblocking/DnsBlockingScreen.kt`

### Görev 2: Backend Dış Bağlantılar Endpoint'i
**Yapılacaklar:**
Backend `devices.py` veya yeni `external_connections.py` dosyasına endpoint ekle:
`GET /api/v1/devices/external-dns-connections`

Bu endpoint:
- `connection_flows` tablosundan son 1 saatteki aktif flow'lara bak
- DoT: `dst_port == 853` olan cihazları bul
- DoH: `dst_port == 443` VE `dst_ip` bilinen DoH IP'lerinden biriyse
- DNS Bypass: `dst_port == 53` VE `dst_ip != 192.168.1.2` (Pi IP'si)
- Her cihaz için `device_id`, `device_ip`, `mac_address`, `hostname`, `os_type` bilgisi
- `detection_type`: "dot", "doh", "dns_bypass"
- `dst_ip`: hedef IP
- `last_seen`: son görülme zamanı

Bilinen DoH IP'leri: `8.8.8.8`, `8.8.4.4`, `1.1.1.1`, `1.0.0.1`, `9.9.9.9`, `149.112.112.112`, `208.67.222.222`, `208.67.220.220`, `94.140.14.14`, `94.140.15.15`

**Dosyalar:**
- `backend/app/api/v1/devices.py` (endpoint ekle)
- Pi'ye deploy: SSH ProxyJump + `sudo systemctl restart tonbilaios-backend`

### Görev 3: Android + Web "Dış Bağlantılar" Bölümü
**Android:**
- `ExternalDnsConnectionDto` DTO ekle
- `DeviceRepository.getExternalDnsConnections()` ekle
- `DevicesScreen.kt`'ye alt bölüm: "Dış Bağlantılar" collapsible card
  - DoT/DoH/Bypass kategorilerini badge'li göster
  - Cihaz adı + MAC + detection_type + hedef IP
  - 30 saniyede bir otomatik yenileme

**Web Panel:**
- `frontend/src/pages/DevicesPage.tsx`'e "Dış Bağlantılar" tab/bölüm ekle
- Veya mevcut `DnsBlockingPage.tsx`'e yeni tab
- Tablo: Cihaz | MAC | Tespit Türü | Hedef IP | Son Görülme
- Cyberpunk tema uyumlu (neon-red uyarı rengi)
- Build + deploy

## Commit Stratejisi
- Commit 1: `feat(38): add DNS query log DTO, repository, ViewModel state`
- Commit 2: `feat(38): add DNS query log tab to DnsBlockingScreen`
- Commit 3: `feat(38): add external-dns-connections backend endpoint + deploy`
- Commit 4: `feat(38): add external connections UI on Android + web panel`

## Başarı Kriterleri
- [ ] DnsBlockingScreen'de "Sorgular" tab'ı görünüyor, loglar listeleniyor
- [ ] Arama + engellendi filtresi çalışıyor
- [ ] `/api/v1/devices/external-dns-connections` endpoint'i sonuç döndürüyor
- [ ] Android DevicesScreen'de Dış Bağlantılar bölümü görünüyor
- [ ] Web panelde Dış Bağlantılar tablosu görünüyor
- [ ] Android build hatasız tamamlanıyor (`./gradlew assembleDebug`)
