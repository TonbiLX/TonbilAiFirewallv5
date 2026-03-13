# NPM (Nginx Proxy Manager) Docker Yapi Analiz Raporu

**Tarih:** 2026-03-13
**Hedef:** 192.168.1.4 (TonbiLX-N0)
**Analiz Yontemi:** SSH (Paramiko ProxyJump) ile uzaktan komut calistirma

---

## 1. Genel Bakis

| Bilgi | Deger |
|-------|-------|
| **NPM Versiyonu** | 2.14.0 |
| **Build Commit** | 84fb2729 |
| **Build Tarihi** | 2026-02-17 05:42:59 UTC |
| **Docker Image** | jc21/nginx-proxy-manager:latest |
| **Container ID** | e253361328226ccd... |
| **Container Adi** | npm |
| **Durum** | Running (28+ saat) |
| **Olusturulma** | 2026-02-17T06:25:21Z |
| **Son Baslatma** | 2026-03-12T10:29:14Z |
| **Restart Policy** | always (MaxRetry: 0) |
| **OpenResty** | 1.27.1.2 |
| **CrowdSec Bouncer** | 0.1.7 |
| **Node.js** | Production mode |

---

## 2. Container Konfigurasyonu

### Port Binding

| Container Port | Host Port | Protokol |
|---------------|-----------|----------|
| 80 | 0.0.0.0:80 | TCP (HTTP) |
| 81 | 0.0.0.0:81 | TCP (Admin Panel) |
| 443 | 0.0.0.0:443 | TCP (HTTPS) |

### Volume Mount'lar

| Host Path | Container Path | Aciklama |
|-----------|---------------|----------|
| `/data/compose/2/data` | `/data` | Ana veri dizini |
| `/data/compose/2/data/letsencrypt` | `/etc/letsencrypt` | SSL sertifikalari |
| `/data/compose/2/config.json` | `/app/config/production.json` | Uygulama config |

> **Not:** production.json dosyasi bos (icerik yok).

### Network

| Ozellik | Deger |
|---------|-------|
| Network Mode | `npm_npm-network` |
| Network Driver | bridge |
| Network ID | c4023be81252 |

### Ortam Degiskenleri

```
NODE_ENV=production
NPM_BUILD_VERSION=2.14.0
NPM_BUILD_COMMIT=84fb2729
NPM_BUILD_DATE=2026-02-17 05:42:59 UTC
NODE_OPTIONS=--openssl-legacy-provider
OPENRESTY_VERSION=1.27.1.2
CROWDSEC_OPENRESTY_BOUNCER_VERSION=0.1.7
S6_BEHAVIOUR_IF_STAGE2_FAILS=1
S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0
S6_KILL_FINISH_MAXTIME=10000
S6_VERBOSITY=1
SUPPRESS_NO_CONFIG_WARNING=1
```

---

## 3. Kaynak Kullanimi

| Metrik | Deger |
|--------|-------|
| **CPU** | %1.65 |
| **Bellek** | 0B / 0B (sinir yok) |
| **Network I/O** | 142GB / 142GB |
| **Block I/O** | 240MB / 0B |
| **Disk (/data)** | 204MB |

### Host Makine

- **Uptime:** 1 gun, 3 saat 54 dakika
- **Load Average:** 0.36, 0.42, 0.33

---

## 4. Proxy Host Listesi (25 Aktif Config)

API'den alinan toplam proxy host sayisi ve detaylari:

### Aktif Proxy Host'lar

| # | Domain | Hedef IP:Port | SSL | Exploit Block | WebSocket | HTTP/2 | Config |
|---|--------|--------------|-----|---------------|-----------|--------|--------|
| 1 | a.previous.social | 192.168.1.4:9553 (https) | Cert #61 | Hayir | Evet | Evet | 52.conf |
| 2 | bazarr.tonbilx.com | 192.168.1.5:6767 | Cert #45 | Evet | Evet | Hayir | 39.conf |
| 3 | dns.tonbilx.com | 192.168.1.7:5380 | Cert #52 | Evet | Evet | Hayir | 46.conf |
| 4 | docker.tonbil.com | 192.168.1.4:9443 (https) | Cert #2 | Evet | Evet | Hayir | 2.conf |
| 5 | file-n0.tonbilx.com | 192.168.1.4:3970 | Cert #54 | Evet | Evet | Hayir | 48.conf |
| 6 | file.tonbilx.com | 192.168.1.5:5151 | Cert #55 | Evet | Evet | Hayir | 49.conf |
| 7 | guard.tonbilx.com | 192.168.1.2:8000 | Cert #58 | Hayir | Evet | Evet | **51.conf (BOS!)** |
| 8 | home.tonbilx.com | 192.168.1.4:8123 | Cert #19 | Evet | Evet | Hayir | 13.conf |
| 9 | immich.tonbilx.com | 192.168.1.4:2283 | Cert #28 | Evet | Evet | Hayir | 33.conf |
| 10 | luci.tonbilx.com | 192.168.1.9:8765 | Cert #53 | Hayir | Evet | Evet | 53.conf |
| 11 | n0.tonbilx.com | 192.168.1.4:8081 | Cert #27 | Evet | Evet | Hayir | 32.conf |
| 12 | nas-n0.tonbilx.com | 192.168.1.4:5001 (https) | Cert #17 | Evet | Evet | Hayir | 5.conf |
| 13 | nas.tonbil.com | 192.168.1.9:5001 (https) | Cert #35 | Evet | Evet | Hayir | 40.conf |
| 14 | nas.tonbilx.com | 192.168.1.5:5001 (https) | Cert #18 | Evet | Evet | Hayir | 1.conf |
| 15 | nextcloud.tonbil.com | 192.168.1.4:8081 | Cert #33 | Evet | Evet | Evet | 4.conf |
| 16 | ombi.tonbilx.com | 192.168.1.5:3579 | Cert #42 | Evet | Evet | Hayir | 36.conf |
| 17 | photo-n0.tonbilx.com | 192.168.1.4:2342 | Cert #21 | Evet | Evet | Hayir | 42.conf |
| 18 | photo.tonbilx.com | 192.168.1.5:2342 | Cert #22 | Evet | Evet | Hayir | 43.conf |
| 19 | pi.tonbil.com | 192.168.1.2:80 | Cert #25 | Evet | Evet | Hayir | 35.conf |
| 20 | prowlarr.tonbilx.com | 192.168.1.5:9696 | Cert #47 | Evet | Evet | Hayir | 47.conf |
| 21 | radarr.tonbilx.com | 192.168.1.5:7878 | Cert #44 | Evet | Evet | Hayir | 38.conf |
| 22 | sonarr.tonbilx.com | 192.168.1.5:8989 | Cert #41 | Evet | Evet | Hayir | 41.conf |
| 23 | storage-n0.tonbilx.com | 192.168.1.4:5001 (https) | Cert #37 | Evet | Evet | Hayir | 44.conf |
| 24 | tonbilx.com | 192.168.1.4:8081 | Cert #29 | Evet | Evet | Hayir | 45.conf |
| 25 | w.previous.social | 192.168.1.4:4000 | Cert #63 | Hayir | Evet | Evet | 54.conf |

### Hedef IP Dagilimi

| Hedef IP | Sayi | Aciklama |
|----------|------|----------|
| 192.168.1.4 (N0 - bu makine) | 11 | Nextcloud, Portainer, Immich, PhotoPrism, FileBrowser vb. |
| 192.168.1.5 (N2 - NAS) | 8 | Sonarr, Radarr, Bazarr, Prowlarr, Ombi, NAS, Photo vb. |
| 192.168.1.2 (Pi - Firewall) | 2 | pi.tonbil.com, guard.tonbilx.com |
| 192.168.1.7 | 1 | dns.tonbilx.com (DNS Server) |
| 192.168.1.9 (N2-NAS alt) | 2 | nas.tonbil.com, luci.tonbilx.com |

---

## 5. KRITIK BULGU: guard.tonbilx.com (51.conf BOS)

**guard.tonbilx.com** icin NPM'de proxy host kaydi mevcut (ID: 51) ancak **51.conf dosyasi olusturulmamis/bos**.

API'den alinan bilgi:
- **Forward:** 192.168.1.2:8000 (http)
- **SSL:** Cert #58 (Guard.tonbilx.com, gecerli: 2026-05-27)
- **WebSocket:** Aktif
- **HTTP/2:** Aktif
- **Block Exploits:** Hayir
- **Advanced Config:** Bos

Bu, guard.tonbilx.com'a gelen isteklerin NPM tarafindan proxy'lenmedigini ve dolayisiyla TonbilAiOS web arayuzune NPM uzerinden dis erisimin **CALISMAYACAGINI** gosterir.

> **Sebep:** NPM bazen proxy host config dosyasini olusturamaz. nginx reload/restart gerekebilir veya proxy host'un NPM admin panelinden disable/enable yapilmasi gerekir.

---

## 6. SSL Sertifikalari

### Toplam Sertifika Sayisi

Let's Encrypt dizininde 62 sertifika klasoru mevcut (npm-1 ile npm-66 arasi, bazi numaralar eksik).

### Onemli Sertifikalar

| Cert ID | Domain | Son Gecerlilik | Durum |
|---------|--------|---------------|-------|
| #58 | Guard.tonbilx.com | 2026-05-27 | Gecerli |
| #62 | Guard.tonbilx.com | 2026-05-21 | Gecerli (yedek) |
| #65 | Guard.tonbilx.com | 2026-04-28 | Gecerli (yedek) |
| #52 | dns.tonbilx.com | - | **HATA (Rate Limited)** |
| #59 | a.previous.social | 2026-05-02 | Gecerli |
| #33 | nextcloud.tonbil.com | - | Gecerli (otomatik yenileme) |

### SSL Yenileme Hatasi

`dns.tonbilx.com` (Cert #52) icin Let's Encrypt **rate limit** hatasi alinmis:
```
urn:ietf:params:acme:error:rateLimited :: Your account is temporarily prevented
from requesting certificates for dns.tonbilx.com
```
Unpause linki: https://portal.letsencrypt.org/sfe/v1/unpause?jwt=...

> **Not:** guard.tonbilx.com icin 3 ayri sertifika (58, 62, 65) olusturulmus. Bu muhtemelen NPM'nin config sorunlari nedeniyle tekrarlanan SSL olusturma girisimleri.

---

## 7. Nginx Ana Konfigurasyonu

### Onemli Ayarlar

| Ayar | Deger |
|------|-------|
| Worker Processes | auto |
| Client Max Body Size | 2000m (2GB) |
| Keepalive Timeout | 90s |
| Proxy Connect/Send/Read Timeout | 90s |
| Server Names Hash Bucket Size | 1024 |
| Gzip | on |
| Cache | off (varsayilan) |
| Real IP Header | X-Real-IP |

### Include Yapisi

```
/etc/nginx/nginx.conf
  ├── /etc/nginx/modules/*.conf          # Dinamik moduller
  ├── /data/nginx/custom/root_top[.]conf # Ozel root config
  ├── /data/nginx/custom/events[.]conf   # Ozel events
  ├── /data/nginx/custom/http_top[.]conf # Ozel HTTP ust
  ├── /etc/nginx/conf.d/*.conf           # NPM dahili config
  ├── /data/nginx/default_host/*.conf    # Varsayilan host
  ├── /data/nginx/proxy_host/*.conf      # Proxy host'lar (25 dosya)
  ├── /data/nginx/redirection_host/*.conf # Yonlendirmeler
  ├── /data/nginx/dead_host/*.conf       # Olmus host'lar
  ├── /data/nginx/temp/*.conf            # Gecici config
  ├── /data/nginx/custom/http[.]conf     # Ozel HTTP alt
  └── stream { ... }                     # TCP/UDP stream
```

### Real IP Trust

```
set_real_ip_from 10.0.0.0/8;
set_real_ip_from 172.16.0.0/12;    # Docker subnet dahil
set_real_ip_from 192.168.0.0/16;
include conf.d/include/ip_ranges.conf;  # CDN IP araliklari
real_ip_header X-Real-IP;
real_ip_recursive on;
```

---

## 8. Disk Kullanimi

### Container Icerisi (/data)

| Dizin | Aciklama |
|-------|----------|
| `/data/` | **204MB** toplam |
| `/data/nginx/proxy_host/` | 25 config dosyasi |
| `/data/nginx/stream/` | Bos |
| `/data/nginx/custom/` | Bos |
| `/data/letsencrypt/` | SSL sertifikalari (62 klasor) |
| `/data/logs/` | Erisim ve hata loglari |

### Host Disk

Host makine disk bilgisi alinmistir (df -h ciktisi).

---

## 9. Docker Compose

Docker compose dosyasi (`/data/compose/2/docker-compose.yml`) **bulunamadi**. Bu, NPM container'inin muhtemelen Portainer uzerinden olusturuldugunu gosterir (Portainer compose ID: 2).

Portainer compose verisi Docker container'in inspect ciktisindaki bind mount'lardan anlasilabilir:
```
/data/compose/2/data → /data
/data/compose/2/data/letsencrypt → /etc/letsencrypt
/data/compose/2/config.json → /app/config/production.json
```

---

## 10. Ayni Host'taki Diger Container'lar

192.168.1.4 uzerinde NPM disinda su container'lar calisir:

### Aktif (Running)

| Container | Image | Portlar |
|-----------|-------|---------|
| nextcloud-app-1 | nextcloud:latest | 8081→80 |
| filebrowser | filebrowser/filebrowser:latest | 3970→80 |
| portainer-agent | portainer/agent:latest | 9001→9001 |
| portainer | portainer/portainer-ce:latest | 8000, 9443 |
| redis | redis:alpine | 6379 (ic) |
| photoprism-mariadb-1 | mariadb:10.11 | 3306 (ic) |
| db | mariadb:latest | 3306→3306 |
| nextcloud-db | mariadb:latest | 3306 (ic) |
| watchtower | containrrr/watchtower | 8080 (ic) |

### Durdurulmus (Exited)

| Container | Image | Durum |
|-----------|-------|-------|
| photoprism-photoprism-1 | photoprism:latest | 2 ay once |
| mastodon + db + redis | linuxserver/mastodon | 5 ay once |
| wireguard | linuxserver/wireguard | 11 ay once |
| netdata, prometheus, grafana, node-exporter, cadvisor, code-server | cesitli | 14 ay once |

### Docker Network'ler

28 bridge network mevcut. NPM kendi `npm_npm-network` bridge'ini kullaniyor.

---

## 11. Oneriler ve Aksiyon Gerektiren Noktalar

### KRITIK

1. **guard.tonbilx.com 51.conf BOS** - NPM proxy host config dosyasi olusturulmamis. Bu durumda guard.tonbilx.com uzerinden TonbilAiOS web arayuzune dis erisim **calismaz**. Cozum:
   - NPM admin panelinden (192.168.1.4:81) proxy host #51'i disable edip tekrar enable etmek
   - Veya `docker exec npm nginx -s reload` ile nginx'i yeniden yuklemek
   - Ya da API uzerinden proxy host'u guncellemek

2. **dns.tonbilx.com SSL Rate Limit** - Let's Encrypt rate limit'e takilmis. Unpause linki ziyaret edilmeli.

### UYARI

3. **3x Guard.tonbilx.com sertifikasi** - Cert #58, #62, #65 hepsi ayni domain icin. Gereksiz sertifika olusumu var.

4. **production.json BOS** - NPM config dosyasi hicbir ozel ayar icermiyor. Varsayilan degerler kullaniliyor.

5. **Bellek siniri YOK** - Container icin memory limit belirlenmemis (0B / 0B). OOM riski.

6. **Block exploits KAPALI** - guard.tonbilx.com, a.previous.social, luci.tonbilx.com icin exploit bloklama kapali.

### BILGI

7. **142GB Network I/O** - NPM container'i ciddi miktarda trafik islemis.
8. **Watchtower aktif** - Docker image'leri otomatik guncellenebilir.
9. **Durdurulmus container'lar** - 6 container 14+ aydir durdurulmus, temizlenebilir.

---

## 12. guard.tonbilx.com DoH Proxy Icin Ozel Not

CLAUDE.md'de belirtilen "NPM guard.tonbilx.com DoH proxy config (51.conf bos, generate edilmiyor)" sorunu **dogrulanmistir**.

Mevcut NPM kaydi:
- Forward: `http://192.168.1.2:8000`
- SSL: Cert #58 (gecerli)
- 51.conf: **MEVCUT DEGIL** (nginx tarafindan yuklenmiyor)

Bu sorunu cozmek icin:
1. NPM API uzerinden proxy host #51'i disable/enable yapmak
2. Veya ozel bir nginx config dosyasini `/data/nginx/custom/` altina elle yazmak
3. Veya tamamen yeni bir proxy host olusturmak (eski #51'i silip)

---

*Rapor Sonu*
