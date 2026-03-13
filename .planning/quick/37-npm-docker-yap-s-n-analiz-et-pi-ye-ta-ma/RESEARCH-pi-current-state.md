# Pi Mevcut Durum Raporu (192.168.1.2)

**Tarih:** 2026-03-13 17:19 UTC+3
**Uptime:** 1 gun, 3 saat 52 dakika
**Load Average:** 0.20, 0.08, 0.02

---

## 1. Donanim

| Ozellik | Deger |
|---------|-------|
| Model | Raspberry Pi 5 Model B Rev 1.1 |
| CPU | ARM Cortex-A76 (4 cekirdek), aarch64, BogoMIPS 108 |
| Kernel | Linux 6.12.62+rpt-rpi-2712 (PREEMPT, Debian) |
| RAM | 4 GB toplam, 1.6 GB kullanilan, 2.3 GB kullanilabilir |
| Swap | 2 GB (kullanilmiyor) |
| Disk | 118 GB SD kart, 7.7 GB kullanilan (%7), 105 GB bos |
| Boot | 510 MB, 66 MB kullanilan |

---

## 2. Nginx Yapisi

### Versiyon
- **Nginx 1.26.3-3+deb13u2** (Debian paketi, arm64)
- `certbot-nginx` eklentisi kurulu

### Ana Konfigurasyon (`/etc/nginx/nginx.conf`)
- `worker_processes auto` (4 worker, CPU sayisina gore)
- `worker_cpu_affinity auto`
- `server_tokens off`
- Gzip acik
- SSL: TLSv1.2 + TLSv1.3
- Include: `/etc/nginx/conf.d/*.conf` ve `/etc/nginx/sites-enabled/*`

### Site Konfigurasyonlari

**Aktif:** Sadece `/etc/nginx/sites-enabled/tonbilaios`

#### Server 1: Ana Uygulama (Panel + API)
- **Dinlenen portlar:** 80, 93, 443 (SSL)
- **Server names:** `guard.tonbilx.com`, `wall.tonbilx.com`, `192.168.1.2`, `localhost`
- **Root:** `/opt/tonbilaios/frontend/dist`
- **SSL sertifikasi:** Let's Encrypt (`/etc/letsencrypt/live/wall.tonbilx.com/`)
- **API proxy:** `http://127.0.0.1:8000` (uvicorn backend)
- **WebSocket destegi:** Evet (`Upgrade` + `Connection` header)
- **Guvenlik basliklari:** X-Frame-Options, CSP, HSTS, XSS-Protection
- **Login rate limit:** `ddos_limit` zone, burst=5
- **API rate limit:** `ddos_limit` zone, burst=60
- **Swagger/docs:** Sadece 192.168.1.0/24 ve 127.0.0.1 erisebilir
- **SPA fallback:** `try_files $uri $uri/ /index.html`
- **Statik cache:** JS/CSS/img 30 gun

#### Server 2: Block Page (DNS Engelleme, catch-all)
- **Dinlenen portlar:** 80 (default_server), 443 SSL (default_server)
- **Server name:** `_` (herhangi bir hostname)
- **SSL sertifikasi:** Self-signed (`/etc/tonbilaios/blockpage-cert.pem`)
- HTTPS istekleri `http://192.168.1.2/blocked.html?domain=$host` adresine 302 redirect
- Block sebebi API: `/api/v1/dns/blockpage` (CORS acik, auth gerektirmez)

### conf.d Dosyalari
- **`/etc/nginx/conf.d/tonbilaios-ddos.conf`:** Rate limiting zone tanimlaması
  - `limit_req_zone $binary_remote_addr zone=ddos_limit:10m rate=30r/s`

### Sites-available (aktif olmayan)
- `default` (standart Debian default, aktif degil)
- `tonbilaios.bak` (yedek)

---

## 3. Backend Servisi

| Ozellik | Deger |
|---------|-------|
| Servis | `tonbilaios-backend.service` |
| Durum | **active (running)** |
| PID | 260363 |
| Runtime | 2+ saat |
| Komut | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` |
| Tasks | 16 |
| CPU | 6 dk 29 sn (toplam) |
| Drop-in | `/etc/systemd/system/tonbilaios-backend.service.d/99-resilience.conf` |

---

## 4. Docker Durumu

**Docker KURULU DEGIL.** Pi uzerinde Docker yok. Tum servisler native calisıyor.

---

## 5. Acik Portlar

| Port | Servis | Proses |
|------|--------|--------|
| 22 | SSH | sshd |
| 80 | HTTP | nginx (4 worker + master) |
| 93 | HTTP (alternatif) | nginx |
| 443 | HTTPS | nginx |
| 853 | DoT (DNS over TLS) | uvicorn |
| 3306 | MariaDB | mariadbd (sadece 127.0.0.1) |
| 6379 | Redis | redis-server (sadece 127.0.0.1 + ::1) |
| 8000 | FastAPI/uvicorn | uvicorn |

---

## 6. Calisan Servisler (24 adet)

| Servis | Aciklama |
|--------|----------|
| tonbilaios-backend | FastAPI ana uygulama |
| nginx | Web sunucu + reverse proxy |
| mariadb | MariaDB 11.8.3 veritabani |
| redis-server | Redis cache |
| dnsmasq | DHCP + DNS (upstream) |
| hostapd | WiFi Access Point |
| fail2ban | Brute-force koruma |
| ssh | OpenSSH sunucu |
| NetworkManager | Ag yonetimi |
| bluetooth | Bluetooth servisi |
| avahi-daemon | mDNS/DNS-SD |
| ModemManager | Modem yonetimi |
| cron | Zamanlanmis gorevler |
| irqbalance | IRQ dagilimi |
| systemd-timesyncd | NTP senkronizasyon |
| wpa_supplicant | WiFi WPA |

---

## 7. Firewall (nftables) Kurallari

### inet filter
- **input chain:**
  - Loopback ve br0/wlan0 kabul
  - Established/related kabul
  - WAN (eth0) sadece: TCP 22, 80, 93, 443 + UDP 51820 (WireGuard)
  - WAN'dan DoT (853) ve uvicorn (8000) ENGELLENDI
  - WAN default: DROP

- **forward chain:** Established/related kabul, policy accept
- **output chain:** policy accept

### bridge filter
- eth1↔eth0 bridge izolasyonu (LAN-WAN arasi drop)
- Accounting sayaclari (1.6 milyar paket, 2.4 TB)

### inet nat
- **prerouting:**
  - UDP/TCP 53 → port 53'e redirect (DNS yakalama)
  - TCP 853 → port 853'e redirect (DoT yakalama)
- **postrouting:**
  - VPN (10.13.13.0/24) masquerade
  - LAN (192.168.1.0/24) dis trafik masquerade

### inet tonbilai
- `blocked_macs` seti (bos)
- `blocked_ips` seti (yuzlerce IP, 365 gun timeout - IP reputation engelleme)

---

## 8. Ozet ve Onemli Bulgular

1. **Pi 5 Model B** - 4 GB RAM, 4 cekirdek ARM Cortex-A76, 118 GB SD kart
2. **Docker YOK** - Tum servisler native systemd ile calisiyor
3. **Nginx 1.26.3** tek site konfigurasyon dosyasi ile calisiyor (`tonbilaios`)
4. **Iki server blogu:** Ana panel (80/93/443) + Block page (default_server)
5. **Let's Encrypt SSL** wall.tonbilx.com icin aktif, block page self-signed
6. **Backend** tek worker ile uvicorn (port 8000), nginx reverse proxy arkasindan
7. **DNS guvenlik zinciri tam:** DNS redirect (53) + DoT redirect (853) + WAN'dan engelleme
8. **IP reputation sistemi aktif:** Yuzlerce IP 365 gun engelli
9. **Kaynak durumu iyi:** RAM %40, Disk %7, Load ~0.20
10. **Port 93** ek erisim noktasi olarak dinleniyor (muhtemelen alternatif HTTP)
11. **WireGuard VPN** aktif (UDP 51820 WAN'dan acik, 10.13.13.0/24 subnet)
12. **MariaDB 11.8.3** ve **Redis** sadece localhost'tan erisilebilir (guvenli)
