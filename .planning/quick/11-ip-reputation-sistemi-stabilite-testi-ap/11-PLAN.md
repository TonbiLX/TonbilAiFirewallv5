---
phase: quick-11
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - test_ip_reputation.py
autonomous: true
requirements: [QUICK-11]

must_haves:
  truths:
    - "Backend IP Reputation API endpointleri (config, summary, ips, cache, test) 200 donuyor"
    - "AbuseIPDB API key test endpoint calisiyor ve gecerli sonuc donuyor"
    - "Ulke engelleme PUT ile yazilabiliyor ve GET ile okunabiliyor"
    - "IP reputation worker Redis key'leri mevcut ve dogru formatta"
    - "Frontend IpReputationTab component'i crash etmeden yukleniyor (siyah ekran bug duzeltilmis)"
  artifacts:
    - path: "test_ip_reputation.py"
      provides: "End-to-end IP reputation test scripti"
  key_links:
    - from: "frontend IpReputationTab"
      to: "/api/v1/ip-reputation/*"
      via: "ipReputationApi.ts axios calls"
    - from: "backend ip_reputation API"
      to: "Redis reputation:* keys"
      via: "get_redis() async calls"
    - from: "ip_reputation worker"
      to: "AbuseIPDB external API"
      via: "httpx async client"
---

<objective>
IP Reputation sisteminin tum katmanlarini (backend API, Redis state, AbuseIPDB entegrasyonu, frontend renderlanma) canli Pi uzerinde test et.

Purpose: Quick-10'da eklenen IP reputation ozellikleri (AbuseIPDB key girisi, ulke engelleme, IP listesi, cache temizleme, test butonu) ve Quick-10 sirasinda tespit edilen siyah ekran bugunun duzeltilip duzeltilmedigini dogrula.
Output: Basarili/basarisiz test raporu (console ciktisi)
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@backend/app/api/v1/ip_reputation.py
@frontend/src/services/ipReputationApi.ts
@frontend/src/components/firewall/IpReputationTab.tsx

SSH erisim: pi.tonbil.com:2323 -> 192.168.1.2 (admin/benbuyum9087)
Backend API: http://192.168.1.2:8000/api/v1/
Frontend: http://192.168.1.2 (nginx -> dist/)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend API + Redis + AbuseIPDB entegrasyon testi</name>
  <files>test_ip_reputation.py</files>
  <action>
Python test scripti olustur. Paramiko ile SSH tunnel acip backend API'ye eris:

1. **Auth token al:** POST /api/v1/auth/login (admin/benbuyum9087) -> JWT token al

2. **GET /ip-reputation/config testi:**
   - 200 donmeli
   - Response'da su alanlar olmali: enabled, abuseipdb_key, abuseipdb_key_set, blocked_countries, check_interval, max_checks_per_cycle, daily_limit
   - abuseipdb_key_set == True olmali (key girildi)
   - abuseipdb_key maskelenms olmali (ilk 4 + son 4 karakter gorulmeli)

3. **GET /ip-reputation/summary testi:**
   - 200 donmeli
   - Response'da: total_checked, flagged_critical, flagged_warning, daily_checks_used, daily_limit
   - daily_limit == 900 olmali

4. **GET /ip-reputation/ips testi:**
   - 200 donmeli
   - Response'da: ips (array), total (int)
   - Eger IP varsa her birinde: ip, abuse_score, total_reports, country, city, isp, org, checked_at alanlari olmali

5. **POST /ip-reputation/test testi (AbuseIPDB key validation):**
   - 200 donmeli
   - status == "ok" olmali (key gecerli)
   - data.tested_ip == "8.8.8.8" olmali
   - data.abuse_score tanimliyken integer olmali

6. **PUT /ip-reputation/config - Ulke engelleme testi:**
   - Mevcut config'i oku (blocked_countries)
   - Test ulkesi ekle: blocked_countries'e "XX" ekle
   - PUT ile kaydet -> 200 olmali
   - GET ile tekrar oku -> "XX" listede olmali
   - Temizle: "XX"'i cikar ve PUT ile geri kaydet (eski duruma dondur)

7. **DELETE /ip-reputation/cache testi:**
   - NOT: Gercek cache'i silmemek icin, sadece endpoint'in 200 donup donmedigini kontrol et.
   - Eger cache bos ise (total_checked == 0) sil, yoksa SKIP et ve sadece endpoint varligini dogrula GET ile.

8. **Redis key kontrolu (SSH uzerinden):**
   - SSH ile Pi'ye baglan
   - `redis-cli -a TonbilAiRedis2026 GET reputation:enabled` -> "1" veya "0"
   - `redis-cli -a TonbilAiRedis2026 GET reputation:abuseipdb_key` -> bos olmamali
   - `redis-cli -a TonbilAiRedis2026 GET reputation:blocked_countries` -> JSON array
   - `redis-cli -a TonbilAiRedis2026 KEYS "reputation:ip:*" | head -5` -> varsa listele

9. **Worker calisma durumu (SSH):**
   - `sudo journalctl -u tonbilaios-backend --no-pager -n 50 | grep -i "ip_reputation\|reputation"` -> worker log kayitlari var mi

10. **Frontend build kontrolu (SSH):**
    - `/opt/tonbilaios/frontend/dist/` altinda assets/*.js dosyasinin icinde "IpReputation" veya "ip-reputation" metni var mi (grep)
    - Bu, component'in build ciktisina dahil oldugunu dogrular

Her test icin PASS/FAIL durumu yazdir. Sonunda ozet tablo goster.
Hata durumunda detayli hata mesaji yazdir (traceback degil, anlasilir mesaj).

SSH tunnel yerine dogrudan paramiko uzerinden HTTP istekleri gondermek icin:
- SSH jump host uzerinden port forwarding yap (localhost:18000 -> 192.168.1.2:8000)
- Ardindan requests/httpx ile localhost:18000 uzerinden API cagirlari yap

Alternatif olarak, SSH uzerinden curl komutlari calistir (daha basit):
- `curl -s -X POST http://localhost:8000/api/v1/auth/login ...` seklinde Pi uzerinde dogrudan calistir
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python test_ip_reputation.py</automated>
  </verify>
  <done>
    - Tum 10 test kategorisi PASS donuyor
    - AbuseIPDB API key gecerli ve calisiyor (test endpoint "ok" donuyor)
    - Ulke engelleme round-trip (yaz-oku-geri al) basarili
    - Redis key'leri dogru formatta mevcut
    - Worker log kayitlari var (calistigini gosteriyor)
    - Frontend build ciktisinda IpReputation component'i mevcut
    - Siyah ekran bug'i icin: component kodunda acik bir crash noktasi yok (runtime kontrolu frontend'de yapilir, burada build varligini dogruluyoruz)
  </done>
</task>

</tasks>

<verification>
Test scripti calistirildiginda tum testler PASS donmeli.
Herhangi bir FAIL varsa, sorunun hangi katmanda oldugu (API, Redis, Worker, Frontend) acikca belirtilmeli.
</verification>

<success_criteria>
- Backend API: 5 endpoint (config GET/PUT, summary, ips, test, cache) basarili yanit donuyor
- AbuseIPDB: Key gecerli, test endpoint 8.8.8.8 icin skor donuyor
- Redis: reputation:* key'leri dogru formatta mevcut
- Worker: Log kayitlarinda calistigi goruluyor
- Frontend: Build ciktisinda component dahil edilmis
- Ulke engelleme: PUT/GET round-trip calisiyor
</success_criteria>

<output>
After completion, create `.planning/quick/11-ip-reputation-sistemi-stabilite-testi-ap/11-SUMMARY.md`
</output>
