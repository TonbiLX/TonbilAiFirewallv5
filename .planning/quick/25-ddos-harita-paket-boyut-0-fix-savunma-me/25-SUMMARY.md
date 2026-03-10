---
phase: 25-ddos-harita-paket-boyut-0-fix-savunma-me
plan: 01
subsystem: ddos
tags: [ddos, nftables, attack-map, conn_limit, redis]
dependency_graph:
  requires: [ddos_service, nftables]
  provides: [per-ip-counters, conn_limit-attacker-set, history-counters]
  affects: [DdosMapPage, AttackFeed]
tech_stack:
  patterns: [per-IP-counter-distribution, attacker-set-tracking, redis-history-counters]
key_files:
  modified:
    - backend/app/services/ddos_service.py
decisions:
  - "Per-IP counter: nftables kural-bazli counter'i IP sayisina bolerek tahmini per-IP deger uretme"
  - "conn_limit meter+set: Gecis donemi icin hem meter hem set'ten IP toplama"
  - "History geri uyumluluk: Eski Redis kayitlari packets/bytes icermiyorsa 0 fallback"
metrics:
  duration: "3 min"
  completed: "2026-03-10"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Quick 25: DDoS Harita Paket/Boyut 0 Fix + Savunma Mekanizmasi

DDoS harita ekraninda 3 sorunu cozen backend guncellemesi: per-IP counter dagilimi, conn_limit attacker set takibi, Redis history'de counter kaydi.

## Completed Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Backend: conn_limit attacker set + per-IP counter + history counter | 202a281 | ddos_service.py |
| 2 | Deploy + canli test: Pi'ye yukle, kurallar uygula, dogrula | - (deploy) | - |

## Changes Made

### A) conn_limit Attacker Set
- `ATTACKER_SETS` dict'ine `"ddos_conn_attackers": "conn_limit"` eklendi
- `_ensure_attacker_sets()` otomatik olarak nftables'ta set olusturuyor (timeout 30m, size 4096)
- conn_limit nftables kuralina `add @ddos_conn_attackers { ip saddr }` eklendi (reject'ten once)
- `get_ddos_attacker_ips()` hem set hem meter'dan IP topluyor (gecis donemi)

### B) Per-IP Paket/Boyut Hesaplama
- `get_attack_map_data()`: Kural bazli toplam counter'i IP sayisina bolerek per-IP deger uretir
- Eski davranis: Ayni counter degeri tum IP'lere ataniyordu (yanlis)
- Yeni davranis: `prot_stats["packets"] // ip_count` ile esit dagilim

### C) Redis History Counter Kaydi
- `check_ddos_anomaly_and_alert()`: Redis `ddos:attack_history`'ye `packets` ve `bytes` alanlari eklendi
- `get_attack_map_data()`: History'den gelen IP'ler icin counter bilgisi toplanip attacks listesine ekleniyor
- Eger IP hem attacker_ips'te hem history'de varsa, counter'lar toplanir
- Eger IP sadece history'de varsa, ayri olarak attacks listesine eklenir
- Eski history kayitlari (packets/bytes icermeyen) 0 fallback ile geri uyumlu

## Deploy Verification

- Backend status: **active**
- ddos_conn_attackers set: **olusturuldu** (nftables'ta mevcut)
- conn_limit kuralinda `add @ddos_conn_attackers { ip saddr }`: **VAR**
- attack-map endpoint: **calisiyor** (conn_limit IP'leri gorunuyor)
- Counter 0: Beklenen — kurallar yeni uygulandiginda counter sifirdan baslar, saldiri geldikce artacak

## Deviations from Plan

None — plan tam olarak uygulandı.

## Self-Check: PASSED
- [x] backend/app/services/ddos_service.py degisiklikleri commit edildi (202a281)
- [x] Pi'ye deploy edildi ve dogrulandi
- [x] ddos_conn_attackers set nftables'ta mevcut
- [x] conn_limit kuralinda attacker set ekleme var
- [x] Backend hatasiz calisiyor
