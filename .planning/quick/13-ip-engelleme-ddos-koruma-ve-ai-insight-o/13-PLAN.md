---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/workers/ip_reputation.py
autonomous: true
requirements: [AUTO-BLOCK-CRITICAL-IP, AUTO-BLOCK-COUNTRY]

must_haves:
  truths:
    - "AbuseIPDB skoru >= 80 olan IP'ler otomatik olarak nftables'da engellenir"
    - "Engellenen ulke listesindeki IP'ler otomatik olarak nftables'da engellenir"
    - "Backend hatasiz restart eder ve worker calismaya devam eder"
  artifacts:
    - path: "backend/app/workers/ip_reputation.py"
      provides: "auto_block_ip entegrasyonu"
      contains: "auto_block_ip"
  key_links:
    - from: "backend/app/workers/ip_reputation.py"
      to: "backend/app/workers/threat_analyzer.py"
      via: "auto_block_ip import"
      pattern: "from app.workers.threat_analyzer import auto_block_ip"
---

<objective>
IP Reputation worker'a otomatik engelleme ozelligini ekle.

Purpose: AbuseIPDB skoru >= 80 olan kritik tehdit IP'leri ve engellenen ulkelerden gelen IP'ler sadece AiInsight yazmakla kalmayip, nftables uzerinden otomatik engellenecek.
Output: Guncellenmis ip_reputation.py dosyasi, Pi'ye deploy edilmis ve calisir durumda.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@backend/app/workers/ip_reputation.py
@backend/app/workers/threat_analyzer.py (auto_block_ip fonksiyonu)
</context>

<interfaces>
<!-- threat_analyzer.py'den kullanilacak fonksiyon -->
```python
# backend/app/workers/threat_analyzer.py satir 270
async def auto_block_ip(ip: str, reason: str):
    """IP'yi otomatik engelle ve AiInsight yaz."""
    # Guvenilir IP korumasi dahili (TRUSTED_IPS kontrolu mevcut)
    # nftables'a engel kuralı ekler + AiInsight yazar + Telegram bildirim atar
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: IP Reputation — Kritik IP ve Ulke Engeli Otomatik Bloklama</name>
  <files>backend/app/workers/ip_reputation.py</files>
  <action>
1. Dosyanin basina import ekle:
   ```python
   from app.workers.threat_analyzer import auto_block_ip
   ```

2. `_process_ip()` fonksiyonunda, skor >= 80 blogu icinde (satir 298-309 arasi), mevcut `_write_ai_insight` cagrisindan SONRA otomatik engelleme ekle:
   ```python
   if abuse_score >= 80:
       # ... mevcut message ve action tanimlari ...
       logger.warning(f"[KRITIK] {message}")
       await _write_ai_insight(Severity.CRITICAL, message, action)
       # OTOMATIK ENGELLEME
       await auto_block_ip(ip, f"AbuseIPDB kritik skor: {abuse_score}/100, raporlar: {total_reports}")
   ```

3. `_check_country_block()` fonksiyonunda (satir 342-361), mevcut `_write_ai_insight` cagrisindan SONRA otomatik engelleme ekle:
   ```python
   async def _check_country_block(ip: str, country_code: str, blocked_countries: list[str]) -> None:
       # ... mevcut kontroller ...
       logger.warning(f"[ULKE ENGEL] {message}")
       await _write_ai_insight(Severity.CRITICAL, message, action, category="country_block")
       # OTOMATIK ENGELLEME
       await auto_block_ip(ip, f"Engellenen ulke: {country_code}")
   ```

NOT: `auto_block_ip` icinde zaten TRUSTED_IPS korumasi var (192.168.1.1, 192.168.1.2 vb. asla engellenmez). Ekstra kontrol gerekmez.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "import ast; ast.parse(open('backend/app/workers/ip_reputation.py').read()); print('SYNTAX OK')" && grep -c "auto_block_ip" backend/app/workers/ip_reputation.py</automated>
  </verify>
  <done>ip_reputation.py dosyasinda auto_block_ip cagrisi 3 yerde bulunur (1 import + 2 cagri). Syntax hatasi yok.</done>
</task>

<task type="auto">
  <name>Task 2: Pi'ye Deploy + Backend Restart + Dogrulama</name>
  <files>deploy_quick13.py</files>
  <action>
Deploy scripti olustur ve calistir. Script su adimlari yapacak:

1. Paramiko ile SSH baglantisi kur (jump host: pi.tonbil.com:2323 -> 192.168.1.2:22, user: admin, pass: benbuyum9087)
2. `backend/app/workers/ip_reputation.py` dosyasini SFTP ile `/tmp/ip_reputation.py` olarak yukle
3. `sudo cp /tmp/ip_reputation.py /opt/tonbilaios/backend/app/workers/ip_reputation.py` ile hedef dizine kopyala
4. `sudo systemctl restart tonbilaios-backend` ile backend'i yeniden baslat
5. 5 saniye bekle, `sudo systemctl is-active tonbilaios-backend` ile servis durumunu kontrol et
6. `sudo journalctl -u tonbilaios-backend --since '30 seconds ago' --no-pager -n 30` ile hata olup olmadigini kontrol et
7. Sonuclari ekrana yazdir

SSH jump host uzerinden ProxyJump tunnel ile baglan (CLAUDE.md'deki yontem 1).
  </action>
  <verify>
    <automated>python deploy_quick13.py</automated>
  </verify>
  <done>Backend "active" durumunda, journalctl'de import hatasi veya traceback yok, ip_reputation worker "basliyor" mesaji gorunuyor.</done>
</task>

</tasks>

<verification>
- ip_reputation.py'de `auto_block_ip` import edilmis
- Skor >= 80 durumunda `auto_block_ip` cagriliyor
- Engellenen ulke durumunda `auto_block_ip` cagriliyor
- Backend Pi'de hatasiz calisiyor
</verification>

<success_criteria>
- Backend restart sonrasi "active" durumunda
- Journalctl'de hata yok
- ip_reputation.py'de 3 auto_block_ip referansi mevcut (1 import + 2 cagri)
</success_criteria>

<output>
After completion, create `.planning/quick/13-ip-engelleme-ddos-koruma-ve-ai-insight-o/13-SUMMARY.md`
</output>
