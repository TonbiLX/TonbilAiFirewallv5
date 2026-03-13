---
phase: 11
slug: network-security
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 11 — Validation Strategy

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
- **Before `/gsd:verify-work`:** Full suite must be green + tum 10 requirement manuel dogrulanmis
- **Max feedback latency:** 120 seconds (build time)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | FW-01, FW-02, FW-03 | smoke | `./gradlew assembleDebug` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | VPN-01, VPN-02, VPN-03, VPN-04 | smoke | `./gradlew assembleDebug` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | DDOS-01, DDOS-02, DDOS-03 | smoke | `./gradlew assembleDebug` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Mevcut SecurityScreen.kt Firewall/VPN tab'lari genisletme — FW-01..03, VPN-01..04
- [ ] DDoS tab icerik genisletme — DDOS-01..03

*Mevcut test altyapisi yok; proje Android APK sideload + manuel dogrulama kullaniyor*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Firewall kural listesi + CRUD | FW-01, FW-02 | UI rendering + API | Kural listesi ac, yeni kural ekle, duzenle, sil |
| Kural priority siralama | FW-03 | UI drag/buton + API | Up/down butonlari ile siralama degistir, yeniden yukle |
| VPN peer QR paylasma | VPN-04 | ShareSheet = Android OS | QR dialog ac, paylas butonuna bas |
| DDoS saldiri haritasi | DDOS-02 | Canli veri + UI rendering | DDoS ekranini ac, saldiri listesini kontrol et |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
