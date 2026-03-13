# Phase 12: Traffic Monitoring - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** Roadmap requirements + codebase analysis

<domain>
## Phase Boundary

Android uygulamasinda trafik izleme — 4 alan:
1. **Canli akislar** — per-flow baglanti listesi, 5s auto-refresh
2. **Buyuk transferler** — >1MB flow'lar ayri liste
3. **Trafik gecmisi** — sayfalama ile eski kayitlar
4. **Per-device grafik** — bant genisligi zaman serisi (Vico chart)

DeviceDetailScreen'de zaten canli trafik akisi VAR (Quick 26'da eklendi).
Bu phase ayri TrafficScreen olusturacak ve per-device grafikler ekleyecek.

</domain>

<decisions>
## Implementation Decisions

### Canli Akislar Tab
- Backend: GET /api/v1/traffic/flows/live
- 5s auto-refresh (LaunchedEffect + delay)
- Yon oklari, uygulama badge, durum renklendirme (web ile tutarli)

### Buyuk Transferler Tab
- Backend: GET /api/v1/traffic/flows/large-transfers
- >10MB neon-magenta vurgulama
- 3s auto-refresh

### Trafik Gecmisi Tab
- Backend: GET /api/v1/traffic/flows/history?page=X&per_page=Y
- Sayfalama (LazyColumn + loadMore)
- Domain arama filtresi

### Per-Device Grafik
- Backend: GET /api/v1/traffic/flows/device/{id}/summary
- Vico CartesianChart (mevcut dashboard'da zaten kullaniliyor)
- DeviceDetailScreen'e entegre

### Claude's Discretion
- Tab yapisi (3-tab: Canli/Buyuk/Gecmis)
- DTO ve Repository organizasyonu
- Auto-refresh mekanizmasi detaylari

</decisions>

<specifics>
## Specific Ideas

### Mevcut Android Kod
- DeviceDetailScreen: canli trafik akisi listesi zaten var (Quick 26)
- TrafficRepository: henuz yok, olusturulacak
- TrafficDtos: henuz yok, olusturulacak
- Vico chart: DashboardScreen'de zaten kullaniliyor (ModelProducer pattern)

### Backend Endpoint'ler (CLAUDE.md'den)
- GET /api/v1/traffic/flows/live — canli akislar
- GET /api/v1/traffic/flows/large-transfers — buyuk transferler
- GET /api/v1/traffic/flows/history — gecmis (sayfalama)
- GET /api/v1/traffic/flows/device/{id}/summary — per-device ozet
- GET /api/v1/traffic/flows/stats — genel istatistikler

</specifics>

<deferred>
## Deferred Ideas

- Floating overlay / PiP modu (ADV-01) — v2 requirement
- Domain bazli trafik analizi grafikleri — AI Insights ile birlikte

</deferred>

---

*Phase: 12-traffic-monitoring*
*Context gathered: 2026-03-13 via roadmap analysis*
