# Phase 10: DNS Filtering - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** User directive + system state analysis

<domain>
## Phase Boundary

Android uygulamasinda DNS filtreleme sisteminin tam yonetimi:
- DNS ozet ekrani (istatistikler, top domain'ler)
- DNS filtreleme hizli toggle
- Icerik kategorileri goruntuleme ve blocklist baglama
- Profil olusturma/duzenleme (kategori secimi + bandwidth limiti)

**EK KAPSAM (kullanici talimati):** Son yapilan sistem guncellemelerini de yansit:
- DNSSEC dogrulama durumu ve enforce modu
- DNS Tunneling tespiti durumu
- DoH endpoint durumu
- DNS guvenlik katmanlari gorunurlugu (12 aktif katman)
- IP Reputation entegrasyonu (AbuseIPDB)
- Genel sistem kontrolu — app uzerinden tam yonetim

</domain>

<decisions>
## Implementation Decisions

### DNS Ozet Ekrani
- Toplam sorgu, engelleme sayisi, engelleme orani gosterilmeli
- En cok sorgulanan ve engellenen domain'ler listesi
- DNS guvenlik katmanlari durumu (DNSSEC, Tunneling, DoH, DGA)
- Kaynak tipi dagilimi (INTERNAL/EXTERNAL/DOT)

### DNS Filtreleme Toggle
- Tek dokunusla global DNS filtreleme ac/kapa
- SecuritySettings API uzerinden hot-reload (mevcut backend destekliyor)

### Icerik Kategorileri
- Kategori listesi (ikon, renk, domain sayisi)
- Blocklist baglama yonetimi (multi-select)
- Ozel domain ekleme (custom_domains textarea)

### Profil Yonetimi
- Profil CRUD (isim, ikon, bandwidth limiti)
- Kategori secimi (content_filters JSON array)
- Profil bazli domain sayisi gosterimi

### DNS Guvenlik Katmanlari (YENi — son guncellemeler)
- DNSSEC dogrulama durumu (enforce/log_only/disabled)
- DNS Tunneling dedektoru durumu (aktif/pasif, istatistikler)
- DoH endpoint durumu (guard.tonbilx.com)
- DGA tespiti durumu
- Rate limiting ayarlari
- Engelli sorgu tipleri (ANY, AXFR, vb.)
- Sinkhole IP

### Claude's Discretion
- Ekran tab yapisi (DNS Ozet / Kategoriler / Profiller / Guvenlik)
- DTO yapisi ve Kotlin data class'lari
- Repository pattern organizasyonu
- ViewModel state management detaylari
- Pull-to-refresh davranisi

</decisions>

<specifics>
## Specific Ideas

### Mevcut Backend Endpoint'ler
- GET /api/v1/dns/stats — DNS istatistikleri
- GET /api/v1/dns/top-domains — En cok sorgulanan
- GET /api/v1/dns/top-blocked — En cok engellenen
- GET /api/v1/dns/queries — Sorgu listesi
- GET /api/v1/content-categories — Kategori listesi
- POST/PUT/DELETE /api/v1/content-categories — Kategori CRUD
- GET /api/v1/profiles — Profil listesi
- POST/PUT/DELETE /api/v1/profiles — Profil CRUD
- GET /api/v1/security-settings — Guvenlik ayarlari
- PUT /api/v1/security-settings — Guvenlik ayarlari guncelleme

### Son Sistem Guncellemeleri (2026-03-08 — 2026-03-13)
- DNSSEC enforce modu aktif (log_only'den gecis yapildi)
- DNS Tunneling dedektoru calisiyor
- DoH endpoint (guard.tonbilx.com) NPM uzerinden aktif
- IP Reputation sistemi: AbuseIPDB entegrasyonu, lokal blocklist, hibrit skor
- DB optimize: connection_flows + dns_query_logs fragmentasyon temizligi
- Flow tracker: INSERT ON DUPLICATE KEY UPDATE ile concurrent fix
- 12 aktif DNS guvenlik katmani
- 980K+ blocklist domain

### Web Frontend Referanslari
- DnsBlockingPage.tsx — DNS engelleme sayfasi
- ContentCategoriesPage.tsx — Icerik kategorileri
- ProfilesPage.tsx — Profil yonetimi
- SecuritySettingsPage.tsx — Guvenlik ayarlari (5-tab)

</specifics>

<deferred>
## Deferred Ideas

- DNS sorgu gecmisi detayli filtreleme (zaman araliqi, cihaz bazli) — Phase 12 ile birlikte
- DNS analytics grafikleri (saatlik trend) — AI Insights sayfasiyla birlikte

</deferred>

---

*Phase: 10-dns-filtering*
*Context gathered: 2026-03-13 via user directive*
