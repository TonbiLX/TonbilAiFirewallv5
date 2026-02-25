# Phase 1: Bridge Isolation Core - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

HAL'a bridge izolasyon fonksiyonlari eklemek: `ensure_bridge_isolation()` (7 adimli L2 drop + NAT MASQUERADE) ve `remove_bridge_isolation()` (handle-based rollback). Tek dosya degisikligi: `backend/app/hal/linux_nftables.py`. Mevcut `ensure_bridge_masquerade()` deprecated olarak isaretlenir ama silinmez (Phase 4'te main.py swap yapilacak).

</domain>

<decisions>
## Implementation Decisions

### Hata Yonetimi ve Guvenlik
- MASQUERADE kurali (Step 4) basarisiz olursa: sessizce dur, logger.error yaz, drop kurallarini UYGULAMA. SSH lockout'u onlemek icin return et.
- Drop kurallari (Step 5) basarisiz olursa: RuntimeError firlat. MASQUERADE zaten aktif, SSH guvende — ama caller izolasyonun tamamlanmadigini bilmeli.
- Sysctl ayarlari (Step 1-3) basarisiz olursa: log yaz, devam et (check=False). Mevcut codebase patterni ile tutarli.
- Loglama: Her adim icin ayri log yazilsin (Step 1: ip_forward=1 set, Step 4: MASQUERADE applied, vb.). Debug icin adim adim takip mumkun olmali.

### Rollback Davranisi
- MASQUERADE kurali (bridge_lan_masq) rollback'te yerinde birakilisin — transparent bridge modunda zarar vermez, diger NAT kurallarini etkileyebilir.
- masquerade_fix tablosu rollback'te geri yuklenmeyecek — eski workaround, gereksiz karmasiklik.
- ip_forward rollback'te 1'de kalsin — kapatmak VPN veya port forwarding gibi servisleri bozabilir.
- Rollback sonrasi dogrulama: nft list chain ile kontrol et, kalan bridge_isolation kurali varsa logger.warning yaz.

### Idempotency ve Siralama
- Mevcut kural tespiti: Comment anchor kontrolu (`bridge_isolation_lan_wan`, `bridge_isolation_wan_lan`, `bridge_lan_masq` string'leri ruleset icerisinde aranir).
- Sysctl ayarlari her cagrilisinda yeniden yazilsin (sysctl -w idempotent, kontrol eklemeye gerek yok).
- masquerade_fix tablosu yoksa sessizce atlasin — log bile yazmaya gerek yok.
- Tek nft list ruleset sorgusu: Fonksiyon basinda bir kez cagrilir, sonuc degiskende tutulur, tum adimlar bu string'i kontrol eder.

### Test ve Dogrulama Stratejisi
- Lokal dogrulama: ast.parse ile syntax kontrolu + grep ile anchor kontrolu + fonksiyon sirasi assertion (MASQUERADE anchor < drop rule anchor).
- Pi'de canli test: 7 adimli dogrulama (nft list rules, curl google.com, sysctl kontrol, masquerade_fix yok, SSH calisiyor, rollback, rollback sonrasi kontrol).
- Guvenlik agi: screen/tmux ile paralel session — bir session'da test, digerinde rollback komutu hazir.
- Deploy yontemi: deploy_dist.py (Paramiko SFTP, jump host uzerinden).

### Claude's Discretion
- Fonksiyonlarin tam docstring icerigi
- Helper fonksiyon organizasyonu (ortak kod cikarma)
- Log mesajlarinin tam metni
- Rollback dogrulama adiminin detay seviyesi

</decisions>

<specifics>
## Specific Ideas

- SSH lockout'u onleme en kritik konu: MASQUERADE her zaman drop kurallarindan ONCE uygulanmali, basarisiz olursa fonksiyon durmali.
- Rollback fonksiyonu "paranoid" olmali — silme isleminden sonra nft list ile kalan kural kontrolu yapsin.
- 7 adimli siranin degistirilmemesi gerektigini docstring'de belirt.
- Screen/tmux paralel session ile canli test yapmak kullanicinin tercihi — deploy ve test talimatlarina bu dahil edilmeli.

</specifics>

<deferred>
## Deferred Ideas

None — tartisma phase sinirlarinda kaldi.

</deferred>

---

*Phase: 01-bridge-isolation-core*
*Context gathered: 2026-02-25*
