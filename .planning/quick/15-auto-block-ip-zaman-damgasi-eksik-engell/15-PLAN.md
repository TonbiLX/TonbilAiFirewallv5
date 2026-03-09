---
phase: quick-15
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/workers/threat_analyzer.py
  - backend/app/api/v1/ip_management.py
autonomous: true
requirements: [QUICK-15]
---

<objective>
auto_block_ip fonksiyonu IP engellerken blocked_at timestamp kaydetmiyor.
Redis'e ayrı key ile timestamp ekle, get_blocked_ips'ten oku, API response'a aktar.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Backend — auto_block_ip timestamp kaydetme + get_blocked_ips okuma</name>
  <files>backend/app/workers/threat_analyzer.py</files>
  <action>
    1. auto_block_ip fonksiyonunda (satir ~299), `redis.set(f"dns:threat:block_expire:{ip}", reason, ex=block_dur)` satirindan SONRA yeni bir key ekle:
       ```python
       await redis.set(f"dns:threat:block_time:{ip}", datetime.utcnow().isoformat(), ex=block_dur)
       ```
       Bu key ayni TTL ile expire olur, boylece block expire ile sync kalir.

    2. get_blocked_ips fonksiyonunda (satir ~510-517), for loop icine blocked_at okuma ekle:
       Mevcut:
       ```python
       reason = await redis.get(f"dns:threat:block_expire:{ip}") or "Bilinmiyor"
       ttl = await redis.ttl(f"dns:threat:block_expire:{ip}")
       ```
       Sonrasina ekle:
       ```python
       blocked_at = await redis.get(f"dns:threat:block_time:{ip}")
       ```
       Ve result dict'ine ekle:
       ```python
       result.append({
           "ip": ip,
           "reason": reason,
           "remaining_seconds": max(ttl, 0),
           "blocked_at": blocked_at,
       })
       ```

    NOT: datetime import'u zaten dosyada mevcut (auto_block_ip icinde kullaniliyor).
  </action>
  <done>auto_block_ip timestamp kaydediyor, get_blocked_ips blocked_at donduruyor.</done>
</task>

<task type="auto">
  <name>Task 2: API — blocked_at None yerine Redis degerini kullan</name>
  <files>backend/app/api/v1/ip_management.py</files>
  <action>
    ip_management.py satir ~189'da:
    Mevcut: `blocked_at=None,`
    Yeni: `blocked_at=r.get("blocked_at"),`
  </action>
  <done>API response'ta otomatik engellenen IP'ler icin blocked_at dolduruluyor.</done>
</task>

</tasks>
