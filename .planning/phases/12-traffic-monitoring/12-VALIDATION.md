---
phase: 12
slug: traffic-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 12 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manuel test (APK deploy) |
| **Quick run command** | `./gradlew assembleDebug` |
| **Estimated runtime** | ~120 seconds |

## Sampling Rate

- **After every task commit:** `./gradlew assembleDebug`
- **After every plan wave:** APK deploy + manuel smoke test
- **Max feedback latency:** 120 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command |
|---------|------|------|-------------|-----------|-------------------|
| 12-01-01 | 01 | 1 | TRAF-01, TRAF-02, TRAF-03 | smoke | `./gradlew assembleDebug` |
| 12-01-02 | 01 | 1 | TRAF-04 | smoke | `./gradlew assembleDebug` |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| 5s auto-refresh canli akis | TRAF-01 | Canli API verisi |
| Sayfalama gecmis | TRAF-03 | API sayfalama |
| Per-device grafik | TRAF-04 | Vico rendering |

**Approval:** pending
