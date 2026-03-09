# Quick 15: auto_block_ip Zaman Damgasi Fix

## Sorun
`auto_block_ip` fonksiyonu IP engellerken `blocked_at` timestamp kaydetmiyordu. Bu yuzden otomatik engellenen IP'ler tabloda tarih gostermiyordu ("--") ve zaman siralamasi yapilamiyordu.

## Duzeltmeler

### 1. threat_analyzer.py — auto_block_ip (satir ~301)
- Yeni Redis key: `dns:threat:block_time:{ip}` — `datetime.utcnow().isoformat()` degerini block_dur TTL ile kaydeder
- Bu key, `block_expire` ile ayni TTL'ye sahip, boylece expire olunca ikisi birlikte silinir

### 2. threat_analyzer.py — get_blocked_ips (satir ~513)
- `dns:threat:block_time:{ip}` key'inden `blocked_at` degerini okuyor
- Sonuc dict'ine `"blocked_at": blocked_at` eklendi

### 3. ip_management.py (satir ~189)
- `blocked_at=None` → `blocked_at=r.get("blocked_at")` olarak degistirildi
- Redis'ten gelen otomatik engellemeler artik tarih bilgisi ile donuyor

## Deploy
- Backend dosyalari SFTP ile Pi'ye yuklendi
- `sudo systemctl restart tonbilaios-backend` ile yeniden baslatildi

## Not
Mevcut engelli IP'ler (fix oncesi engellenmis) hala `blocked_at=None` gosterecektir cunku eski kayitlarda `block_time` key'i yok. Yeni engellemeler dogru tarih gosterecek.
