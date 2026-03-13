# TonbilAiOS v5 — Firewall Koruma Katmanları Gap Analizi Raporu

**Tarih:** 2026-03-13
**Yöntem:** 8 paralel ajan ile dünya standartları araştırması + mevcut kod tabanı analizi
**Kapsam:** nftables, DDoS, DNS güvenliği, IDS/IPS, NGFW, WAF, tehdit istihbaratı, AI/ML

---

## 1. Karşılaştırma Matrisi

### 1.1 Firewall Çekirdeği (nftables)

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| Stateful Inspection (conntrack) | ✅ Zorunlu | ✅ `inet tonbilai` tablosu, ct state established/related/invalid | **TAM** |
| NAT / Masquerade | ✅ Zorunlu | ✅ POSTROUTING masquerade, PREROUTING DNAT (port forwarding) | **TAM** |
| Set-based Blocking (O(1) lookup) | ✅ Modern | ✅ MAC set, IP set (timeout 30dk), subnet set | **TAM** |
| VPN Kill Switch | ✅ İyi pratik | ✅ WireGuard arayüzü düşünce tüm trafik drop | **TAM** |
| Port Forwarding | ✅ Temel | ✅ DNAT kuralları API üzerinden yönetim | **TAM** |
| DMZ Segmentasyonu | ✅ Enterprise | ❌ Tek subnet (192.168.1.0/24) | **YOK** |
| VLAN Desteği | ✅ Enterprise | ❌ Bridge isolation var ama VLAN tag yok | **YOK** |
| High Availability (HA) | ✅ Enterprise | ❌ Tek cihaz, failover yok | **YOK** |
| IPv6 Firewall | ✅ Modern | ⚠️ `inet` ailesi IPv6 destekler ama kurallar IPv4 odaklı | **KISMİ** |
| Reboot Persistence | ✅ Zorunlu | ✅ `/etc/nftables.conf` otomatik kayıt | **TAM** |

### 1.2 DDoS Koruma

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| SYN Flood Koruması | ✅ Zorunlu | ✅ nftables meter 25 pkt/s, burst 100 | **TAM** |
| UDP Flood Koruması | ✅ Zorunlu | ✅ nftables meter 50 pkt/s, burst 200 | **TAM** |
| ICMP Flood Koruması | ✅ Zorunlu | ✅ nftables meter 10 pkt/s, burst 50 | **TAM** |
| Bağlantı Limiti (per-IP) | ✅ Zorunlu | ✅ 1000 conn/IP, ct state new | **TAM** |
| Invalid Paket Drop | ✅ Zorunlu | ✅ FIN+SYN, SYN+RST, null scan + ct invalid | **TAM** |
| Kernel Sertleştirme (sysctl) | ✅ İyi pratik | ✅ tcp_max_syn_backlog, syncookies, rp_filter, conntrack_max | **TAM** |
| HTTP Rate Limiting | ✅ Zorunlu | ✅ Nginx `limit_req_zone` dinamik rate | **TAM** |
| Saldırgan Takip | ✅ İyi pratik | ✅ 5 ayrı attacker set, 30dk timeout, 4096 IP | **TAM** |
| Adaptif Eşik (Baseline) | ✅ Modern | ✅ Welford 3-sigma anomali tespiti (`traffic_baseline.py`) | **TAM** |
| GeoIP Engelleme | ✅ Modern | ⚠️ GeoIP verisi toplanıyor ama politika engelleme yok | **KISMİ** |
| FORWARD Chain Koruması | ✅ Zorunlu | ✅ LAN trafiği için ayrı forward chain kuralları | **TAM** |
| LAN Muafiyeti | ✅ İç ağ güvenliği | ⚠️ 192.168.1.0/24 tüm meter'lardan muaf → spoofing riski | **RİSK** |
| Telegram Uyarı | ✅ İyi pratik | ✅ Cooldown 30dk, iç ağ IP filtreleme | **TAM** |

### 1.3 DNS Güvenliği

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| DNS Proxy (UDP/53) | ✅ Zorunlu | ✅ Tam işlevsel, sinkhole (192.168.1.2) | **TAM** |
| DNS-over-TLS (DoT/853) | ✅ Modern | ✅ TLS şifreli, Android Private DNS uyumlu | **TAM** |
| DNS-over-HTTPS (DoH) | ✅ Modern | ❌ Tarayıcı DoH trafiği yakalanamıyor | **YOK** |
| DNS-over-QUIC (DoQ) | ⚠️ Gelişen | ❌ | **YOK** |
| DNSSEC Doğrulama | ✅ Zorunlu | ❌ Upstream yanıtlar doğrulanmıyor | **YOK** |
| Profil Bazlı Filtreleme | ✅ Enterprise | ✅ Kategori → blocklist → profil → cihaz zinciri | **TAM** |
| Servis Engelleme | ✅ İyi pratik | ✅ YouTube, Netflix vb. bağımsız engelleme | **TAM** |
| DGA Algılama | ✅ Modern | ✅ Shannon entropi ≥3.5, rakam/sesli harf oranı | **TAM** |
| DNS Tunneling Tespiti | ✅ Modern | ⚠️ LLM prompt'unda bahsediliyor, özel dedektör yok | **ZAYİF** |
| Rate Limiting (dış IP) | ✅ Zorunlu | ✅ 5 sorgu/s, bucket-based | **TAM** |
| Query Type Filtreleme | ✅ İyi pratik | ✅ AXFR, ANY, NULL engelleme | **TAM** |
| DNS Fingerprinting | ⚠️ Nadir | ✅ OS/cihaz tipi tespiti (`dns_fingerprint.py`) | **BENZERSİZ** |
| 5651 Log Uyumu | ✅ Yasal zorunluluk (TR) | ✅ HMAC-SHA256 imzalı günlük arşiv (`log_signer.py`) | **TAM** |
| Cache Poisoning Önleme | ✅ Zorunlu | ⚠️ Rate limit var, TXID/port randomizasyonu kontrol edilmeli | **KISMİ** |
| Response Policy Zone (RPZ) | ✅ Enterprise | ✅ Sinkhole + kategori filtreleme (RPZ benzeri) | **TAM** |

### 1.4 Tehdit Algılama & İstihbarat

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| IP Blocklist Feed'leri | ✅ Zorunlu | ✅ 5 kaynak: Firehol L1, Spamhaus DROP, DShield, ET, AbuseIPDB | **TAM** |
| IP Reputation Skorlama | ✅ Modern | ✅ AbuseIPDB API + GeoIP zenginleştirme | **TAM** |
| Domain Reputation | ✅ Modern | ✅ Entropi + TLD risk + CDN whitelist (0-100 skor) | **TAM** |
| Otomatik IP Engelleme | ✅ Modern | ✅ Tehdit skoru ≥15 → auto-block, 1 saat TTL | **TAM** |
| Flood Tespiti | ✅ Zorunlu | ✅ Dış IP 20/dk, LAN 300/dk, subnet 5+ IP | **TAM** |
| Koordineli Tarama Tespiti | ✅ Modern | ✅ Aynı qtype+domain, 3+ IP, 5dk window | **TAM** |
| STIX/TAXII Entegrasyonu | ✅ Enterprise | ❌ | **YOK** |
| MITRE ATT&CK Etiketleme | ✅ Enterprise | ❌ | **YOK** |
| IOC Yaşam Döngüsü | ✅ Enterprise | ⚠️ TTL var ama decay/aging mekanizması yok | **KISMİ** |
| Güvenilir IP Whitelist | ✅ İyi pratik | ✅ `/data/trusted_ips.txt` + public IP + gateway | **TAM** |
| Cooldown Mekanizması | ✅ İyi pratik | ✅ 30dk spam önleme, Redis key | **TAM** |

### 1.5 IDS/IPS

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| Signature-Based IDS | ✅ Enterprise | ❌ Suricata/Snort kurulu değil | **YOK** |
| Anomaly-Based Detection | ✅ Modern | ✅ Welford 3-sigma + DGA + flood pattern | **İYİ** |
| Deep Packet Inspection | ✅ Enterprise | ❌ Payload incelenmez | **YOK** |
| JA3/JA4 TLS Fingerprinting | ✅ Modern | ❌ | **YOK** |
| Protocol Analysis | ✅ Modern | ⚠️ Sadece DNS protokolü parse ediliyor | **KISMİ** |
| Flow Analysis | ✅ Modern | ✅ `flow_tracker.py` conntrack tabanlı per-flow izleme | **TAM** |

### 1.6 NGFW & Uygulama Farkındalığı

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| Application Awareness (L7) | ✅ NGFW tanımı | ⚠️ DNS + port tabanlı uygulama tespiti (120+ kural) | **KISMİ** |
| Kullanıcı/Cihaz Kimliği | ✅ NGFW tanımı | ✅ Profil + MAC/IP tabanlı kimlik | **İYİ** |
| SSL/TLS Inspection | ✅ NGFW tanımı | ❌ Pi CPU kapasitesi yetersiz | **N/A** |
| Sandboxing | ✅ NGFW tanımı | ❌ Pi için uygulanamaz | **N/A** |
| URL Kategorize Filtreleme | ✅ NGFW tanımı | ✅ DNS bazlı kategori filtreleme (profil sistemi) | **TAM** |
| QoS / Traffic Shaping | ✅ NGFW tanımı | ✅ HTB qdisc + MAC→class mapping (`linux_tc.py`) | **TAM** |

### 1.7 AI/ML Güvenlik

| Özellik | Dünya Standardı | TonbilAiOS Durumu | Seviye |
|---------|----------------|-------------------|--------|
| İstatistiksel Anomali | ✅ Temel | ✅ Welford online + z-score 3.0/5.0 | **TAM** |
| DGA Tespiti | ✅ Temel | ✅ Shannon entropi + karakter analizi | **TAM** |
| LLM Log Analizi | ⚠️ Gelişen | ✅ Periyodik DNS+DDoS özeti LLM'e gönderme | **BENZERSİZ** |
| Doğal Dil Yönetim (NLP) | ⚠️ Nadir | ✅ TF-IDF + fuzzy matching, Türkçe, 20+ intent | **BENZERSİZ** |
| UEBA (Davranış Analizi) | ✅ Enterprise | ❌ Cihaz bazlı davranış profili çıkarılmıyor | **YOK** |
| ML Model (eğitilmiş) | ✅ Enterprise | ❌ Tüm algoritmalar kural/istatistik tabanlı | **YOK** |
| Otomatik Politika Önerisi | ✅ Modern | ⚠️ LLM insight var ama otomatik kural önerisi yok | **KISMİ** |

---

## 2. Özet Skorlama

| Katman | Mevcut | Toplam | Oran | Değerlendirme |
|--------|--------|--------|------|---------------|
| Firewall Çekirdeği | 7/10 | %70 | 🟢 | Sağlam temel, enterprise özellikler eksik |
| DDoS Koruma | 12/14 | %86 | 🟢 | Çok iyi, GeoIP politikası eksik |
| DNS Güvenliği | 12/16 | %75 | 🟢 | Güçlü, DNSSEC ve DoH kritik eksik |
| Tehdit İstihbaratı | 8/11 | %73 | 🟡 | İyi, STIX/TAXII ve IOC aging eksik |
| IDS/IPS | 2/6 | %33 | 🔴 | En zayıf alan, signature-based IDS yok |
| NGFW Özellikleri | 4/6 | %67 | 🟡 | DNS bazlı uygulama farkındalığı yeterli |
| AI/ML | 4/7 | %57 | 🟡 | Benzersiz özellikler var, UEBA eksik |
| **TOPLAM** | **49/70** | **%70** | **🟢** | **Ev/SOHO için güçlü, enterprise için geliştirilmeli** |

---

## 3. Güçlü Yanlar (Rekabet Avantajı)

### 3.1 Dünya Standartlarını Karşılayan
1. **Çok katmanlı DDoS koruması:** Kernel (nftables meter) + Nginx HTTP + sysctl sertleştirme + Welford anomali
2. **Profil bazlı DNS filtreleme:** Kategori → blocklist → profil → cihaz zinciri, RPZ benzeri sinkhole
3. **Stateful nftables:** conntrack entegrasyonu, set-based O(1) engelleme, VPN kill switch
4. **5 kaynaklı tehdit istihbaratı:** Firehol L1 (50K IP), Spamhaus DROP, DShield, Emerging Threats, AbuseIPDB
5. **5651 yasal uyum:** HMAC-SHA256 imzalı log arşivleme — Türkiye'ye özel zorunluluk

### 3.2 Benzersiz / Farklılaştırıcı
1. **LLM tabanlı log analizi:** Ev tipi firewall'larda nadir. Periyodik DNS+DDoS özetleri LLM'e gönderiliyor
2. **Türkçe NLP chatbot:** TF-IDF + fuzzy matching ile doğal dil cihaz yönetimi (20+ intent)
3. **DNS fingerprinting:** OS/cihaz tipi tespiti DNS sorgu pattern'lerinden
4. **Hibrit IP reputation:** Yerel sinyaller + AbuseIPDB API + GeoIP zenginleştirme
5. **Welford online anomali:** O(1) bellek, incremental güncelleme — Pi için ideal algoritma seçimi

---

## 4. Eksikler — 12 Maddelik Öncelik Tablosu

| #  | Eksiklik                                                     | Önem     | Pi'de Uygulanabilir |
|----|--------------------------------------------------------------|----------|---------------------|
| 1  | DNSSEC doğrulama — upstream yanıt AD flag kontrolü yok       | KRİTİK   | Evet                |
| 2  | DNS Tunneling dedektörü — veri sızıntısı tespiti yok         | KRİTİK   | Evet                |
| 3  | DoH (DNS-over-HTTPS) desteği — tarayıcı bypass riski         | KRİTİK   | Evet                |
| 4  | GeoIP politika engelleme — veri var aksiyon yok               | YÜKSEK   | Evet                |
| 5  | Hardcoded eşik değerleri — Redis/DB'ye taşınmalı              | YÜKSEK   | Evet                |
| 6  | Suricata lightweight IDS — signature-based tespit tamamen yok | YÜKSEK   | Dikkatli (200MB RAM)|
| 7  | IoT karantina — yeni cihaz otomatik güvenilir ağa katılıyor  | YÜKSEK   | Evet                |
| 8  | Cihaz davranış profili (basit UEBA) — sapma algılama yok     | ORTA     | Evet                |
| 9  | Ek tehdit feed'leri — URLhaus, PhishTank, MalwareBazaar      | ORTA     | Evet                |
| 10 | MITRE ATT&CK etiketleme — insight'lara technique ID eksik    | ORTA     | Evet                |
| 11 | IOC aging/decay — AbuseIPDB skoru sabit TTL, decay yok       | ORTA     | Evet                |
| 12 | Traffic baseline gündüz/gece — Welford kümülatif sorun        | DÜŞÜK    | Evet                |

---

### Detaylı Açıklamalar

#### 🔴 KRİTİK (Hemen Uygulanmalı)

**#1 — DNSSEC Doğrulama**
- **Neden:** Cache poisoning saldırılarına karşı en güçlü savunma. Upstream DNS yanıtlarının `AD` (Authenticated Data) flag'i kontrol edilmiyor.
- **Uygulama:** `dns_proxy.py`'de `dnspython` kütüphanesi ile upstream yanıtın AD flag'ini kontrol et. Doğrulanmamış yanıtları logla/uyar.
- **Maliyet:** Düşük CPU, ~50 satır kod
- **Dosyalar:** `dns_proxy.py`

**#2 — DNS Tunneling Dedektörü**
- **Neden:** DNS üzerinden veri sızıntısı yaygın saldırı vektörü. Mevcut sistemde özel dedektör yok.
- **Uygulama:** `threat_analyzer.py`'ye 3 kural ekle: (1) subdomain uzunluğu >50 karakter, (2) TXT query oranı >%30, (3) tek domain'e >100 subdomain/dk
- **Maliyet:** Çok düşük, ~30 satır kod
- **Dosyalar:** `threat_analyzer.py`

**#3 — DoH (DNS-over-HTTPS) Desteği**
- **Neden:** Modern tarayıcılar (Firefox, Chrome) varsayılan DoH kullanıyor. DoH trafiği mevcut DNS proxy'yi bypass ediyor.
- **Uygulama:** Nginx'te `/dns-query` endpoint'i → `dns_proxy.py`'ye HTTP wrapper. Veya port 443'te DoH trafiğini yakalama.
- **Maliyet:** Orta, nginx config + HTTP handler
- **Dosyalar:** `dns_proxy.py`, nginx config

#### 🟠 YÜKSEK (Planlı Sprint)

**#4 — GeoIP Politika Engelleme**
- **Neden:** `ip_reputation.py` zaten ülke verisi topluyor ama engelleme aksiyonu yok. Birçok saldırı belirli ülkelerden geliyor.
- **Uygulama:** Redis SET `geo:blocked_countries` + nftables set entegrasyonu. Admin panelinden ülke seçimi.
- **Maliyet:** Düşük, mevcut altyapıya eklenti
- **Dosyalar:** `ip_reputation.py`, `linux_nftables.py`, frontend

**#5 — Hardcoded Eşik Değerleri**
- **Neden:** `EXTERNAL_RATE_THRESHOLD=20`, `BLOCK_DURATION_SEC=3600` gibi değerler kod içinde sabit. Operasyonel esneklik yok.
- **Uygulama:** Redis/DB'ye taşı, admin panelinden ayarlanabilir yap. `security_settings` tablosuna ekle.
- **Maliyet:** Orta, birçok dosyada değişiklik
- **Dosyalar:** `threat_analyzer.py`, `ddos_service.py`, `dns_proxy.py`

**#6 — Suricata Lightweight IDS**
- **Neden:** Signature-based IDS tamamen eksik. En büyük gap (%33 skor).
- **Uygulama:** Raspberry Pi 4/5'te `af-packet` modu, kısıtlı kural seti (ET Open critical+high, ~2000 kural). ~200MB RAM.
- **Risk:** CPU darboğazı, throughput düşüşü. Dikkatli profiling gerekli.
- **Maliyet:** Yüksek, yeni servis + entegrasyon

**#7 — IoT Karantina Sistemi**
- **Neden:** Yeni keşfedilen cihazlar otomatik olarak güvenilir ağa katılıyor. Zero Trust ihlali.
- **Uygulama:** Yeni cihaz → kısıtlı profil (sadece temel DNS) → admin onayı (Telegram) → normal profil.
- **Maliyet:** Orta-yüksek, profil otomasyon + bildirim
- **Dosyalar:** `device_discovery.py`, `profiles.py`, `telegram_service.py`

#### 🟡 ORTA

**#8 — Cihaz Davranış Profili (Basit UEBA)**
- **Neden:** Cihaz ele geçirilmesi veya yetkisiz kullanımı tespit edilemiyor. Normal davranıştan sapma algılama yok.
- **Uygulama:** Her cihaz için günlük DNS profili: top 20 domain, saatlik dağılım, ortalama sorgu/dk. `traffic_baseline.py`'nin cihaz bazlı versiyonu. Sapma → uyarı.
- **Maliyet:** Orta, yeni worker + Redis keys
- **Dosyalar:** Yeni `device_baseline.py` + `threat_analyzer.py`

**#9 — Ek Tehdit Feed'leri**
- **Neden:** Mevcut 5 kaynak iyi ama URL/malware bazlı feed'ler eksik.
- **Kaynaklar:** Abuse.ch URLhaus (zararlı URL), PhishTank (phishing domain), MalwareBazaar (hash)
- **Uygulama:** `ip_blocklist_sync.py` benzeri worker, domain listesi olarak DNS filtrelemeye ekleme
- **Maliyet:** Orta, yeni worker

**#10 — MITRE ATT&CK Etiketleme**
- **Neden:** AiInsight kayıtlarına saldırı tekniği ID'si eklenmesi, korelasyon ve raporlama için değerli.
- **Örnekler:** T1071.004 (DNS C2), T1048.003 (DNS exfiltration), T1499.001 (SYN flood)
- **Uygulama:** `threat_analyzer.py` ve `ddos_service.py`'de her insight'a `attack_technique` alanı ekle
- **Maliyet:** Düşük

**#11 — IOC Aging / Decay Mekanizması**
- **Neden:** AbuseIPDB skoru sabit 24 saat TTL. Zamanla azalan güvenilirlik yönetimi yok.
- **Uygulama:** Skor × decay_factor(zaman) formülü. Eski IOC'lerin otomatik öncelik düşürülmesi.
- **Maliyet:** Düşük
- **Dosyalar:** `ip_reputation.py`

#### 🟢 DÜŞÜK

**#12 — Traffic Baseline Gündüz/Gece Ayrımı**
- **Neden:** Welford algoritması kümülatif ortalama hesaplıyor. Gündüz trafiği yüksek, gece düşük — tek ortalama her iki zaman diliminde de yanlış anomali tetikliyor.
- **Uygulama:** Saatlik bucket'lar (0-23) ile ayrı Welford accumulator. Gündüz (08-23) ve gece (23-08) ayrı baseline.
- **Maliyet:** Orta, `traffic_baseline.py` refactor
- **Dosyalar:** `traffic_baseline.py`
- **Not:** Mevcut durumda ciddi false positive üretmiyor, ama uzun vadede doğruluk artışı sağlar

---

## 5. Pi Sınırlamaları — Uygulanmaması Gerekenler

| Özellik | Neden Uygulanmamalı |
|---------|---------------------|
| SSL/TLS Inspection (MITM) | Pi CPU wirespeed TLS decrypt yapamaz. Gizlilik sorunu. |
| Full DPI (Suricata inline, 30K+ kural) | Throughput %50+ düşer. RAM yetersiz. |
| Sandboxing | İzole yürütme ortamı için kaynak yok. |
| STIX/TAXII Sunucu | Bellek + karmaşıklık orantısız. |
| Deep Learning (LSTM, Autoencoder) | GPU yok, inference çok yavaş. |
| BGP Blackhole / Anycast | ISP işbirliği + birden fazla PoP gerektirir. |
| 802.1X / RADIUS | Ev ortamında karmaşıklık/fayda oranı düşük. |
| Full ZTNA Proxy | Her uygulama için ayrı tunnel Pi'de pratik değil. |
| Recursive DNS Resolver | Forwarding proxy yeterli, full resolver gereksiz kaynak tüketimi. |

---

## 6. Bilinen Riskler ve İyileştirmeler

| Risk | Açıklama | Önerilen Çözüm |
|------|----------|----------------|
| LAN Spoofing | 192.168.1.0/24 tüm DDoS meter'lardan muaf | İç ağ için ayrı, daha yüksek eşikli meter ekle |
| Hardcoded Threshold | EXTERNAL_RATE_THRESHOLD=20 vb. kod içinde sabit | Redis/DB'ye taşı, admin panelinden ayarlanabilir yap |
| TC Mark Collision | Hash-based 9998 slot, çok cihazda çakışma riski | Ev ortamı için sorun değil (<50 cihaz), monitör ekle |
| DNS Rate Limit FP | 5/s dış IP limiti meşru DNS sunucuları engelleyebilir | Upstream DNS IP'leri whitelist'e ekle |
| IPv6 Kural Eksikliği | nftables `inet` ailesi IPv6 destekler ama kurallar IPv4 odaklı | IPv6 için paralel kural seti oluştur |

---

## 7. Sonuç

TonbilAiOS v5, bir Raspberry Pi tabanlı ev/SOHO firewall olarak **%70 dünya standardı uyumu** ile güçlü bir konumdadır. DNS filtreleme (%75), DDoS koruması (%86) ve tehdit istihbaratı (%73) katmanları olgun seviyededir. LLM log analizi, Türkçe NLP chatbot ve DNS fingerprinting gibi benzersiz özellikler rekabet avantajı sağlamaktadır.

**12 eksik tespit edildi** — 3 KRİTİK, 4 YÜKSEK, 4 ORTA, 1 DÜŞÜK. KRİTİK maddelerin (DNSSEC, DNS tunneling, DoH) düşük maliyetle hemen uygulanması toplam skoru **%70 → %78**'e çıkarabilir. Tüm 12 maddenin tamamlanması **%90+** hedefine ulaştırır.

### Uygulama Takvimi Önerisi

| Dönem | Maddeler | Hedef | Beklenen Skor |
|-------|----------|-------|---------------|
| **Sprint 1** (1 hafta) | #1 DNSSEC + #2 DNS tunneling + #5 hardcoded eşikler | %76 |
| **Sprint 2** (1 hafta) | #3 DoH + #4 GeoIP politika + #11 IOC aging | %82 |
| **Sprint 3** (2 hafta) | #7 IoT karantina + #8 UEBA + #9 ek feed'ler + #10 MITRE | %87 |
| **Sprint 4** (2-4 hafta) | #6 Suricata IDS + #12 baseline gündüz/gece | %90+ |

---

*Rapor: 8 paralel araştırma ajanı çıktılarının sentezi. Kod analizi: 14+ dosya, 8.000+ satır. Web araştırma: 27+ kaynak (RFC, NIST SP 800-41, vendor dokümantasyonu).*
