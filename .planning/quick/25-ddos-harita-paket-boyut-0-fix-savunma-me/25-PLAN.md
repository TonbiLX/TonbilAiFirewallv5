---
phase: 25-ddos-harita-paket-boyut-0-fix-savunma-me
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/ddos_service.py
  - frontend/src/pages/DdosMapPage.tsx
  - frontend/src/components/ddos/AttackFeed.tsx
autonomous: true
requirements: [DDOS-MAP-FIX, DDOS-CONN-LIMIT-FIX, DDOS-DEFENSE-TEST]
must_haves:
  truths:
    - "DDoS harita ekraninda saldiri akisinda her IP icin paket ve boyut degerleri 0 degil, gercek counter verisi gosteriliyor"
    - "Connection limit korumasindan yakalanan IP'ler de saldirgan listesinde gorunuyor"
    - "Redis gecmisinden gelen IP'ler icin de paket/boyut bilgisi mevcut"
  artifacts:
    - path: "backend/app/services/ddos_service.py"
      provides: "Per-IP paket/boyut hesaplama + conn_limit attacker set + attack_history'de counter kaydi"
    - path: "frontend/src/components/ddos/AttackFeed.tsx"
      provides: "Paket ve boyut sutunlari gercek veriyle dolu"
  key_links:
    - from: "ddos_service.get_attack_map_data"
      to: "nftables counter + Redis attack_history"
      via: "Per-protection counter bolunup IP basina dagilir + history'den counter okunur"
      pattern: "packets.*per_ip|attack_history.*packets"
---

<objective>
DDoS harita ekranindaki 3 sorunu cozmek:
1. Saldiri akisi tablosunda paket/boyut HEP 0 gosteriliyor — backend per-IP counter verisi uretmiyor
2. Connection limit (conn_limit) korumasindan yakalanan IP'ler saldirgan listesinde gorunmuyor — attacker set'e ekleme eksik
3. Redis ddos:attack_history'ye kaydedilen IP'lerde paket/boyut bilgisi yok

Purpose: DDoS harita sayfasi gercek ve anlamli veriler gostermeli, savunma mekanizmasi dogru raporlanmali.
Output: Calisan backend + frontend degisiklikleri, deploy edilecek dosyalar.
</objective>

<execution_context>
@E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md
</execution_context>

<context>
@backend/app/services/ddos_service.py
@backend/app/api/v1/ddos.py
@frontend/src/pages/DdosMapPage.tsx
@frontend/src/components/ddos/AttackFeed.tsx
@frontend/src/services/ddosApi.ts
@backend/app/models/ddos_config.py
@backend/app/schemas/ddos_config.py

<interfaces>
<!-- Mevcut attack map veri yapisi (DdosMapPage.tsx) -->
```typescript
interface AttackData {
  ip: string;
  lat: number; lon: number;
  country: string; countryCode: string; city: string; isp: string;
  type: string;
  packets: number;  // SORUN: her zaman 0
  bytes: number;    // SORUN: her zaman 0
}
```

<!-- Backend get_attack_map_data() mevcut davranis -->
```python
# Satir 1046-1062: prot_stats toplam koruma counter'ini AYNI IP'lere atiyor
# Redis history'den gelen IP'ler attacker_ips loop'unda YOK
prot_stats = by_prot.get(prot, {"packets": 0, "bytes": 0})
# → packets = prot toplami (veya 0), IP basina degil

# ATTACKER_SETS'te conn_limit YOK (nftables'da attacker set'e eklemiyor)
ATTACKER_SETS = {
    "ddos_syn_attackers": "syn_flood",
    "ddos_udp_attackers": "udp_flood",
    "ddos_icmp_attackers": "icmp_flood",
    "ddos_invalid_attackers": "invalid_packet",
}
# conn_limit icin sadece meter var, attacker set yok
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — conn_limit attacker set + per-IP counter + history counter kaydi</name>
  <files>backend/app/services/ddos_service.py</files>
  <action>
  3 sorun var, hepsini ddos_service.py'de coz:

  **A) conn_limit icin attacker set ekle:**
  1. ATTACKER_SETS dict'ine `"ddos_conn_attackers": "conn_limit"` ekle
  2. `_ensure_attacker_sets()` zaten ATTACKER_SETS'i itere ediyor, otomatik olusturulacak
  3. `apply_ddos_nft_rules()` icindeki conn_limit kuralini (satir 237-243) guncelle:
     - `add @ddos_conn_attackers { ip saddr }` ekle (reject'ten once)
     - Mevcut kural: `ct state new meter ddos_connlimit { ip saddr ct count over X } counter reject`
     - Yeni kural: `ct state new meter ddos_connlimit { ip saddr ct count over X } add @ddos_conn_attackers { ip saddr } counter reject`
  4. `flush_attacker_sets()`'te connlimit meter flush'u zaten var, ek degisiklik gerekmez
  5. `get_ddos_attacker_ips()` conn_limit meter'dan IP okuyor (satir 627-633), ama artik set'ten de okuyacak (ATTACKER_SETS'teki dongu ile otomatik). Meter'dan okuma kodunu kaldir veya birlestir:
     - ATTACKER_SETS'e ekledigimiz icin artik ana dongude okunacak
     - Mevcut meter okuma kodunu (satir 626-633) set ile birlestir: once set oku, sonra meter'dan okunan IP'leri de ekle (set'e gecis doneminde ikisinde de IP olabilir)

  **B) Per-IP paket/boyut hesaplama:**
  `get_attack_map_data()` fonksiyonunda (satir 1042-1063):
  - nftables'ta counter KURAL bazinda, IP bazinda degil. Per-IP counter almak mumkun degil.
  - Cozum: counter toplamini IP sayisina bol (tahmini per-IP deger) + Redis history'deki counter'lari kullan
  - Degisiklik:
    ```python
    # Mevcut (yanlis):
    prot_stats = by_prot.get(prot, {"packets": 0, "bytes": 0})
    "packets": prot_stats["packets"],  # AYNI deger tum IP'lere

    # Yeni (dogru):
    prot_stats = by_prot.get(prot, {"packets": 0, "bytes": 0})
    ip_count = max(len(ips), 1)
    per_ip_packets = prot_stats["packets"] // ip_count
    per_ip_bytes = prot_stats["bytes"] // ip_count
    # Her IP'ye esit paylastir
    "packets": per_ip_packets,
    "bytes": per_ip_bytes,
    ```

  **C) Redis attack_history'ye counter kaydet:**
  `check_ddos_anomaly_and_alert()` fonksiyonunda (satir 806-818), Redis'e kaydederken counter bilgisini de ekle:
  ```python
  # Mevcut:
  entry = _json.dumps({"ip": ip, "type": prot, "ts": now})
  # Yeni — delta ve counter bilgisi ekle:
  entry = _json.dumps({
      "ip": ip, "type": prot, "ts": now,
      "packets": alert.get("delta", 0) // max(len(external_ips), 1),
      "bytes": by_prot_current.get(prot, {}).get("bytes", 0) // max(len(external_ips), 1),
  })
  ```

  Ayrica `get_attack_map_data()`'da Redis history'den gelen IP'leri de attacks listesine ekle:
  - Mevcut kodda history IP'leri sadece `all_ips`'e ekleniyor (GeoIP icin) ama attacks listesine girmiyor
  - History'den gelen IP'leri ayri bir dict'te topla: `{ip: {"type": ..., "packets": ..., "bytes": ...}}`
  - Eger IP zaten attacker_ips'ten geldiyse, history counter'ini ekle/birlestir
  - Eger IP sadece history'de varsa, attacks listesine history verisiyle ekle

  **DIKKAT:**
  - Tum degisiklikler geri uyumlu olmali — eski Redis kayitlari packets/bytes icermiyor, 0 fallback kullan
  - conn_limit kuralinda `reject` korunmali (drop degil), `add @ddos_conn_attackers` reject'ten ONCE gelmeli
  - `_ensure_attacker_sets()` icindeki add set komutu mevcut set varsa hata vermez (nftables idempotent)
  </action>
  <verify>
    <automated>cd /opt/tonbilaios/backend && python -c "from app.services.ddos_service import ATTACKER_SETS; assert 'ddos_conn_attackers' in ATTACKER_SETS; print('OK: conn_limit attacker set mevcut')"</automated>
    Backend restart sonrasi: `curl -s http://localhost:8000/api/v1/ddos/attack-map -H 'Authorization: Bearer TOKEN'` ile attacks listesinde packets/bytes > 0 degerler donmeli (saldiri varsa).
  </verify>
  <done>
  - ATTACKER_SETS'te ddos_conn_attackers var ve nftables'a ekleniyor
  - conn_limit nftables kuralinda `add @ddos_conn_attackers { ip saddr }` var
  - get_attack_map_data() per-IP counter paylastirma yapiyor (toplam / IP sayisi)
  - Redis attack_history'ye packets/bytes bilgisi kaydediliyor
  - History'den gelen IP'ler de attacks listesinde gorunuyor
  </done>
</task>

<task type="auto">
  <name>Task 2: Deploy + canli test — Pi'ye yukle, kurallar uygula, harita dogrula</name>
  <files>backend/app/services/ddos_service.py</files>
  <action>
  Paramiko ile Pi'ye baglan (pi.tonbil.com:2323 → 192.168.1.2, admin/benbuyum9087):

  1. `backend/app/services/ddos_service.py` dosyasini Pi'ye SFTP ile yukle:
     - Hedef: `/opt/tonbilaios/backend/app/services/ddos_service.py`

  2. Backend restart:
     ```bash
     sudo systemctl restart tonbilaios-backend
     ```

  3. DDoS kurallarini yeniden uygula (conn_limit attacker set'in olusmasini sagla):
     ```bash
     curl -s http://localhost:8000/api/v1/ddos/apply -X POST -H 'Authorization: Bearer ...' -H 'Content-Type: application/json'
     ```

  4. Dogrulama:
     a. nftables'ta ddos_conn_attackers set'inin varligini kontrol et:
        `sudo nft list set inet tonbilai ddos_conn_attackers`
     b. conn_limit kuralinda `add @ddos_conn_attackers` olup olmadigini kontrol et:
        `sudo nft list chain inet tonbilai input | grep conn_limit`
     c. attack-map endpoint'ini cagir ve sonucu incele:
        `curl -s http://localhost:8000/api/v1/ddos/attack-map -H 'Authorization: Bearer ...'`
     d. Backend loglarinda hata olup olmadigini kontrol et:
        `sudo journalctl -u tonbilaios-backend --since '5 min ago' | tail -50`

  5. Eger saldiri yoksa ve haritada test edilemiyorsa, nft counter'lari kontrol et:
     `sudo nft list chain inet tonbilai input | grep -E 'ddos_.*counter'`
     — counter packets > 0 olan kurallar varsa, attack-map'te gorunmeli.
  </action>
  <verify>
    <automated>SSH uzerinden: `sudo nft list set inet tonbilai ddos_conn_attackers` basarili donmeli + `sudo nft list chain inet tonbilai input | grep 'ddos_conn_limit'` icinde `add @ddos_conn_attackers` olmali</automated>
  </verify>
  <done>
  - ddos_service.py Pi'de guncel
  - Backend hatasiz calisiyor
  - ddos_conn_attackers set'i nftables'ta mevcut
  - conn_limit kuralinda attacker set ekleme var
  - attack-map endpoint'i calisiyor
  </done>
</task>

</tasks>

<verification>
1. `sudo nft list set inet tonbilai ddos_conn_attackers` — set var mi?
2. `sudo nft list chain inet tonbilai input | grep conn_limit` — kural icinde `add @ddos_conn_attackers` var mi?
3. `curl /api/v1/ddos/attack-map` — attacks listesinde packets/bytes > 0 mu? (saldiri varsa)
4. `curl /api/v1/ddos/counters` — counter degerleri okunuyor mu?
5. Frontend DDoS harita sayfasinda saldiri akisi tablosunda paket/boyut sutunlarinda 0 olmayan degerler var mi?
</verification>

<success_criteria>
- DDoS harita sayfasinda saldiri akisi tablosundaki Paket ve Boyut sutunlari gercek degerler gosteriyor (0 degil)
- Connection limit korumasindan yakalanan IP'ler saldirgan listesinde gorunuyor
- Backend hatasiz calisiyor, nftables kurallari dogru uygulanmis
</success_criteria>

<output>
After completion, create `.planning/quick/25-ddos-harita-paket-boyut-0-fix-savunma-me/25-SUMMARY.md`
</output>
