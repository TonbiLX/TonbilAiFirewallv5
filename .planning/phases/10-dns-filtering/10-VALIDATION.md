---
phase: 10
slug: dns-filtering
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manuel test (APK deploy + Pi SSH) |
| **Config file** | N/A |
| **Quick run command** | `./gradlew assembleDebug` |
| **Full suite command** | `./gradlew assembleDebug` + Pi deploy + manuel dogrulama |
| **Estimated runtime** | ~120 seconds (build) + manuel |

---

## Sampling Rate

- **After every task commit:** Run `./gradlew assembleDebug` (derleme hatasi yok)
- **After every plan wave:** APK Pi'ye deploy + manuel smoke test
- **Before `/gsd:verify-work`:** Full suite must be green + tum 4 requirement manuel dogrulanmis
- **Max feedback latency:** 120 seconds (build time)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | DNS-01 | smoke | `./gradlew assembleDebug` + manuel | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | DNS-02 | integration | Manuel (Pi SSH ile verify) | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | DNS-03 | smoke | `./gradlew assembleDebug` + manuel | Kismi | ⬜ pending |
| 10-02-02 | 02 | 1 | DNS-04 | smoke | `./gradlew assembleDebug` + manuel | Kismi | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DnsFilteringScreen.kt` — DNS-01, DNS-02 kapsami
- [ ] `DnsFilteringViewModel.kt` — DNS-01, DNS-02 kapsami
- [ ] `FullSecurityConfigDto.kt` veya mevcut SecurityConfigDtos.kt guncellemesi — DNS-02, Guvenlik tab
- [ ] `ProfilesScreen.kt` content_filters guncelleme — DNS-04 kapsami
- [ ] `NavRoutes.kt` + `AppNavHost.kt` routing guncelleme

*Mevcut test altyapisi yok; proje Android APK sideload + manuel dogrulama kullaniyor*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DNS ozet ekraninda stats gorunuyor | DNS-01 | UI rendering + canli API verisi | APK deploy, DNS ekranini ac, stats kartlarini kontrol et |
| Toggle ile DNS filtreleme acilip kapaniyor | DNS-02 | Backend hot-reload + Pi DNS proxy | Toggle'a bas, Pi'de `redis-cli GET dns:filtering_enabled` kontrol et |
| Kategori listesi + blocklist baglama | DNS-03 | Coklu API cagri + UI state | Kategori ekranini ac, blocklist sec, kaydet, yeniden ac |
| Profil CRUD + kategori secimi | DNS-04 | Profil → kategori → bandwidth zinciri | Profil olustur, kategori sec, bandwidth gir, cihaza ata |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
