# Requirements: TonbilAiOS Bridge Isolation

**Defined:** 2026-02-25
**Core Value:** Modem sadece Pi'yi gorsun, tum LAN cihazlari modemden gizlensin — trafik Pi'nin IP stack'i uzerinden route edilsin.

## v1 Requirements

Requirements for bridge isolation transition. Each maps to roadmap phases.

### Bridge Isolation Core

- [ ] **ISOL-01**: Pi, bridge forward chain'inde eth0↔eth1 arasi L2 iletimi drop kurallari ile engelleyebilmeli
- [ ] **ISOL-02**: Pi, inet nat postrouting'de LAN subnet icin MASQUERADE kurali uygulayabilmeli
- [ ] **ISOL-03**: ip_forward=1 sysctl ayari aktif ve kalici olmali
- [ ] **ISOL-04**: br_netfilter modulu yuklu ve bridge-nf-call-iptables=1 aktif olmali
- [ ] **ISOL-05**: ICMP redirect (send_redirects) tum interface'lerde devre disi olmali
- [ ] **ISOL-06**: Eski bridge masquerade_fix tablosu kaldirilmali (MAC rewrite artik gereksiz)
- [ ] **ISOL-07**: Izolasyon kurallari atomik olarak uygulanmali (nft -f ile tek transaction)

### Rollback

- [ ] **ROLL-01**: remove_bridge_isolation() fonksiyonu ile seffaf kopru moduna donulebilmeli
- [ ] **ROLL-02**: Rollback sirasinda izolasyon kurallari handle ile silinmeli
- [ ] **ROLL-03**: Rollback sirasinda ICMP redirect'ler geri acilmali

### Accounting Migration

- [ ] **ACCT-01**: Bridge accounting per_device chain'i (forward hook) upload/download chain'lerine (input/output hook) tasinmali
- [ ] **ACCT-02**: Upload chain: iifname eth1, ether saddr MAC ile counter kurallar icermeli
- [ ] **ACCT-03**: Download chain: oifname eth1, ether daddr MAC ile counter kurallar icermeli
- [ ] **ACCT-04**: add_device_counter(mac) yeni chain'lere kural eklemeli
- [ ] **ACCT-05**: remove_device_counter(mac) her iki chain'den kural silmeli
- [ ] **ACCT-06**: read_device_counters() her iki chain'i okuyup birlestirmeli
- [ ] **ACCT-07**: sync_device_counters(macs) yeni chain isimlerini kullanmali

### TC Mark Migration

- [ ] **TCMK-01**: TC mark chain (forward hook) tc_mark_up/tc_mark_down chain'lerine (input/output hook) tasinmali
- [ ] **TCMK-02**: tc_mark_up: iifname eth1, ether saddr MAC ile meta mark set kurallar icermeli
- [ ] **TCMK-03**: tc_mark_down: oifname eth1, ether daddr MAC ile meta mark set kurallar icermeli
- [ ] **TCMK-04**: add_device_limit(mac, rate, ceil) yeni chain'lere mark kurali eklemeli
- [ ] **TCMK-05**: remove_device_limit(mac) her iki chain'den mark kurallarini silmeli

### Startup & Persistence

- [ ] **STRT-01**: main.py lifespan fonksiyonu ensure_bridge_masquerade() yerine ensure_bridge_isolation() cagirmali
- [ ] **STRT-02**: sysctl ayarlari /etc/sysctl.d/99-bridge-isolation.conf'a yazilmali
- [ ] **STRT-03**: nftables kurallari /etc/nftables.conf'a persist edilmeli
- [ ] **STRT-04**: br_netfilter modulu /etc/modules-load.d/ ile otomatik yuklenecek sekilde ayarlanmali

### DHCP Gateway

- [ ] **DHCP-01**: dnsmasq konfigurasyonunda gateway .1'den .2'ye degistirilmeli
- [ ] **DHCP-02**: dhcp_pools veritabani tablosunda gateway guncellenmeli

### Validation

- [ ] **VALD-01**: Modem ARP tablosunda sadece Pi MAC'i gorunmeli (tcpdump dogrulama)
- [ ] **VALD-02**: Mevcut cihazlarin conntrack ESTABLISHED baglantiları mevcut olmali
- [ ] **VALD-03**: Pi internet erisimi calismali (curl testi)
- [ ] **VALD-04**: DNS cozumlemesi calismali (dig testi)
- [ ] **VALD-05**: Bridge accounting counter'lari artmali (upload/download chain'ler)
- [ ] **VALD-06**: Bridge forward chain'de drop kurallari gorunmeli
- [ ] **VALD-07**: Yapay cihaz testi: veth namespace ile gateway .2 ve internet erisimi dogrulanmali

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Transition

- **ENHN-01**: Counter deger koruma (hook gecisi sirasinda sifirlanma onleme)
- **ENHN-02**: DHCP lease force-renewal (kisa lease suresi gecici ayar)
- **ENHN-03**: Conntrack flush (gateway degisikliginden sonra stale entry temizleme)
- **ENHN-04**: Mode status API endpoint (bridge/router durumu sorgulama)

## Out of Scope

| Feature | Reason |
|---------|--------|
| br0 bridge tamamen kaldirma | MAC tabanli accounting bridge layer'a bagli, 5+ alt sistem degisikligi gerektirir |
| VLAN segmentasyon | Ayri milestone, switch desteyi gerektirir |
| IPv6 NAT (NAT66) | Ev agi icin gereksiz, karmasiklik ekler |
| dnsmasq'i baska DHCP ile degistirme | Gecis sirasinda iki sistem degisikligi debug'u zorlastirir |
| TC qdisc degisiklikleri | Sadece nftables mark chain'leri gocuyor, HTB qdisc'ler degismiyor |
| Frontend UI degisiklikleri | Bu milestone sadece backend/HAL |
| Pi'ye SSH deploy | Kullanici manuel yapacak |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ISOL-01 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-02 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-03 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-04 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-05 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-06 | Phase 1 — Bridge Isolation Core | Pending |
| ISOL-07 | Phase 1 — Bridge Isolation Core | Pending |
| ROLL-01 | Phase 1 — Bridge Isolation Core | Pending |
| ROLL-02 | Phase 1 — Bridge Isolation Core | Pending |
| ROLL-03 | Phase 1 — Bridge Isolation Core | Pending |
| ACCT-01 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-02 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-03 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-04 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-05 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-06 | Phase 2 — Accounting Chain Migration | Pending |
| ACCT-07 | Phase 2 — Accounting Chain Migration | Pending |
| TCMK-01 | Phase 3 — TC Mark Chain Migration | Pending |
| TCMK-02 | Phase 3 — TC Mark Chain Migration | Pending |
| TCMK-03 | Phase 3 — TC Mark Chain Migration | Pending |
| TCMK-04 | Phase 3 — TC Mark Chain Migration | Pending |
| TCMK-05 | Phase 3 — TC Mark Chain Migration | Pending |
| STRT-01 | Phase 4 — Startup and Persistence | Pending |
| STRT-02 | Phase 4 — Startup and Persistence | Pending |
| STRT-03 | Phase 4 — Startup and Persistence | Pending |
| STRT-04 | Phase 4 — Startup and Persistence | Pending |
| DHCP-01 | Phase 5 — DHCP Gateway and Validation | Pending |
| DHCP-02 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-01 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-02 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-03 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-04 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-05 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-06 | Phase 5 — DHCP Gateway and Validation | Pending |
| VALD-07 | Phase 5 — DHCP Gateway and Validation | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after roadmap creation*
