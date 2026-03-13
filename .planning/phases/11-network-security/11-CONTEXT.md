# Phase 11: Network Security - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** Roadmap requirements + existing codebase analysis

<domain>
## Phase Boundary

Android uygulamasinda ag guvenligi yonetimi — 3 alan:
1. **Firewall kurallari** — listeleme, ekleme, duzenleme, silme, oncelik siralama
2. **VPN peer yonetimi** — listeleme, ekleme, silme, QR kod goruntuleme/paylasma, durum
3. **DDoS koruma** — durum ekrani, basitlestirilmis saldiri haritasi, canli saldiri akisi

Bu ozelliklerin cogu SecurityScreen.kt'de ZATEN MEVCUT:
- Firewall tab: kural toggle + silme butonu + FAB ekleme
- VPN tab: start/stop, peer silme, QR dialog
- DDoS tab: temel bilgiler
Bu phase eksikleri tamamlayacak ve tam CRUD + UX iyilestirmesi yapacak.

</domain>

<decisions>
## Implementation Decisions

### Firewall
- Mevcut SecurityScreen Firewall tab'i genisletilecek
- Kural siralama (drag-and-drop veya up/down butonlari)
- Edit dialog (mevcut Add dialog'a duzenleme modu ekleme)
- Backend: /api/v1/firewall/* endpoint'leri

### VPN
- Mevcut SecurityScreen VPN tab'i genisletilecek
- QR kod goruntuleme + paylasma (ShareSheet)
- VPN global durum gostergesi
- Backend: /api/v1/vpn/* endpoint'leri

### DDoS
- DDoS durumu: aktif/pasif, savunma metrikleri
- Basitlestirilmis saldiri haritasi (mobil optimize — web'deki SVG dunya haritasi yerine liste/kart bazli)
- Canli saldiri akisi (son N saldiri)
- Backend: /api/v1/ddos/* endpoint'leri

### Claude's Discretion
- Saldiri haritasi mobil implementasyonu (SVG harita vs basit liste)
- Kural oncelik duzenleme UX'i (drag vs buton)
- DTO ve Repository organizasyonu
- Tab yapisi (mevcut SecurityScreen tab'lari icinde mi, ayri ekran mi)

</decisions>

<specifics>
## Specific Ideas

### Mevcut Android Kod (SecurityScreen.kt icinde)
- FirewallTab: kural listesi, toggle Switch, silme butonu, AddFirewallRuleDialog
- VpnTab: peer listesi, start/stop butonlari, peer silme, QR/config dialog (VpnPeerConfigDialog)
- SecurityRepository: getFirewallRules, addFirewallRule, deleteFirewallRule, getVpnPeers, addVpnPeer, deleteVpnPeer, startVpn, stopVpn

### Eksikler
- Firewall: kural DUZENLEME (edit) yok, oncelik siralama yok
- VPN: QR kod PAYLASMA (ShareSheet) yok, global durum gostergesi eksik
- DDoS: sadece temel bilgiler var, saldiri haritasi ve canli akis yok

### Backend Endpoint'ler
- GET/POST/PUT/DELETE /api/v1/firewall/rules
- GET/POST/DELETE /api/v1/vpn/peers, GET /api/v1/vpn/status
- GET /api/v1/ddos/status, GET /api/v1/ddos/attacks, GET /api/v1/ddos/stats

</specifics>

<deferred>
## Deferred Ideas

- Full SVG dunya haritasi (web versiyonu gibi) — mobil icin performans sorunu, basit liste yeterli
- VPN tunel istatistikleri (per-peer bandwidth) — ileride

</deferred>

---

*Phase: 11-network-security*
*Context gathered: 2026-03-13 via roadmap analysis*
