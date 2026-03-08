---
phase: quick
plan: 10
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/ip_reputation.py
  - frontend/src/services/ipReputationApi.ts
  - frontend/src/components/firewall/IpReputationTab.tsx
  - frontend/src/pages/FirewallPage.tsx
  - backend/app/api/v1/router.py
autonomous: true
---

<objective>
IP Reputation yonetim arayuzu — Guvenlik Duvari sayfasina yeni tab olarak eklenir.
AbuseIPDB API key girme/kaydetme, ulke/bolge sinirlandirma, worker acma/kapatma,
kontrol edilen IP'lerin listesi ve istatistikleri gosterilir.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Backend API — IP Reputation Ayarlari Endpoint</name>
  <files>backend/app/api/v1/ip_reputation.py, backend/app/api/v1/router.py</files>
  <action>
  Yeni backend API dosyasi: `backend/app/api/v1/ip_reputation.py`

  Endpoints:
  - GET /ip-reputation/config — Mevcut ayarlari getir (Redis'ten)
  - PUT /ip-reputation/config — Ayarlari guncelle (API key, enabled, country blocks)
  - GET /ip-reputation/summary — IP reputation ozet istatistikleri
  - GET /ip-reputation/ips — Kontrol edilen IP listesi (cache'ten)
  - DELETE /ip-reputation/cache — Cache temizle

  Redis key'leri (ip_reputation.py worker ile uyumlu):
  - reputation:abuseipdb_key — API key
  - reputation:enabled — Worker aktif/pasif (default: "1")
  - reputation:blocked_countries — JSON array ["CN", "RU", ...]
  - reputation:ip:{ip} — HASH (mevcut cache)
  - reputation:daily_checks — Gunluk sayac

  router.py'ye ekleme: ip_reputation router'i register et
  </action>
</task>

<task type="auto">
  <name>Task 2: Frontend — IpReputationTab + API Service</name>
  <files>frontend/src/services/ipReputationApi.ts, frontend/src/components/firewall/IpReputationTab.tsx</files>
  <action>
  1. ipReputationApi.ts: API cagrilari
  2. IpReputationTab.tsx: Cyberpunk glassmorphism UI
     - Ayarlar bolumu: API key input (masked), worker toggle, kaydet butonu
     - Ulke sinirlandirma: ulke kodu ekle/kaldir (multi-select chip UI)
     - Istatistikler: toplam kontrol, isaretlenen, gunluk kullanim
     - IP Listesi: tablo (IP, skor, ulke, ISP, tarih) skor bazli renklendirme
  </action>
</task>

<task type="auto">
  <name>Task 3: FirewallPage Entegrasyonu</name>
  <files>frontend/src/pages/FirewallPage.tsx</files>
  <action>
  - ActiveTab tipine "reputation" ekle
  - Tab butonunu ekle (Fingerprint icon + "IP Itibar" text)
  - Tab iceriginde IpReputationTab renderla
  </action>
</task>

</tasks>
