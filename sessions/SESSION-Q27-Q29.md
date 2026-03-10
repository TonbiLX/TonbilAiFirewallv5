# Quick 27–29 Arsiv

## Quick 27 — DDoS World Map + Traffic/Log Bugfix ✅ (commit 84b2580)
- DTO fix'leri (InsightsDtos, DnsBlockingScreen)
- DDoS world map iyilestirmeleri
- Traffic, log, reputation bug duzeltmeleri

## Quick 28 — DDoS Harita Crash Fix ✅ (commit f5ce5e3)
- LazyColumn key crash — duplicate/empty IP key fix

## Quick 29 — Nav Fix + Sort Chips + Cihaz Yonetim Hazirlik ✅ (commit 3fb27a6)
### Bottom Nav Direkt Navigasyon
- `popUpTo<DashboardRoute>` — SplashRoute/LoginRoute sorununu cozdu
- `saveState/restoreState` kaldirildi — alt sayfada kalma sorunu giderildi
- Child route eslestirmesi — alt sayfalarda dogru tab highlighted
- **Dosya:** `BottomNavBar.kt`

### Siralama Butonlari (Sort Chips)
- **TrafficScreen** — 4 tab'a siralama eklendi (Hiz, Boyut, Protokol, Isim, Yeni/Eski, Hedef)
- **SystemLogsScreen** — Yeni Once, Eski Once, Onem, Kategori
- Cyberpunk glassmorphism chip tasarimi, secili=cyan

### Cihaz Yonetim Altyapi (Kismen)
- `DeviceResponseDto` → `isIptv`, `deviceType`, `riskScore`, `riskLevel` eklendi
- `DeviceUpdateDto` → `isIptv` eklendi
- `DeviceDetailViewModel` → `updateHostname()`, `updateBandwidth()`, `toggleIptv()` eklendi

---
**Onceki:** [SESSION-Q23-Q26.md](SESSION-Q23-Q26.md)
**Sonraki:** [SESSION.md](../SESSION.md) (guncel oturum)
