---
phase: 08-dashboard
plan: 01
subsystem: data
tags: [ktor, websocket, dto, kotlinx-serialization, vico, koin]

requires:
  - phase: 07-authentication
    provides: TokenManager, ServerDiscovery, HttpClient, Koin DI setup
provides:
  - Dashboard REST DTO'lari (DashboardSummaryDto + 5 sub-DTO)
  - WebSocket realtime DTO'lari (RealtimeUpdateDto + 6 sub-DTO)
  - Lifecycle-aware WebSocketManager with SharedFlow
  - DashboardRepository with Result-based getSummary()
  - Vico charting dependency
affects: [08-02-dashboard-ui, 09-devices, 10-dns]

tech-stack:
  added: [vico-compose-m3 2.1.2, ktor-client-websockets 3.4.0]
  patterns: [SharedFlow for WebSocket messages, Result pattern for repository, lifecycle-aware connect/disconnect]

key-files:
  created:
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/DashboardDto.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/repository/DashboardRepository.kt
  modified:
    - android/gradle/libs.versions.toml
    - android/app/build.gradle.kts
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
    - android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt

key-decisions:
  - "ApiRoutes.wsUrl() dynamically derives WS URL from ServerDiscovery.activeUrl"
  - "WebSocketManager uses MutableSharedFlow with replay=1 and DROP_OLDEST overflow"

patterns-established:
  - "SharedFlow for streaming data: replay=1, extraBuffer=5, DROP_OLDEST"
  - "Repository Result pattern: try/catch wrapping Ktor calls"
  - "Dynamic WS URL from ServerDiscovery activeUrl (https->wss, http->ws)"

requirements-completed: [DASH-01, DASH-02]

duration: 2min
completed: 2026-03-06
---

# Phase 8 Plan 1: Dashboard Data Layer Summary

**Dashboard REST + WebSocket DTO'lari, lifecycle-aware WebSocketManager ve DashboardRepository ile Vico charting bagimliligi**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T11:40:32Z
- **Completed:** 2026-03-06T11:42:35Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Backend REST ve WebSocket JSON yapisina birebir eslesen 13 DTO sinifi olusturuldu
- Lifecycle-aware WebSocketManager: SharedFlow ile realtime veri akisi, 3sn reconnect
- DashboardRepository: Result pattern ile guvenli REST cagrisi
- Vico charting ve ktor-websockets bagimliliklari eklendi
- Koin DI'da WebSocketManager ve DashboardRepository singleton olarak kayitli

## Task Commits

Each task was committed atomically:

1. **Task 1: Vico + ktor-websockets deps ve Dashboard/WebSocket DTO'lari** - `bf0abff` (feat)
2. **Task 2: WebSocketManager + DashboardRepository + Koin wiring** - `e8f1bbd` (feat)

## Files Created/Modified
- `android/gradle/libs.versions.toml` - vico 2.1.2 ve ktor-client-websockets eklendi
- `android/app/build.gradle.kts` - Charting ve WebSocket implementation satirlari
- `android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/DashboardDto.kt` - 6 DTO sinifi (REST response)
- `android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt` - 7 DTO sinifi (WS messages)
- `android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt` - wsUrl() fonksiyonu eklendi
- `android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt` - Lifecycle-aware WS yoneticisi
- `android/app/src/main/java/com/tonbil/aifirewall/data/repository/DashboardRepository.kt` - REST veri katmani
- `android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt` - Koin singleton kayitlari

## Decisions Made
- ApiRoutes.wsUrl() ServerDiscovery.activeUrl'den dinamik WS URL uretiyor (https->wss, http->ws donusumu)
- WebSocketManager MutableSharedFlow replay=1, extraBuffer=5, DROP_OLDEST ile yapilandirildi

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tum DTO'lar ve veri katmani hazir, Plan 02 (Dashboard UI) dogrudan kullanabilir
- DashboardViewModel'in WebSocketManager ve DashboardRepository'yi inject etmesi Plan 02'de yapilacak

---
*Phase: 08-dashboard*
*Completed: 2026-03-06*
