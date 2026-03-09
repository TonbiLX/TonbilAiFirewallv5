---
phase: quick-13
plan: 01
subsystem: backend-workers
tags: [ip-reputation, auto-block, nftables, abuseipdb, geoip]
key-files:
  modified:
    - backend/app/workers/ip_reputation.py
  created:
    - deploy_quick13.py
decisions:
  - "auto_block_ip threat_analyzer'dan import edildi — TRUSTED_IPS korumasi zaten dahili"
  - "Ekstra LAN/whitelist kontrolu gerekmedi — auto_block_ip icinde mevcut"
metrics:
  duration: "5 min"
  completed: "2026-03-09"
  tasks_completed: 2
  files_changed: 2
---

# Quick-13: IP Engelleme — AbuseIPDB + Ulke Otomatik Bloklama

**One-liner:** ip_reputation worker artik AbuseIPDB skoru >=80 ve engellenen ulke IP'lerini AiInsight'in yaninda nftables uzerinden de otomatik engelliyor.

## Yapilan Degisiklikler

### Task 1: ip_reputation.py — auto_block_ip Entegrasyonu

`backend/app/workers/ip_reputation.py` dosyasina 3 degisiklik eklendi:

1. **Import** (satir 27): `from app.workers.threat_analyzer import auto_block_ip`

2. **Kritik IP bloklama** (`_process_ip` fonksiyonu, abuse_score >= 80 blogu):
   ```python
   await auto_block_ip(ip, f"AbuseIPDB kritik skor: {abuse_score}/100, raporlar: {total_reports}")
   ```

3. **Ulke engelleme** (`_check_country_block` fonksiyonu):
   ```python
   await auto_block_ip(ip, f"Engellenen ulke: {country_code}")
   ```

`auto_block_ip` icinde zaten TRUSTED_IPS korumasi var (192.168.1.1, 192.168.1.2 vb. asla engellenmez).

### Task 2: Pi Deploy

- SFTP ile `/tmp/ip_reputation.py` olarak yuklendi
- `sudo cp` ile `/opt/tonbilaios/backend/app/workers/ip_reputation.py` hedefine kopyalandi
- `sudo systemctl restart tonbilaios-backend` calistirildi
- 5 saniye beklendi

## Dogrulama

- Syntax: PASS (`ast.parse` hatasi yok)
- auto_block_ip sayisi: 3 (1 import + 2 cagri) — PASS
- Backend durumu: `active` — PASS
- Journalctl: "IP reputation worker basliyor — 180s bekleniyor..." goruldu — PASS
- Import hatasi veya traceback: YOK — PASS

## Commits

| Hash | Mesaj |
|------|-------|
| 0c7e15f | feat(quick-13): ip_reputation — auto_block_ip entegrasyonu |
| e459bcf | chore(quick-13): deploy_quick13.py — Pi deploy + backend restart scripti |

## Deviations

None — plan tam olarak uygulandı.

## Self-Check: PASSED

- [x] backend/app/workers/ip_reputation.py guncellendi ve Pi'ye deploy edildi
- [x] auto_block_ip 3 yerde mevcut (1 import + 2 cagri)
- [x] Backend "active" durumunda
- [x] Journalctl'de hata yok
