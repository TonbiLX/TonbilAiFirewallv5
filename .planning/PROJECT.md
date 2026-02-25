# TonbilAiOS — Bridge Izolasyon Gecisi

## What This Is

TonbilAiOS, Raspberry Pi uzerinde calisan AI destekli bir router yonetim sistemidir. DNS filtreleme, cihaz yonetimi, VPN, DHCP, DDoS koruma, trafik izleme ve firewall ozellikleri sunar. Bu milestone'da seffaf kopru (transparent bridge) modundan izole router moduna gecis yapilacak.

## Core Value

Modem sadece Pi'yi gorsun, tum LAN cihazlari modemden tamamen gizlensin — trafik Pi'nin IP stack'i uzerinden route edilsin.

## Requirements

### Validated

- ✓ DNS filtreleme (profil tabanli) — existing
- ✓ Cihaz yonetimi (CRUD, kesfetme) — existing
- ✓ VPN yonetimi (WireGuard) — existing
- ✓ DHCP yonetimi — existing
- ✓ DDoS koruma — existing
- ✓ Trafik izleme (per-flow) — existing
- ✓ Bandwidth accounting (bridge counter) — existing
- ✓ TC bandwidth limiting — existing
- ✓ Dashboard (drag-drop grid) — existing
- ✓ AI sohbet — existing
- ✓ Telegram bildirimleri — existing
- ✓ Firewall kural yonetimi — existing
- ✓ Bridge masquerade (MAC rewrite) — existing (kaldirilacak)

### Active

- [ ] Bridge L2 forwarding izolasyonu (eth0↔eth1 arasi drop)
- [ ] Router modu NAT/MASQUERADE (Pi kendi MAC'i ile)
- [ ] Bridge accounting gecisi (forward → input/output hooks)
- [ ] TC marking gecisi (forward → input/output hooks)
- [ ] DHCP gateway degisikligi (.1 → .2)
- [ ] ICMP redirect devre disi birakma
- [ ] Eski bridge masquerade_fix tablosu temizligi
- [ ] Rollback mekanizmasi (izole → seffaf kopru geri donus)
- [ ] Startup guncelleme (main.py lifespan)

### Out of Scope

- Frontend UI degisiklikleri — bu milestone sadece backend/HAL katmanini kapsar
- Pi'ye SSH ile deploy — kullanici manuel yapacak
- Yeni ozellik ekleme — sadece mevcut yapiyi router moduna gecirme
- Modem konfigurasyonu — modem tarafinda degisiklik yok

## Context

- Pi uzerinde br0 = eth0 (WAN) + eth1 (LAN) seffaf kopru calisiyor
- Modem (192.168.1.1) tum cihazlarin MAC adreslerini gorebiliyor
- DHCP gateway su an .1 (modem), DNS zaten .2 (Pi)
- MASQUERADE + MAC rewrite (bridge_masquerade_fix) aktif
- Bandwidth accounting bridge forward hook'unda calisiyor
- TC marking de bridge forward hook'unda calisiyor
- Gecis sonrasi: L2 forwarding engellenir, trafik IP stack uzerinden route edilir
- BRIDGE_ISOLATION_PLAN.md detayli uygulama plani mevcut

## Constraints

- **Platform**: Raspberry Pi (ARM, Linux) — tum degisiklikler nftables ve sysctl uzerinden
- **Downtime**: Gecis sirasinda kisa sure internet kesintisi olabilir, minimize edilmeli
- **Uyumluluk**: Mevcut bandwidth accounting ve TC limiting aynen calismali (hook degisikligi ile)
- **Geri donus**: remove_bridge_isolation() ile seffaf kopru moduna donebilmeli

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Bridge L2 drop (forward chain) | Modem cihazlari gormemeli, en temiz izolasyon | — Pending |
| Accounting input/output hook | Forward hook izolasyondan sonra trafik gormez | — Pending |
| DHCP gateway .2 | Pi router olunca gateway Pi olmali | — Pending |
| Eski masquerade_fix kaldirilir | Router modunda MAC rewrite gereksiz | — Pending |
| Rollback dahil | Risk azaltma, geri donus mumkun olmali | — Pending |

---
*Last updated: 2026-02-25 after initialization*
