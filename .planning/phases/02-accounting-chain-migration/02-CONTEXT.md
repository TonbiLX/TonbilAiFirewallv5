# Phase 2: Accounting Chain Migration - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Mevcut bridge bandwidth sayac zincirlerini forward hook'tan input/output hook'lara tasimak. 4 fonksiyon yerinde degistirilir: `ensure_bridge_accounting_chain()`, `add_device_counter()`, `remove_device_counter()`, `read_device_counters()`. Tek dosya: `backend/app/hal/linux_nftables.py`. Caller'lar (bandwidth_monitor vb.) degismez.

</domain>

<decisions>
## Implementation Decisions

### Mevcut Kodla Uyum
- Fonksiyonlar yerinde degistirilir (rewrite, not new functions). Imzalar ve donus formatlari ayni kalir.
- add_device_counter(mac) ve remove_device_counter(mac) imzalari degismez — icerde iki chain'e (upload+download) ayri kural ekler/siler.
- read_device_counters() ayni format dondurir: {mac: total_bytes}. Upload + download merge edilir. bandwidth_monitor degismez.
- Eski forward hook chain'i (per_device) migration sirasinda otomatik tespit edilip silinir. Temiz gecis.

### Counter Veri Surekliligi
- Yeni chain'ler sifir counter'la baslar. Eski degerler Redis/DB'de zaten mevcut, kayip olmaz.
- Migration sirasindaki birkac sanyelik bosluk kabul edilebilir (bandwidth_monitor 20s aralikla okuyor, en fazla 1 okuma kaybi).
- Counter isaretleme: comment anchor kullanilir (acct_{mac}_upload, acct_{mac}_download). Mevcut parse mantigi korunur.

### Hata Yonetimi ve Rollback
- Chain olusturma atomic: upload basarili + download basarisiz = upload da silinir + exception firlatilir. Partial state birakilmaz.
- add_device_counter: bir chain'e ekleyip digerine ekleyemediyse, eklenen kural geri alinir + exception firlatilir. Ayni atomic felsefe.
- Phase 1 rollback (remove_bridge_isolation) yapilirsa accounting chain'ler yerinde kalir — zarar vermez.
- Loglama: Phase 1 ile tutarli, her adim icin ayri log yazilir.

### Test ve Dogrulama
- Lokal: Phase 1 ile ayni yaklasim (ast.parse + grep + fonksiyon varlik kontrolu + comment anchor kontrolu).
- Pi'ye deploy sonrasi ayrica canli test yapilacak (counter byte artisi dogrulamasi).
- bandwidth_monitor worker degismeden calismaya devam etmeli — bu bir dogrulama kriteri.
- Deploy: deploy_dist.py + screen/tmux (Phase 1 ile tutarli).

### Claude's Discretion
- Chain isim secimi (upload/download vs accounting_up/accounting_down)
- Eski chain tespit ve silme mantigi detaylari
- Comment anchor format detaylari
- Log mesajlarinin tam icerigi

</decisions>

<specifics>
## Specific Ideas

- Phase 1 ile ayni "atomic" felsefe: ya tamami basarili olur ya hicbiri. Partial state birakma.
- Fonksiyon imzalari ve donus formatlari KESINLIKLE degismeyecek — caller'lar (bandwidth_monitor, device_discovery) etkilenmemeli.
- Eski forward hook chain'i migration sirasinda otomatik temizlenmeli, cupruk birakilmamali.

</specifics>

<deferred>
## Deferred Ideas

None — tartisma phase sinirlarinda kaldi.

</deferred>

---

*Phase: 02-accounting-chain-migration*
*Context gathered: 2026-02-25*
