---
phase: quick-31
plan: "01"
subsystem: ip-reputation
tags: [frontend, backend, ip-reputation, abuseipdb, api-usage]
dependency_graph:
  requires: [quick-16, quick-17, quick-24]
  provides: [unified-api-usage-bar]
  affects: [frontend/src/components/firewall/IpReputationTab.tsx, backend/app/api/v1/ip_reputation.py]
tech_stack:
  added: []
  patterns:
    - Unified API usage top bar with 3 pools (Check, Blacklist, Check-Block)
    - Promise.all parallel API usage fetch
    - FastAPI endpoint ordering fix for path parameters
key_files:
  created:
    - .planning/quick/31-ip-itibar-api-kullanim-ust-bari/31-SUMMARY.md
  modified:
    - frontend/src/components/firewall/IpReputationTab.tsx
    - backend/app/api/v1/ip_reputation.py
decisions:
  - 3 API havuzunu tek üst barda birleştir, dağınık kontrol butonlarını kaldır
  - FastAPI check-block/{network:path} catch-all endpoint'ini dosya sonuna taşı (static path'ler önce)
  - DAILY_LIMIT 900→1000 (AbuseIPDB free plan gerçek limiti)
  - 429 response'ta da header'lardan gerçek limit oku ve status ok dön
  - Günlük Kullanım özet kartını kaldır (üst bar zaten gösteriyor)
metrics:
  duration: "25 min"
  completed_date: "2026-03-11"
  tasks_completed: 3
  files_modified: 2
---

# Quick 31: IP İtibar API Kullanım Üst Barı

**One-liner:** IP İtibar sayfasına 3 API havuzunu (Check, Blacklist, Check-Block) birleşik gösteren üst bar eklendi, dağınık kontrol butonları kaldırıldı, backend endpoint sıralama ve limit hataları düzeltildi.

## Sorun

- 3 farklı AbuseIPDB API havuzu (Check, Blacklist, Check-Block) sayfanın farklı yerlerinde dağınık küçük "Kontrol Et" butonlarıyla gösteriliyordu
- Check-Block API kullanım verisi hiç gelmiyordu (endpoint sıralama hatası)
- Günlük limit 900 gösteriliyordu, gerçek AbuseIPDB limiti 1000
- 429 (rate limit) durumunda API limiti okunamıyordu

## Çözüm

### Frontend (IpReputationTab.tsx)

1. **API Kullanım Üst Barı eklendi** — sayfanın en üstünde glassmorphism kartında:
   - **Check (IP Sorgu):** kullanım/limit + progress bar + kalan istek
   - **Blacklist (Kara Liste):** kullanım/limit + progress bar + kalan istek
   - **Check-Block (Subnet):** kullanım/limit + progress bar + kalan istek
   - **"Tümünü Kontrol Et" butonu:** 3 API'yi tek tıkla paralel sorgular (Promise.all)
   - Renk kodlaması: %70→sarı, %90→kırmızı

2. **Dağınık kontrol butonları kaldırıldı:**
   - Özet kartlarındaki "AbuseIPDB Kullanım" kartı + "Kontrol Et" butonu → kaldırıldı
   - Kara Liste başlığındaki "Günlük: x/y" + "Kontrol Et" butonu → kaldırıldı
   - Subnet Analizi başlığındaki "x/y (z%)" + "Kontrol Et" butonu → kaldırıldı

3. **Günlük Kullanım özet kartı kaldırıldı** — grid 4→3 sütuna düşürüldü (Toplam Kontrol, Kritik IP, Şüpheli IP)

4. **Otomatik yükleme:** `loadAll` sırasında blacklist ve check-block API usage arka planda çekiliyor

### Backend (ip_reputation.py)

1. **Endpoint sıralama düzeltmesi:** `@router.get("/check-block/{network:path}")` catch-all endpoint'i dosyanın EN SONUNA taşındı. Önceden `/check-block/api-usage` ve `/check-block/cache` static endpoint'lerinden ÖNCE tanımlıydı, `{network:path}` parametresi "api-usage" stringini yakalıyordu → `ipaddress.ip_network("api-usage")` ValueError fırlatıyordu.

2. **DAILY_LIMIT 900→1000:** AbuseIPDB free plan gerçek günlük limiti 1000.

3. **429 response handling:** `/api-usage` endpoint'i AbuseIPDB'den 429 aldığında artık response header'larından (`X-RateLimit-Limit`, `X-RateLimit-Remaining`) gerçek limit bilgisini okuyup Redis'e kaydediyor ve `status: "ok"` ile dönüyor.

## Doğrulama

- Pi'ye deploy edildi (backend restart + frontend static)
- Backend active
- "Tümünü Kontrol Et" butonu 3 havuzu da başarıyla dolduruyor
- Check: 1104/1000 (limit dolmuş, doğru gösteriyor)
- Blacklist: veri geliyor
- Check-Block: veri geliyor (endpoint sıralama fix'i çalışıyor)

## Deploy

- `deploy_api_bar_v2.py` — Paramiko SFTP backend + frontend birlikte deploy
