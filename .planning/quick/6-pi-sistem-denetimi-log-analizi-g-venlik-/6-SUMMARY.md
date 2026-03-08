---
type: quick-summary
task: "Pi sistem denetimi: 6 paralel ajan ile kapsamlı güvenlik ve performans denetimi"
date: 2026-03-08
status: complete
agents: 6
duration: ~7 dakika (paralel)
---

# Pi Sistem Denetimi — Kapsamlı Rapor

## Genel Skor

| Alan | Puan | Durum |
|------|------|-------|
| Firewall / Ağ katmanı | 3/10 | KRİTİK — WAN input koruması yok |
| DDoS Koruma | 7.5/10 | İYİ — HTTP flood eksik |
| API Güvenliği | 8/10 | İYİ — XSS/CORS küçük sorunlar |
| Uygulama Güvenliği | 8/10 | İYİ — güçlü key, HTTPS, rate limit |
| Servis Kararlılığı | 5/10 | ORTA — restart döngüsü devam ediyor |
| Veritabanı | 3/10 | KRİTİK — retention yok, 1.1 GB büyüyor |
| Performans | 5/10 | ORTA — CPU0 yük dengesizliği |
| Donanım | 9/10 | İYİ — 53°C, throttling yok |
| **GENEL** | **6/10** | Acil müdahale gerektiren 5 kritik sorun |

---

## KRİTİK BULGULAR (Acil Düzeltme)

### 1. WAN Input Filter TAMAMEN EKSİK
**Kaynak:** Ajan 2 (Güvenlik Zafiyet)
**Seviye:** KRİTİK

nft `inet filter` input zincirinde `policy accept` ile eth0 (WAN) için hiçbir drop kuralı yok. İnternetten gelen her paket sisteme ulaşabiliyor — port 22, 80, 443, 8000, 5353, 53 hepsi açık.

```nft
# MEVCUT (TEHLİKELİ):
chain input { type filter hook input priority filter; policy accept; }

# OLMASI GEREKEN:
chain input {
    type filter hook input priority filter; policy drop;
    iifname "lo" accept
    ct state established,related accept
    iifname "br0" accept
    iifname "wlan0" accept
    iifname "eth0" tcp dport { 22, 80, 443, 93 } accept
    iifname "eth0" udp dport { 51820 } accept
    iifname "eth0" drop
}
```

### 2. Restart Döngüsü DEVAM EDİYOR
**Kaynak:** Ajan 1 (Log Analizi)
**Seviye:** KRİTİK

Bugün 13:57-15:11 arası **47 SIGTERM** (restart counter 161'e ulaştı). Kök neden: DDoS modülü `needs_restart: True` döndürüyor → her startup'ta yeniden restart tetikliyor.

15:15'te stabilleşmiş (nft kuralları doğru sayıya ulaşınca) ama sorun potansiyel olarak tekrarlayabilir.

### 3. Forward Chain'de `ct state established` Yanlış Sırada
**Kaynak:** Ajan 3 (Firewall Performans)
**Seviye:** KRİTİK

`ct state established,related accept` kuralı 16+ subnet kuralından SONRA geliyor. Mevcut bağlantıların her paketi gereksiz yere tüm subnet kontrollerinden geçiyor.

### 4. Firewall Başlangıç Hatası: `*` Wildcard IP
**Kaynak:** Ajan 1 (Log Analizi)
**Seviye:** YÜKSEK

Her restart'ta: `ValueError: '*' does not appear to be an IPv4 or IPv6 address`. Veritabanında bir firewall kuralında kaynak/hedef IP olarak `*` kayıtlı. Firewall başlangıç sync tamamen başarısız oluyor.

### 5. HTTP Rate Limiting ÇALIŞMIYOR
**Kaynak:** Ajan 4 (DDoS Tepki)
**Seviye:** YÜKSEK

Nginx'te `limit_req_zone` tanımlı ama hiçbir `location {}` bloğunda `limit_req` direktifi yok. HTTP flood koruması sıfır.

### 6. DB Retention Mekanizması YOK
**Kaynak:** Ajan 6 (Servis Sağlık)
**Seviye:** YÜKSEK

| Tablo | Boyut | Satır |
|-------|-------|-------|
| connection_flows | 646 MB | 2.27M |
| dns_query_logs | 318 MB | 1.33M |
| traffic_logs | 167 MB | 1.70M |
| **TOPLAM** | **1.1 GB** | **5.3M** |

Hiç silme/purge mekanizması yok. Sınırsız büyüyor.

---

## YÜKSEK SEVİYE BULGULAR

### 7. CPU0 Aşırı Yük (%87 NET_RX)
**Kaynak:** Ajan 3

CPU0: 27M NET_RX vs diğer CPU'lar toplamı 2.9M. Donanım IRQ eth0'da CPU0'a kilitli. RPS aktif ama yetersiz. conntrack insert_failed=1473 sadece CPU0'da.

### 8. Ring Buffer Çok Küçük
**Kaynak:** Ajan 3

eth0 RX ring: 512 (max 8192). br0'da 40.920 drop, wlan0'da 16.759 drop. Burst trafik kaybı.

### 9. Conntrack TCP Timeout 5 GÜN
**Kaynak:** Ajan 3, 4

`nf_conntrack_tcp_timeout_established = 432000` (5 gün). Normal: 3600-7200s (1-2 saat).

### 10. DDoS nft Set Çakışması
**Kaynak:** Ajan 1

`ddos_icmp_meter`, `ddos_syn_meter`, `ddos_udp_meter` timeout flag conflict devam ediyor.

### 11. LAN IP'leri DDoS Meter'lerde
**Kaynak:** Ajan 3

192.168.1.x cihazlar DDoS meter setlerine giriyor. Yerel cihazlar rate limit kontrolünden muaf tutulmalı.

### 12. Backend Port 8000 WAN'a Açık
**Kaynak:** Ajan 4

`0.0.0.0:8000` dinliyor. Nginx bypass edilebilir.

### 13. InnoDB Buffer Pool Yetersiz
**Kaynak:** Ajan 6

128 MB buffer pool, 1.1 GB veri. %96.5 hit rate ama 7.6M fiziksel disk okuması = SD kart yükü + %16.7 iowait.

---

## ORTA SEVİYE BULGULAR

| # | Bulgu | Kaynak |
|---|-------|--------|
| 14 | Swagger /docs internete açık | Ajan 2, 5 |
| 15 | SSH şifre auth aktif + port 22 | Ajan 2 |
| 16 | admin NOPASSWD sudo | Ajan 2 |
| 17 | .env group-writable (rw-rw-r--) | Ajan 2 |
| 18 | CORS localhost dahil | Ajan 5 |
| 19 | XSS payload sessizce kabul | Ajan 5 |
| 20 | bridge-nf-call-iptables=1 (çift işlem) | Ajan 3 |
| 21 | MariaDB deadlock (flow_tracker) | Ajan 1 |
| 22 | device_discovery autoflush bug | Ajan 1 |
| 23 | Redis fragmentasyon 2.43 | Ajan 6 |
| 24 | Conn limit per-IP 300 (çok yüksek) | Ajan 4 |
| 25 | Avahi mDNS interface kısıtlama yok | Ajan 2 |
| 26 | Saldırgan ban süresi 30dk (kısa) | Ajan 4 |
| 27 | MariaDB 20 slow query (log kapalı) | Ajan 6 |

---

## İYİ DURUM TESPİTLERİ

| Alan | Detay |
|------|-------|
| SSL/TLS | Let's Encrypt geçerli (2026-05-19), TLS 1.2/1.3 |
| Güvenlik headerları | X-Frame-Options, HSTS, CSP, XSS-Protection hepsi mevcut |
| Auth rate limiting | 5 başarısız → 15dk kilitleme, IP bazlı |
| JWT güvenliği | alg=none saldırısı reddediliyor, IP binding var |
| WebSocket auth | Token olmadan 403 Forbidden |
| Redis güvenlik | localhost-only, şifreli |
| MariaDB güvenlik | localhost-only, root kilitli |
| SQL injection | ORM koruması aktif |
| Path traversal | Korumalı |
| DDoS kernel | 5 katman aktif (ICMP/SYN/UDP/ConnLimit/Invalid) |
| Sıcaklık | 53.2°C, throttling yok |
| RAM | 2.8 GB kullanılabilir, swap sıfır |
| Disk alanı | %7 kullanım, 105 GB boş |

---

## ÖNCELİKLENDİRİLMİŞ İYİLEŞTİRME ÖNERİLERİ

### ACİL (Bu hafta yapılmalı)

| # | Eylem | Etki |
|---|-------|------|
| A1 | nft inet filter input: policy drop + eth0 port whitelist | WAN güvenliği |
| A2 | Forward chain: ct state established en başa | %80+ paket hızlanması |
| A3 | Firewall DB: `*` IP kaydını düzelt (0.0.0.0/0 veya sil) | Startup hatası |
| A4 | Nginx: location /api/ içine limit_req ekle | HTTP flood koruması |
| A5 | DB retention: 7/14/30 günlük otomatik purge | DB büyüme kontrolü |

### YÜKSEK (2 hafta içinde)

| # | Eylem | Etki |
|---|-------|------|
| B1 | Ring buffer artır: eth0 rx 4096 tx 2048 | Paket kaybı azalır |
| B2 | Conntrack timeout: 432000 → 3600 | Bellek tasarrufu |
| B3 | DDoS kurallarına `ip saddr != 192.168.1.0/24` ekle | LAN muafiyeti |
| B4 | InnoDB buffer pool: 128 → 512 MB | DB performansı |
| B5 | Backend: 127.0.0.1:8000 dinle (0.0.0.0 değil) | WAN bypass engeli |
| B6 | DDoS needs_restart kök neden analizi | Restart döngüsü |
| B7 | netdev_max_backlog: 1000 → 5000 | Burst kapasitesi |

### ORTA (1 ay içinde)

| # | Eylem | Etki |
|---|-------|------|
| C1 | Nginx: /docs, /redoc LAN-only kısıtla | API gizliliği |
| C2 | SSH: PasswordAuthentication no, port değiştir | SSH güvenliği |
| C3 | .env chmod 600 | Dosya güvenliği |
| C4 | CORS: localhost kaldır | CORS güvenliği |
| C5 | Subnet blokları nft set'e taşı (16 kural → 2) | Performans |
| C6 | Redis MEMORY PURGE | RAM tasarrufu (93 MB) |
| C7 | MariaDB slow query log aç | Performans izleme |
| C8 | Conn limit: 300 → 50-100/IP | DDoS hassasiyet |
| C9 | Saldırgan ban: 30dk → 2-24 saat | Saldırı dayanıklılığı |
| C10 | Avahi: allow-interfaces=br0,wlan0 | mDNS gizliliği |

---

## Sonuç

Sistem **fonksiyonel olarak çalışır durumda** ancak **WAN input filter eksikliği kritik bir güvenlik açığı**. DDoS koruma katmanları iyi tasarlanmış ama HTTP flood koruması eksik. Veritabanı retention mekanizmasının yokluğu uzun vadede performans ve disk sorunlarına yol açacak. Forward chain kural sıralaması ve CPU0 yük dengesizliği performansı olumsuz etkiliyor.

En acil eylem: WAN input filter + forward chain sıralama + DB retention.
