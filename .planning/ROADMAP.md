# Roadmap: TonbilAiOS

## Milestones

- ✅ **v1.0 Bridge Isolation** - Phases 1-5 (shipped 2026-03-03)
- 🚧 **v2.0 TonbilAiOS Android App** - Phases 6-15 (in progress)

## Phases

<details>
<summary>✅ v1.0 Bridge Isolation (Phases 1-5) - SHIPPED 2026-03-03</summary>

- [x] **Phase 1: Bridge Isolation Core** - HAL functions for L2 isolation, NAT MASQUERADE, rollback
- [x] **Phase 2: Accounting Chain Migration** - Rewrite bridge accounting from forward hook to input/output hooks
- [x] **Phase 3: TC Mark Chain Migration** - Rewrite TC mark chains from forward hook to input/output hooks
- [x] **Phase 4: Startup and Persistence** - Lifespan swap, sysctl persistence, module persistence
- [x] **Phase 5: DHCP Gateway and Validation** - Gateway change from .1 to .2 and transition validation

</details>

### 🚧 v2.0 TonbilAiOS Android App

**Milestone Goal:** Samsung S24 Ultra icin Kotlin Native Android uygulamasi — TonbilAiOS v5'in tum ozelliklerini mobil platformdan yonetme ve izleme

**Phase Numbering:**
- Integer phases (6, 7, 8...): Planned milestone work
- Decimal phases (7.1, 7.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 6: Project Skeleton** - Gelistirme ortami, proje iskeleti, tema, navigasyon, API client
- [ ] **Phase 7: Authentication** - JWT giris, biyometrik auth, token yonetimi, auto-discovery
- [x] **Phase 8: Dashboard** - Ana dashboard ekrani, WebSocket canli veri, grafikler (completed 2026-03-06)
- [ ] **Phase 9: Device Management** - Cihaz listesi, detay, engelleme, profil atama
- [x] **Phase 10: DNS Filtering** - DNS ozet, filtreleme toggle, kategoriler, profil yonetimi, guvenlik katmanlari (completed 2026-03-13)
- [ ] **Phase 11: Network Security** - Firewall kurallari, VPN peer yonetimi, DDoS koruma izleme
- [ ] **Phase 12: Traffic Monitoring** - Canli akislar, buyuk transferler, gecmis, grafikler
- [ ] **Phase 13: Communication & Config** - Push notifications, AI Chat, Telegram, WiFi AP, DHCP, Guvenlik ayarlari
- [ ] **Phase 14: Android Enhancements** - Home widget, Quick Settings tile, haptic feedback, app shortcuts
- [ ] **Phase 15: Release Build** - Imzali APK build ve S24 Ultra'ya yukleme

## Phase Details

<details>
<summary>✅ v1.0 Bridge Isolation (Phases 1-5) - SHIPPED 2026-03-03</summary>

### Phase 1: Bridge Isolation Core
**Goal**: HAL contains tested functions to apply and safely reverse bridge isolation
**Plans**: 1/1 Complete

### Phase 2: Accounting Chain Migration
**Goal**: Bridge bandwidth counters correctly accumulate on input/output hooks
**Plans**: 1/1 Complete

### Phase 3: TC Mark Chain Migration
**Goal**: Per-device bandwidth limits remain enforced after isolation
**Plans**: 1/1 Complete

### Phase 4: Startup and Persistence
**Goal**: Router mode configuration survives reboots
**Plans**: 1/1 Complete

### Phase 5: DHCP Gateway and Validation
**Goal**: All LAN devices use Pi as default gateway, end-to-end verified
**Plans**: 2/2 Complete

</details>

### Phase 6: Project Skeleton
**Goal**: Gelistirme ortami hazir, bos Compose uygulamasi cihazda baslatilabiliyor, cyberpunk tema uygulanmis, navigasyon calisiyor, API client backend'e baglanabiliyor
**Depends on**: Nothing (first phase of v2.0 milestone)
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05
**Success Criteria** (what must be TRUE):
  1. Komut satirindan `./gradlew assembleDebug` basarili APK uretiyor ve S24 Ultra'da aciliyor
  2. Uygulama acildiginda cyberpunk koyu tema gorунuyor (neon cyan/magenta vurgu renkleri, koyu arka plan)
  3. Bottom navigation ile en az 4 ana ekran arasinda gecis yapilabiliyor
  4. API client wall.tonbilx.com adresine test istegi gonderebiliyor ve JSON yanit aliyor
**Plans:** 2 plans
Plans:
- [ ] 06-01-PLAN.md — Gradle proje yapisi, version catalog, cyberpunk tema, Koin DI
- [ ] 06-02-PLAN.md — Bottom navigation, placeholder ekranlar, Ktor API client

### Phase 7: Authentication
**Goal**: Kullanici guvenli bir sekilde hesabina erisebiliyor — sifre, biyometrik veya otomatik token ile
**Depends on**: Phase 6
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. Kullanici email/sifre ile giris yapabiliyor ve korunmus ekranlara erisebiliyor
  2. Giris sonrasi parmak izi veya yuz tanima ile sonraki girislerde hizli erisim saglaniyor
  3. Uygulama kapatilip acildiginda token gecerli ise tekrar giris istenmiyor
  4. Yerel agda (192.168.1.2) ve disaridan (wall.tonbilx.com) otomatik gecis yapiliyor, baglanti kopuklugunda diger adres deneniyor
  5. Sunucu ayarlari ekranindan manuel URL girilip baglanti testi yapilabiliyor
**Plans:** 1/2 plans executed
Plans:
- [ ] 07-01-PLAN.md — Token depolama, server discovery, auth interceptor, AuthRepository
- [ ] 07-02-PLAN.md — Login ekrani, biyometrik auth, sunucu ayarlari, navigation guard

### Phase 8: Dashboard
**Goal**: Kullanici tek bakista ag durumunu gorebiliyor — canli bant genisligi, cihaz sayisi, DNS ozet, tehdit bilgisi
**Depends on**: Phase 7
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. Dashboard ekraninda baglanti durumu, toplam trafik, engellenen sorgu sayisi ve aktif cihaz sayisi gorunuyor
  2. Bant genisligi grafigi canli olarak guncelleniyor (WebSocket uzerinden veri akisi)
  3. Uygulama arka plana gidip geri geldiginde WebSocket baglantisi otomatik yeniden kuruluyor
  4. Istatistik kartlarina dokunulunca ilgili detay ekranina yonlendirme yapiliyor
**Plans:** 2/2 plans complete
Plans:
- [ ] 08-01-PLAN.md — Veri katmani: Dashboard/WebSocket DTOlari, WebSocketManager, DashboardRepository, Vico bagimliligi
- [ ] 08-02-PLAN.md — UI katmani: DashboardScreen, istatistik kartlari, Vico bandwidth grafigi, kart navigasyonu

### Phase 9: Device Management
**Goal**: Kullanici tum ag cihazlarini gorebiliyor, yonetebiliyor ve tek dokunusla internet erisimlerini kontrol edebiliyor
**Depends on**: Phase 8
**Requirements**: DEV-01, DEV-02, DEV-03, DEV-04, DEV-05
**Success Criteria** (what must be TRUE):
  1. Cihaz listesinde her cihazin ismi, IP'si, durumu ve anlik bant genisligi gorunuyor
  2. Cihaz detay ekraninda trafik gecmisi, DNS sorgulari ve profil bilgisi goruntulenebiliyor
  3. Tek dokunusla bir cihazin interneti durduruluyor/geri aciliyor ve durum aninda guncelleniyor
  4. Cihaza profil atanabiliyor/degistirilebiliyor
  5. Tum cihaz ekranlarinda asagiya cekerek yenileme (pull-to-refresh) calisiyor
**Plans:** 2 plans
Plans:
- [ ] 09-01-PLAN.md — Veri katmani: Device/Profile DTO'lari, DeviceRepository, ProfileRepository, Koin DI
- [ ] 09-02-PLAN.md — UI katmani: DevicesScreen (liste + block toggle + WS bandwidth), DeviceDetailScreen (3 tab + profil atama), AppNavHost wiring

### Phase 10: DNS Filtering
**Goal**: Kullanici DNS filtreleme sistemini mobil uzerinden gorebiliyor ve yonetebiliyor — kategoriler, profiller, hizli toggle, DNS guvenlik katmanlari (DNSSEC, Tunneling, DoH, DGA)
**Depends on**: Phase 9
**Requirements**: DNS-01, DNS-02, DNS-03, DNS-04
**Success Criteria** (what must be TRUE):
  1. DNS ozet ekraninda toplam sorgu, engelleme sayisi, en cok sorgulanan ve engellenen domainler listeleniyor
  2. Tek dokunusla DNS filtreleme acilip kapatilabiliyor
  3. Icerik kategorileri goruntulenebiliyor ve blocklist baglama yonetimi yapilabiliyor
  4. Profil olusturulabiliyor/duzenlenebiliyor — kategori secimi ve bandwidth limiti ayarlanabiliyor
**Plans:** 2/2 plans complete
Plans:
- [ ] 10-01-PLAN.md — Veri katmani: DTO guncellemeleri (DNS guvenlik katmanlari, source type), DnsFilteringViewModel, ProfilesViewModel genisletmesi
- [ ] 10-02-PLAN.md — UI katmani: DnsFilteringScreen (4-tab hub: Ozet, Kategoriler, Profiller, Guvenlik), ProfilesScreen content_filters, navigasyon wiring

### Phase 11: Network Security
**Goal**: Kullanici firewall kurallarini, VPN peer'larini ve DDoS koruma durumunu mobil uzerinden yonetebiliyor
**Depends on**: Phase 8
**Requirements**: FW-01, FW-02, FW-03, VPN-01, VPN-02, VPN-03, VPN-04, DDOS-01, DDOS-02, DDOS-03
**Success Criteria** (what must be TRUE):
  1. Firewall kural listesi goruntulenebiliyor, yeni kural eklenebiliyor/duzenlenebiliyor/silinebiliyor ve oncelik siralamasi degistirilebiliyor
  2. VPN peer listesi goruntulenebiliyor, yeni peer eklenebiliyor/silinebiliyor ve peer QR kodu goruntulenip paylasılabiliyor
  3. VPN durumu (aktif/pasif) goruntulenebiliyor
  4. DDoS koruma durumu, basitlestirilmis saldiri haritasi ve canli saldiri akisi goruntulenebiliyor
**Plans**: TBD

### Phase 12: Traffic Monitoring
**Goal**: Kullanici ag trafigini detayli izleyebiliyor — canli akislar, buyuk transferler, gecmis ve per-device grafikler
**Depends on**: Phase 8
**Requirements**: TRAF-01, TRAF-02, TRAF-03, TRAF-04
**Success Criteria** (what must be TRUE):
  1. Canli akislar ekraninda per-flow baglanti listesi 5 saniyede bir otomatik yenileniyor
  2. Buyuk transferler listesinde >1MB flow'lar ayri goruntulenebiliyor
  3. Trafik gecmisi ekraninda sayfalama ile eski kayitlar goruntulenebiliyor
  4. Per-device bant genisligi zaman serisi grafigi goruntulenebiliyor
**Plans**: TBD

### Phase 13: Communication & Config
**Goal**: Push bildirimler calisiyor, AI sohbet mobilde kullanilabiliyor, Telegram/WiFi/DHCP/Guvenlik ayarlari yonetilebiliyor
**Depends on**: Phase 7
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, CHAT-01, CHAT-02, CHAT-03, TELE-01, TELE-02, WIFI-01, WIFI-02, WIFI-03, DHCP-01, DHCP-02, SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. Yeni cihaz baglantisi veya DDoS alarmi geldiginde telefona push bildirim geliyor ve bildirim kanallari (Guvenlik, Cihaz, Trafik, Sistem) ayri ayri acilip kapatilabiliyor
  2. AI sohbet ekraninda mesaj gonderilip yanitlar goruntulenebiliyor (gecmis + yapilandirilmis format)
  3. Telegram bot token/chat ID yapilandirilabiliyor ve bildirim ayarlari degistirilebiliyor
  4. WiFi AP durumu gorulup SSID/sifre/kanal degistirilebiliyor ve AP acilip kapatilabiliyor
  5. DHCP havuz bilgileri ve statik IP atamalari goruntulenip yonetilebiliyor, guvenlik esik degerleri ayarlanip kaydedilebiliyor
**Plans**: TBD

### Phase 14: Android Enhancements
**Goal**: Uygulama native Android ozelliklerini kullaniyor — ana ekran widget'i, Quick Settings, dokunsal geri bildirim, hizli erisim
**Depends on**: Phase 8, Phase 13
**Requirements**: DASH-05, DASH-06, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Ana ekrana eklenen Glance widget'inda bant genisligi, cihaz sayisi ve son tehdit bilgisi gorunuyor
  2. Quick Settings panelinde DNS filtreleme toggle ve cihaz engelleme toggle tile'lari calisiyor
  3. Kritik uyarilarda (DDoS, engellenen cihaz) telefon titriyor
  4. Uygulama ikonuna uzun basinca durum kontrol, cihaz engelle ve AI chat kisayollari gorunuyor
**Plans**: TBD

### Phase 15: Release Build
**Goal**: Imzali APK uretilip S24 Ultra'ya basariyla yuklenmis — uygulama production-ready
**Depends on**: Phase 6-14 (tum ozellikler tamamlanmis olmali)
**Requirements**: UX-03
**Success Criteria** (what must be TRUE):
  1. Imzali release APK uretilmis ve S24 Ultra'ya sideload ile basariyla yuklenmis
  2. Uygulama ilk acilista giris ekranini gosteriyor, giris sonrasi tum ekranlar erisilebilir
  3. Arka planda push bildirimler calisiyor, uygulama kapatilsa bile bildirim geliyor
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15
(Phase 11 and 12 can run in parallel after Phase 8)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Bridge Isolation Core | v1.0 | 1/1 | Complete | 2026-02-25 |
| 2. Accounting Chain Migration | v1.0 | 1/1 | Complete | 2026-02-25 |
| 3. TC Mark Chain Migration | v1.0 | 1/1 | Complete | 2026-02-25 |
| 4. Startup and Persistence | v1.0 | 1/1 | Complete | 2026-03-03 |
| 5. DHCP Gateway and Validation | v1.0 | 2/2 | Complete | 2026-03-03 |
| 6. Project Skeleton | v2.0 | 0/2 | Planning | - |
| 7. Authentication | 1/2 | In Progress|  | - |
| 8. Dashboard | 2/2 | Complete   | 2026-03-06 | - |
| 9. Device Management | v2.0 | 0/2 | Planning | - |
| 10. DNS Filtering | 2/2 | Complete    | 2026-03-13 | - |
| 11. Network Security | v2.0 | 0/? | Not started | - |
| 12. Traffic Monitoring | v2.0 | 0/? | Not started | - |
| 13. Communication & Config | v2.0 | 0/? | Not started | - |
| 14. Android Enhancements | v2.0 | 0/? | Not started | - |
| 15. Release Build | v2.0 | 0/? | Not started | - |
