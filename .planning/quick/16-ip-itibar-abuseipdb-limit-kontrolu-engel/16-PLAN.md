---
plan: 16
title: "IP itibar: AbuseIPDB limit fix, timestamp kontrolu, toplu IP yonetimi"
type: quick
tasks: 3
---

# Quick Task 16: IP Itibar Sistemi Iyilestirmeleri

## Task 1: AbuseIPDB Gunluk Limit Duzeltmesi

**Sorun:** Sistem "doldu" gosteriyor ama AbuseIPDB'de sadece 611/1000 kullanilmis. Backend DAILY_LIMIT=900 hardcoded. Redis counter TTL sorunu olabilir - sadece count==1'de TTL set ediliyor.

**Dosyalar:**
- `backend/app/workers/ip_reputation.py` — DAILY_LIMIT, _increment_daily_counter, _process_ip
- `backend/app/api/v1/ip_reputation.py` — /summary endpoint

**Yapilacaklar:**
1. Redis `reputation:daily_checks` counter TTL fix: Her incr sonrasi TTL kontrol et (sadece count==1 degil)
2. AbuseIPDB response header'dan `X-RateLimit-Remaining` oku ve Redis'e kaydet
3. /summary endpoint'ine `abuseipdb_remaining` ekle (gercek AbuseIPDB limiti)
4. Frontend IpReputationTab'da gercek limit bilgisini goster

**Verify:** Redis counter TTL dogru set ediliyor, /summary gercek limit bilgisi donuyor

---

## Task 2: Engellenen IP Timestamp Kontrolu + Eski IP'ler Icin Fallback

**Sorun:** ddd6260 commit'inde fix yapildi ama eski auto-blocked IP'lerde `dns:threat:block_time:{ip}` key'i yok. Bu IP'ler "--" gosteriyor.

**Dosyalar:**
- `backend/app/workers/threat_analyzer.py` — get_blocked_ips(), auto_block_ip()
- `backend/app/api/v1/ip_management.py` — list_blocked_ips()

**Yapilacaklar:**
1. `get_blocked_ips()`'te block_time key'i yoksa block_expire TTL'den tahmini blocked_at hesapla
2. Fallback: `blocked_at = now - (block_duration - remaining_ttl)` formulu ile yaklaşik tarih
3. API response'ta her zaman bir blocked_at degeri dondur (null yerine)

**Verify:** Tum engellenen IP'ler (eski ve yeni) tarih gosteriyor

---

## Task 3: Toplu IP Yonetimi (Bulk Select + Unblock + Sure Belirleme)

**Sorun:** Engellenen IP'ler sadece tekli islem destekliyor. Toplu secim, toplu engel kaldirma ve toplu sure belirleme gerekli.

**Backend dosyalar:**
- `backend/app/schemas/blocked_ip.py` — Yeni bulk sema ekle
- `backend/app/api/v1/ip_management.py` — Yeni bulk endpoint'ler ekle

**Frontend dosyalar:**
- `frontend/src/services/ipManagementApi.ts` — Bulk API fonksiyonlari ekle
- `frontend/src/pages/IpManagementPage.tsx` — Multi-select UI + bulk action bar ekle

**Backend yapilacaklar:**
1. `BlockedIpBulkUnblock` schema: `ip_addresses: List[str]`
2. `BlockedIpBulkUpdateDuration` schema: `ip_addresses: List[str], duration_minutes: Optional[int]`
3. `BulkOperationResult` schema: `success_count: int, failed_count: int, failures: List`
4. `PUT /ip-management/blocked/bulk-unblock` endpoint
5. `PUT /ip-management/blocked/bulk-duration` endpoint
6. Her ikisi de hem DB hem Redis'i temizlemeli

**Frontend yapilacaklar:**
1. `selectedBlockedIps: Set<string>` state
2. Tablo header'da "tumunu sec" checkbox
3. Her satirin basinda checkbox
4. Secili IP sayisi gostergesi
5. Bulk action bar: "Engeli Kaldir" butonu + "Sure Belirle" dropdown + "Secimi Temizle"
6. `bulkUnblockIps()` ve `bulkUpdateBlockedIpsDuration()` API fonksiyonlari
7. Loading state ve hata yonetimi
8. Cyberpunk tema uyumu (neon-cyan checkbox, glassmorphism action bar)

**Verify:** Birden fazla IP secilip topluca engel kaldirilabiliyor ve sure degistirilebiliyor
