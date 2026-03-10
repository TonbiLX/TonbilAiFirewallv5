# Quick 23–26 Arsiv

## Quick 23 — Android 35+ Ekran Tamamlama ✅
- APK build basarili: `apk-output/app-debug.apk` (72MB)
- GitHub Actions CI: `.github/workflows/android-build.yml`
- Tum 35+ ekran tamamlandi, placeholder kalmadi

## Quick 24 — AbuseIPDB API Kontrol Butonu ✅
- Backend: `GET /api/v1/ip-reputation/api-usage` endpoint
- Frontend: IpReputationTab'a "Kontrol Et" butonu
- AbuseIPDB limit/used/remaining bilgileri canli

## Quick 25 — DDoS Harita Paket/Boyut Fix (Kismen)
- Kok neden: nftables per-rule counter apply_all() ile sifirlaniyor
- Cozum: conntrack -L'den per-IP packets/bytes (commit 20a1f18)
- Sorun: attack-map endpoint timeout — conntrack parse + GeoIP yavas

## Quick 26 — Ulke Auto-Save ✅ (commit fcbf578)
- IP reputation ulke ekleme/kaldirma aninda backend'e kaydediliyor

---
**Sonraki:** [SESSION-Q27-Q29.md](SESSION-Q27-Q29.md)
