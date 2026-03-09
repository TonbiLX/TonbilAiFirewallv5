# Android App vs Web Panel — Gap Analizi

## Tarih: 2026-03-10

## Mevcut Android App Durumu
- **51 Kotlin dosyasi**, ~10,000 satir kod
- **6 ekran:** Splash, Login, Dashboard, Devices+Detail, Security(6 tab), Settings(6 tab)
- **~44 API endpoint** kullaniliyor
- **Son APK:** 68 MB (7 Mart 2026)

## Web Panel: 27 Sayfa, ~160 Endpoint

---

## TAMAMEN EKSIK EKRANLAR (15 adet)

### 1. VPN Client (/vpn-client)
- Dis VPN sunucu CRUD (manuel + .conf import)
- Baglan/kes toggle
- Istatistikler
- **Endpoint'ler:** GET/POST/PATCH/DELETE vpn-client/servers, activate/deactivate, stats, status

### 2. Content Categories (/content-categories)
- Kategori CRUD (key, isim, ikon, renk, blocklist baglama, ozel domainler)
- Enabled toggle
- **Endpoint'ler:** GET/POST/PATCH/DELETE content-categories/

### 3. Device Services (/devices/:id/services)
- Per-device servis engelleme grid (YouTube, Netflix, WhatsApp vb.)
- Grup filtreleri (Yayin, Oyun, Mesajlasma, Sosyal vb.)
- Per-servis toggle
- **Endpoint'ler:** GET services/, services/groups, services/devices/{id}, PUT toggle, PUT bulk

### 4. IP Management (/ip-management)
- Tab 1: Guvenilir IP CRUD
- Tab 2: Engellenen IP listesi + toplu islemler (bulk unblock, bulk duration)
- **Endpoint'ler:** GET/POST/DELETE trusted, GET/POST blocked, POST unblock, PUT duration, PUT bulk-*

### 5. IP Reputation (/ip-reputation — FirewallPage tab)
- AbuseIPDB config (API key, min skor)
- Sorgulanan IP listesi
- Blacklist yonetimi
- Cache temizle
- **Endpoint'ler:** GET/PUT config, GET summary, GET ips, DELETE cache, POST test, GET/POST blacklist

### 6. Security Settings (/security — tam 5 tab)
- Tab 1: Tehdit analizi (esik degerleri, DGA, subnet flood, scan pattern)
- Tab 2: DNS guvenlik (rate limit, engellenen query types, sinkhole)
- Tab 3: Uyari ayarlari (DDoS esikleri, soguma)
- Tab 4: Guvenilir IP'ler (IP CRUD)
- Tab 5: Canli istatistikler
- **Endpoint'ler:** GET/PUT security/config, POST reset, GET defaults, GET stats, trusted IP CRUD

### 7. System Monitor (/system-monitor)
- Donanim bilgisi, CPU/RAM/Disk/Fan/Ag detayli metrikler
- 5dk rolling grafikler (CPU, sicaklik, ag)
- Fan kontrol (auto/manual, PWM slider)
- **Endpoint'ler:** GET info, GET metrics, GET/PUT fan

### 8. System Management (/system-management)
- Servis listesi + baslat/durdur/yeniden baslat
- Sistem reboot/shutdown (3s onay)
- Safe mode reset
- Journal viewer
- **Endpoint'ler:** GET overview, GET services, POST services/{name}/restart|start|stop, POST reboot/shutdown, GET journal

### 9. System Time (/system-time)
- Canli saat, timezone degistir, NTP sunucu ayarla, anlik sync
- **Endpoint'ler:** GET status, GET timezones, GET ntp-servers, POST set-timezone, POST set-ntp-server, POST sync-now

### 10. TLS/DoT (/tls)
- DNS sifreleme toggle, sertifika yonetimi (PEM yapistir/yukle/Let's Encrypt)
- Sertifika dogrulama
- **Endpoint'ler:** GET/PATCH tls/config, POST validate, POST upload-cert, POST letsencrypt, POST toggle

### 11. AI Settings (/ai-settings)
- Provider secimi (OpenAI/Anthropic/Ollama/Custom), API key, model
- Chat modu, sicaklik, maks token, gunluk limit
- Log analizi config
- Kullanim istatistikleri
- **Endpoint'ler:** GET/PUT config, POST test, GET providers, GET stats, POST reset-counter

### 12. System Logs (/system-logs)
- Filtreli log listesi (tarih, IP, domain, aksiyon, onem, kategori)
- Tam sayfalama
- Ozet istatistikler
- **Endpoint'ler:** GET system-logs/, GET summary

### 13. Insights (/insights)
- AI icgoru feed'i (severity badge, aksiyon butonlari)
- Engellenen IP'ler paneli
- IP engelle/kaldir/gormezden gel butonlari
- **Endpoint'ler:** GET insights, POST dismiss, GET threat-stats, GET blocked-ips, POST block-ip, POST unblock-ip

### 14. DDoS Map (/ddos-map)
- Basitlestirilmis saldiri haritasi (mobil icin)
- Canli saldiri akisi
- **Endpoint'ler:** GET ddos/attack-map, GET counters, GET status

### 15. Push Notifications (YENi — web'de yok)
- FCM token yonetimi
- Bildirim kanallari (Guvenlik, Cihaz, Trafik, Sistem) toggle
- Bildirim gecmisi
- **Backend:** Yeni endpoint'ler gerekli (FCM token kayit, kanal tercihleri)

### 16. User Settings
- Sifre degistir, profil guncelle
- **Endpoint'ler:** PUT auth/profile, POST auth/change-password

---

## YARIM KALAN OZELLIKLER (10 adet)

### 1. DNS (SecurityScreen DNS tab)
**Eksik:** Sorgu loglari tab, domain lookup, blocklist refresh (tekli+toplu), external summary, blocklist edit
**Eklenmesi gereken endpoint'ler:** dns/queries, dns/lookup/{domain}, dns/queries/external-summary, blocklists/{id}/refresh, blocklists/refresh-all, PATCH blocklists/{id}

### 2. Firewall (SecurityScreen Firewall tab)
**Eksik:** Kural duzenleme (edit dialog), port taramasi
**Eklenmesi gereken:** Edit dialog + PATCH firewall/rules/{id} cagrisi, GET firewall/scan

### 3. DDoS (SecurityScreen DDoS tab)
**Eksik:** Toggle aksiyonlari (UI var, backend baglantisi yok), config guncelleme, saldirganlari temizle
**Eklenmesi gereken:** GET/PUT ddos/config, POST ddos/toggle/{name}, POST ddos/apply, POST ddos/flush-attackers

### 4. DHCP (SettingsScreen DHCP tab)
**Eksik:** Pool CRUD (olustur/duzenle/sil/toggle), dinamik kira silme
**Eklenmesi gereken:** POST/PATCH/DELETE dhcp/pools, POST dhcp/pools/{id}/toggle, DELETE dhcp/leases/{mac}

### 5. WiFi (SettingsScreen WiFi tab)
**Eksik:** Misafir ag, zamanlama, MAC filtre tablari, kanal listesi
**Eklenmesi gereken:** PUT wifi/guest, PUT wifi/schedule, PUT wifi/mac-filter, GET wifi/channels

### 6. Profiles (SettingsScreen Profil tab)
**Eksik:** Profil duzenleme dialog, allowed_hours UI, dinamik kategori secimi (domain sayilari ile)
**Eklenmesi gereken:** Kategori listesi icin content-categories/, profil PATCH zaten var

### 7. Traffic (SecurityScreen Trafik tab)
**Eksik:** Buyuk transferler tab, gecmis tab (sayfalama+filtre), protokol/yon/durum filtreleri
**Eklenmesi gereken:** GET traffic/flows/large-transfers, GET traffic/flows/history

### 8. Devices
**Eksik:** Arama (hostname/IP/MAC), "Cihaz Tara" butonu, IPTV toggle, inline hostname/bandwidth edit, risk badge
**Eklenmesi gereken:** POST devices/scan, PATCH devices/{id}/bandwidth

### 9. Chat (SettingsScreen Sohbet tab)
**Eksik:** Gecmis temizle, markdown render, action result gosterimi, ornek komut chip'leri
**Eklenmesi gereken:** DELETE chat/history

### 10. Dashboard
**Eksik:** Cihaz trafik widget'i (per-device 24s tablo)
**Eklenmesi gereken:** GET traffic/per-device

---

## ONCELIK SIRASI

1. **Kritik:** Altyapi (ApiRoutes, DTOs, Repos) — her sey buna bagimli
2. **Kritik:** Navigasyon yeniden yapilandirma — 20+ ekran icin yer acma
3. **Yuksek:** Mevcut ekran duzeltmeleri (DDoS toggle, Firewall edit, DNS logs vb.)
4. **Yuksek:** Yeni ekranlar (VPN Client, Services, IP Mgmt, Security Settings)
5. **Orta:** Sistem ekranlari (Monitor, Management, Time, Logs)
6. **Orta:** Ek ekranlar (TLS, AI Settings, Insights, DDoS Map)
7. **Ozel:** Push Notifications (FCM entegrasyonu)
8. **Son:** Build + test
