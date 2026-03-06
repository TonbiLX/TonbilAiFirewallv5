---
phase: 07-authentication
plan: 01
subsystem: auth-data-layer
tags: [android, jwt, encrypted-storage, server-discovery, ktor-interceptor, koin-di, datastore]

# Dependency graph
requires:
  - "Ktor HttpClient factory with OkHttp engine (06-02)"
  - "Koin DI initialized in TonbilApp Application class (06-01)"
  - "ApiRoutes with BASE_URL and LOCAL_URL constants (06-02)"
provides:
  - "TokenManager with EncryptedSharedPreferences for JWT storage"
  - "ServerConfig with DataStore Preferences for server URL persistence"
  - "ServerDiscovery auto-switching between local (192.168.1.2) and remote (wall.tonbilx.com)"
  - "AuthInterceptor Ktor plugin for automatic Bearer token injection"
  - "AuthRepository with login/logout/getCurrentUser Result pattern"
  - "Auth DTOs: LoginRequest, LoginResponse, UserInfo @Serializable classes"
affects: [07-02-login-ui, 08-dashboard, 09-device-management]

# Tech tracking
tech-stack:
  added: [security-crypto-1.1.0-alpha06, biometric-1.2.0-alpha05, datastore-preferences-1.1.4]
  patterns: [encrypted-shared-preferences, datastore-preferences-flow, ktor-client-plugin, named-koin-qualifier, result-pattern-repository]

key-files:
  created:
    - android/app/src/main/java/com/tonbil/aifirewall/data/local/TokenManager.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/local/ServerConfig.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/AuthDtos.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/ServerDiscovery.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/AuthInterceptor.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/repository/AuthRepository.kt
  modified:
    - android/gradle/libs.versions.toml
    - android/app/build.gradle.kts
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiClient.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
    - android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt

key-decisions:
  - "EncryptedSharedPreferences with AES256_GCM MasterKey for JWT token storage"
  - "DataStore Preferences for server URL persistence (not SharedPreferences)"
  - "createClientPlugin for auth interceptor (Ktor 3.4.0 API)"
  - "Named Koin qualifier for test HttpClient vs main HttpClient"
  - "Result pattern for all AuthRepository API calls"
  - "ServerDiscovery tries lastConnected -> LOCAL_URL -> BASE_URL in order"

requirements-completed: [AUTH-03, AUTH-04, AUTH-05, AUTH-06]

# Metrics
duration: 3min
completed: 2026-03-06
---

# Phase 7 Plan 01: Auth Data Layer Summary

**JWT token storage with EncryptedSharedPreferences, server auto-discovery between local/remote URLs, Ktor auth interceptor plugin, and AuthRepository with Result-based login/logout/me API calls**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-06T10:40:35Z
- **Completed:** 2026-03-06T10:43:31Z
- **Tasks:** 2/2
- **Files modified:** 11

## Accomplishments

### Task 1: Token Storage + Server Config + DTOs
- TokenManager with EncryptedSharedPreferences: saveToken, getToken, clearToken, saveUserInfo, getUserInfo, isLoggedIn, biometric preference
- ServerConfig with DataStore Preferences: serverUrlFlow, setServerUrl, onboarding state, lastConnectedUrl
- AuthDtos: LoginRequest, LoginResponse, UserInfo @Serializable data classes matching backend API
- Added 3 new dependencies: security-crypto 1.1.0-alpha06, biometric 1.2.0-alpha05, datastore-preferences 1.1.4

### Task 2: Server Discovery + Auth Interceptor + Repository + DI
- ServerDiscovery: 3-step auto-discovery (lastConnected -> LOCAL_URL -> BASE_URL), testConnection via dashboard/summary, switchToUrl for manual override
- AuthInterceptor: Ktor createClientPlugin with onRequest (Bearer token injection) and onResponse (401 -> clearToken)
- ApiClient refactored: createHttpClient now takes ServerDiscovery + TokenManager, createTestHttpClient for connection testing
- ApiRoutes: added AUTH_ME, AUTH_LOGOUT, AUTH_CHECK endpoint constants
- AuthRepository: login (POST + token save), getCurrentUser (GET auth/me), logout (POST + clearToken), all wrapped in Result
- AppModule: full Koin DI wiring with named("test") qualifier for separate test HttpClient

## Task Commits

1. **Task 1: Token storage + server config + DTOs** - `84d8bb5` (feat)
2. **Task 2: Server discovery + auth interceptor + repository + DI** - `4ecd4e0` (feat)

## Decisions Made
- EncryptedSharedPreferences with AES256_GCM MasterKey (strongest available scheme)
- DataStore Preferences for server config (coroutine-friendly, type-safe)
- Ktor 3.4.0 createClientPlugin API for auth interceptor (not deprecated HttpSend)
- Named Koin qualifier separates test HttpClient (no interceptor, 3s/5s timeout) from main HttpClient
- Result<T> pattern for repository layer (caller handles success/failure)
- Server discovery order: lastConnected first (fast resume), then local, then remote

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Gradle wrapper missing:** The android project lacks gradlew executable and gradle-wrapper.jar, so local compilation verification could not be performed. Code was verified by manual review of imports, types, and API usage. This is a pre-existing issue from Phase 6.

## Next Phase Readiness
- TokenManager ready for Login UI (Phase 7 Plan 02) to save/retrieve JWT tokens
- ServerDiscovery ready for automatic URL switching on app startup
- AuthRepository ready for ViewModel integration (login form submission)
- AuthInterceptor automatically adds Bearer token to all subsequent API calls
- Biometric dependency already added for Phase 7 Plan 02

## Self-Check: PASSED

All 6 created files verified present. Both commits (84d8bb5, 4ecd4e0) confirmed in git log.
