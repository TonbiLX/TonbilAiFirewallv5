---
phase: 15
slug: release-build
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Gradle assembleRelease (Android release build verification) |
| **Config file** | android/build.gradle.kts |
| **Quick run command** | `cd android && ./gradlew assembleRelease 2>&1 \| tail -10` |
| **Full suite command** | `cd android && ./gradlew assembleRelease 2>&1 \| tail -20` |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd android && ./gradlew assembleRelease 2>&1 | tail -10`
- **After every plan wave:** Run `cd android && ./gradlew assembleRelease 2>&1 | tail -20`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | UX-03 | compile+sign | `cd android && ./gradlew assembleRelease` | ✅ | ⬜ pending |
| 15-01-02 | 01 | 1 | UX-03 | compile+sign | `cd android && ./gradlew assembleRelease` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `android/app/proguard-rules.pro` — R8 keep rules for Ktor/Koin/DTO classes
- [ ] `android/keystore/tonbilaios-release.jks` — Release signing keystore

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| APK S24 Ultra'ya yüklenip çalışıyor | UX-03 | Fiziksel cihaz gerekli | APK'yı Telegram/Drive ile aktar, yükle, giriş yap |
| Tüm ekranlar erişilebilir | UX-03 | UI navigasyon testi | Her menü öğesine tıkla, ekran açılışını kontrol et |
| Arka planda bildirim çalışıyor | UX-03 | Doze/background davranışı | Uygulamayı minimize et, backend'den event tetikle |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
