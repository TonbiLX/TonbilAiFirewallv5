# Quick 23 — TAMAMLANDI
# Quick 24 — AbuseIPDB API Kontrol Butonu — TAMAMLANDI
# Quick 25 — DDoS harita paket/boyut fix — KISMEN (commit 20a1f18)
# Quick 26 — Ülke auto-save — TAMAMLANDI (commit fcbf578)

## DDoS Paket/Boyut Sorunu — DEVAM EDECEK
- Kök neden: nftables per-rule counter apply_all() ile sıfırlanıyor
- Çözüm: conntrack -L'den per-IP packets/bytes çekiliyor (sudo gerekli ✅)
- Sorun: attack-map endpoint timeout oluyor (conntrack parse + GeoIP çözümleme yavaş)
- Yapılacak: conntrack parse'ı optimize et (sadece attacker IP'leri filtrele, tüm listeyi parse etme)
- Alternatif: `sudo conntrack -L -s {ip}` ile sadece bilinen IP'leri sorgula (daha hızlı)

## Quick 23 Durum: TAMAMLANDI
- APK build basarili: `apk-output/app-debug.apk` (72MB)
- GitHub Actions CI: `.github/workflows/android-build.yml`
- Tum 35+ ekran tamamlandi, placeholder kalmadi

## Quick 24 Durum: TAMAMLANDI
- **Gorev:** AbuseIPDB API kalan kullanim kontrolu + sayfaya kontrol butonu ekleme
- **Yapilan:**
  1. Backend: `GET /api/v1/ip-reputation/api-usage` endpoint eklendi
     - AbuseIPDB API'ye fresh sorgu yaparak X-RateLimit-Remaining ve X-RateLimit-Limit header dondurur
     - Redis cache ve yerel sayaci otomatik senkronize eder
     - limit, used, remaining, usage_percent alanlari doner
  2. Frontend: `ipReputationApi.ts`'e `checkApiUsage()` fonksiyonu eklendi
  3. Frontend: `IpReputationTab.tsx` gunluk kullanim stat kartina "Kontrol Et" butonu eklendi
     - Buton tiklandiginda AbuseIPDB API'den canli veri cekilir
     - Kalan istek, yuzde, kullanilan bilgileri guncellenir
     - API anahtari yoksa buton devre disi
  4. Deploy: 3 dosya Pi'ye yuklendi, frontend build OK, backend restart OK
