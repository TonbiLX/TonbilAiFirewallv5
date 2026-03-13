---
phase: 13
slug: communication-config
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Gradle assembleDebug (Android compile-time verification) |
| **Config file** | android/build.gradle.kts |
| **Quick run command** | `cd android && ./gradlew assembleDebug 2>&1 \| tail -5` |
| **Full suite command** | `cd android && ./gradlew assembleDebug 2>&1 \| tail -10` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd android && ./gradlew assembleDebug 2>&1 | tail -5`
- **After every plan wave:** Run `cd android && ./gradlew assembleDebug 2>&1 | tail -10`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | NOTIF-01,02,03,04 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |
| 13-01-02 | 01 | 1 | CHAT-01,02,03 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |
| 13-02-01 | 02 | 1 | TELE-01,02 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |
| 13-02-02 | 02 | 1 | WIFI-01,02,03 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |
| 13-02-03 | 02 | 1 | DHCP-01,02 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |
| 13-02-04 | 02 | 1 | SEC-01,02 | compile+runtime | `cd android && ./gradlew assembleDebug` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Push bildirim telefona ulaşıyor | NOTIF-01 | FCM cloud delivery | APK yükle, backend'den test bildirimi gönder |
| AI sohbet yanıt alıyor | CHAT-01 | Backend LLM bağlantısı gerekli | Sohbet ekranında mesaj gönder, yanıt kontrol et |
| WiFi AP açılıp kapanıyor | WIFI-01 | Fiziksel cihaz gerekli | AP toggle, SSID değiştir, bağlan |
| Telegram bot mesaj gönderiyor | TELE-01 | External service | Bot token gir, test mesajı gönder |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
