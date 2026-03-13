# Firewall'larda Nginx Kullanimi ve NPM Pi'ye Tasima Analizi

**Tarih:** 2026-03-13
**Kapsam:** Modern firewall'larda reverse proxy yonetimi, NPM alternatifleri, Pi'ye tasima fayda/zarar analizi

---

## 1. Firewall'larda Nginx / Reverse Proxy Kullanimi

### OPNsense

OPNsense, Nginx'i **plugin olarak** sunar. Temel ozellikler:
- **NAXSI WAF** entegrasyonu: SQL injection, XSS gibi web saldirilarini tespit eder
- Reverse proxy, SSL termination, upstream load balancing
- GUI uzerinden yapilandirma (Services > Nginx)
- Let's Encrypt entegrasyonu (ACME plugin ile)

OPNsense'in kendi paket filtresi (pf) uygulama katmani protokollerini anlayamaz; bu nedenle reverse proxy HTTP/HTTPS seviyesinde erisim kontrolu saglar.

**Kaynak:** [OPNsense Nginx Reverse Proxy Tutorial](https://forum.opnsense.org/index.php?topic=19305.0), [OPNsense Reverse Proxy Docs](https://docs.opnsense.org/manual/reverse_proxy.html)

### pfSense

pfSense iki reverse proxy secenegi sunar:
- **HAProxy** paketi (resmi, en cok kullanilan)
- **Nginx** paketi (daha az yaygin ama mevcut)
- Squid paketi (forward proxy + caching)

pfSense toplulugunun cogunlugu HAProxy tercih eder cunku pfSense'in GUI entegrasyonu HAProxy icin daha olgun.

**Kaynak:** [pfSense + Nginx Konfigurasyonu](https://www.egirna.com/blog/news-2/configuring-allowing-inbound-traffic-using-port-forwarding-with-nginx-on-pfsense-firewall-1)

### IPFire

IPFire, yerlesik reverse proxy sunmaz. Kullanicilar genellikle:
- Nginx'i manuel olarak kurar
- Veya DMZ'deki ayri bir sunucuda reverse proxy calistirir

### Genel Egilim

Modern firewall'lar reverse proxy'yi **opsiyonel plugin** olarak sunar. Asil firewall fonksiyonu (paket filtreleme, NAT, IDS/IPS) ayridir; reverse proxy uygulama katmani korumasi icin eklenir.

---

## 2. HAProxy vs Nginx: Firewall Ortaminda Karsilastirma

| Kriter | HAProxy | Nginx |
|--------|---------|-------|
| **Tasarim Amaci** | Pure load balancer / proxy | Web sunucu + proxy |
| **Ham Performans** | Baglanti basina %10-15 daha hizli | Web trafiginde yeterli |
| **Protokol Destegi** | TCP, HTTP, SMTP, IMAP, WebSocket | HTTP/HTTPS (TCP stream modulu ile diger) |
| **SSL Termination** | Var (ama Nginx kadar olgun degil) | Cok olgun, OCSP stapling, HTTP/2 |
| **Web Sunucu** | Yok | Var (statik dosya servisi) |
| **WAF Entegrasyonu** | Sinirli | ModSecurity, NAXSI |
| **Monitoring** | 61 metrik, detayli status page | Temel status modulu |
| **Konfigürasyon** | Daha zor, CLI odakli | Daha kolay, basit config dosyalari |
| **Firewall Tercihi** | pfSense varsayilan | OPNsense plugin |

**Sonuc:** Firewall ortaminda her ikisi de kullanilir. HAProxy saf yuk dengeleme icin ustun; Nginx hem web sunucu hem proxy ihtiyaci olanlarda (bizim senaryomuz gibi) daha uygun.

**Kaynaklar:** [NGINX vs HAProxy](https://www.openlogic.com/blog/nginx-vs-haproxy), [HAProxy vs Nginx Performance](https://last9.io/blog/haproxy-vs-nginx-performance/), [HAProxy vs Nginx KeyCDN](https://www.keycdn.com/support/haproxy-vs-nginx)

---

## 3. NPM Alternatifleri Karsilastirma

| Cozum | Artilari | Eksileri | Pi Uygunlugu |
|-------|----------|----------|--------------|
| **NPM (Docker)** | GUI yonetim paneli, kolay SSL, Access Lists, basit kurulum | Docker bagimli (~165-200MB RAM), proje gelistirmesi yavas (3-4 yildir buyuk guncelleme yok), CPU spike sorunu (15-40s aralikla) | Orta - Docker overhead var ama calisir |
| **NPM (Native)** | Docker overhead yok | **Resmi olarak desteklenmiyor**, topluluk fork'lari var ama guncel degil, bakim zor | Dusuk - Kurulum ve bakim problematik |
| **Caddy** | Otomatik HTTPS (varsayilan), tek binary, Caddyfile ile basit config, Go ile yazilmis (dusuk kaynak tuketimi) | GUI yok (3. parti var ama olgun degil), Nginx kadar genis ekosistem yok | Yuksek - Tek binary, ~20-30MB RAM |
| **Traefik** | Docker/K8s ile mukemmel entegrasyon, otomatik servis kesfetme, dashboard var | Kubernetes odakli tasarim, Docker olmadan anlamsiz, config karmasik | Dusuk - Overengineered |
| **Pure Nginx + Certbot** | Maksimum performans, sifir overhead, tam kontrol, ~4-10MB RAM | GUI yok, config dosyasi elle yazilir, SSL yenileme cron gerektirir | Cok Yuksek - En hafif cozum |

### Detayli Notlar

#### NPM Docker Kaynak Tuketimi
- **RAM:** 165-200MB (tipik), 256MB limit onerilir
- **Disk:** ~500MB (Docker image + DB)
- **CPU:** Bilinen CPU spike sorunu var (GitHub Issue #492) - trafik olmasa bile 15-40 saniye aralikla spike yapar
- **Ek:** Docker daemon kendisi ~50-100MB RAM kullanir

**Kaynak:** [NPM RAM Discussion](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3244), [CPU Spikes Issue](https://github.com/jc21/nginx-proxy-manager/issues/492)

#### Caddy
- Tek binary dosya, Go ile yazilmis
- Varsayilan olarak tum sitelere otomatik HTTPS (Let's Encrypt + ZeroSSL)
- Caddyfile son derece basit:
  ```
  guard.tonbilx.com {
      reverse_proxy 192.168.1.2:8000
  }
  ```
- API uzerinden dinamik konfigürasyon mumkun

**Kaynak:** [Caddy vs Nginx vs Traefik](https://tolumichael.com/caddy-vs-nginx-vs-traefik-a-comprehensive-analysis/), [Programonaut Comparison](https://www.programonaut.com/reverse-proxies-compared-traefik-vs-caddy-vs-nginx-docker/)

#### Pure Nginx + Certbot
- Certbot otomatik cron job olusturur (`/etc/cron.d/certbot`)
- `sudo certbot renew --dry-run` ile test edilir
- 90 gunluk sertifikalar, otomatik yenileme
- Pi'de Nginx: ~4-10MB RAM, cok dusuk CPU

**Kaynak:** [Pi SSL Let's Encrypt](https://pimylifeup.com/raspberry-pi-ssl-lets-encrypt/), [Certbot Pi Guide](https://fleetstack.io/blog/raspberry-pi-certbot-ssl-certificate)

---

## 4. Fayda/Zarar Analizi: NPM'i Pi'ye Tasima

### Mevcut Durum

```
Internet → ISP Modem (192.168.1.1)
              ↓
         Pi (192.168.1.2) ← TonbilAiOS Firewall + Backend
              ↓
         NAS/NPM (192.168.1.4) ← Nginx Proxy Manager (Docker)
              ↓
         LAN Cihazlari
```

NPM su anda 192.168.1.4 (Tonbilx-n2 / NAS) uzerinde Docker container olarak calisiyor.

### FAYDALAR (Tasima Durumunda)

| # | Fayda | Aciklama |
|---|-------|----------|
| 1 | **Merkezi Yonetim** | Tek cihazda tum ag servisleri: firewall, DNS, DHCP, VPN, reverse proxy |
| 2 | **Ag Hop Eliminasyonu** | Dis erisim istekleri Pi → NAS hop'u yapmak yerine dogrudan Pi'de karsilanir. ~0.5-1ms gecikme azalmasi |
| 3 | **Tek SSL Yonetim Noktasi** | Sertifika yenileme ve proxy kurallari ayni cihazda |
| 4 | **NAS Bagimsizligi** | NAS kapansa bile reverse proxy calisir; NAS'in yuku azalir |
| 5 | **Guvenlik Sertlestirme** | Firewall + reverse proxy ayni cihazda = daha siki erisim kontrolu, WAF entegrasyonu potansiyeli |
| 6 | **Basitlik** | Bir cihaz daha az yonetilir, bir potansiyel hata noktasi daha az |

### ZARARLAR (Tasima Durumunda)

| # | Zarar | Ciddiyet | Aciklama |
|---|-------|----------|----------|
| 1 | **Pi'ye Ek Yuk** | ORTA | NPM Docker: ~200-300MB ek RAM (Docker daemon + container). Pi 4GB modelinde mevcut TonbilAiOS servisleriyle birlikte sikisik olabilir |
| 2 | **SPOF (Tek Hata Noktasi)** | YUKSEK | Pi arizalanirsa hem firewall hem reverse proxy coker. Simdiki durumda biri cokerse diger calisir |
| 3 | **Docker Overhead** | ORTA | Docker daemon Pi'de ek CPU/RAM tuketir. NPM'in bilinen CPU spike sorunu Pi'de daha belirgin olabilir |
| 4 | **Karmasiklik** | DUSUK | Docker + TonbilAiOS backend ayni port'larda cakisma riski (port 80, 443). Dikkatli port planlamasi gerekir |
| 5 | **Disk I/O** | DUSUK | SD kart uzerinde Docker layer'lari + NPM DB yazmalari SD kart omrunu kisaltabilir |
| 6 | **Bakim Zorlasmasi** | DUSUK | Pi'de sorun ciktiginda debug edilecek servis sayisi artar |

### Risk Degerlendirmesi

**En Buyuk Risk: SPOF**
- Mevcut durumda NAS (192.168.1.4) ve Pi (192.168.1.2) birbirinden bagimsiz
- Pi cokerse: DNS/DHCP/firewall durur ama web servisleri NAS uzerinden erisebilir
- Tasima sonrasi Pi cokerse: HER SEY durur

**En Buyuk Fayda: Basitlik ve Gecikme**
- Tek yonetim noktasi operasyonel karmasikligi azaltir
- Ag hop eliminasyonu olculebilir performans iyilestirmesi saglar

---

## 5. ONERI

### Kisa Vadeli Oneri: TASIMA

NPM'i Pi'ye tasimak **MANTIKSIZ DEGIL** ama en uygun yaklasim NPM Docker yerine **daha hafif bir cozum** kullanmak.

### Onerilen Yaklasim: Pure Nginx + Certbot (NPM Yerine)

**Neden NPM Docker degil:**
- Docker overhead (daemon + container = ~300MB ek RAM)
- NPM'in bilinen CPU spike sorunu
- NPM projesi 3-4 yildir aktif gelistirilmiyor
- Pi'de zaten Nginx calisiyor (TonbilAiOS frontend icin)

**Neden Pure Nginx + Certbot:**
- **Sifir ek overhead**: Mevcut Nginx process'i kullanilir, yeni bir servis baslatmaya gerek yok
- **~4-10MB RAM**: NPM'in 200-300MB'sine karsi
- **Kararlilk**: CPU spike sorunu yok, battle-tested
- **Certbot otomatik yenileme**: cron job ile 90 gunluk sertifikalar otomatik yenilenir
- **Tam kontrol**: Her site icin ozel config yazilabilir
- **Zaten mevcut**: Pi'de Nginx zaten port 80'de calisiyor

**Dezavantaj:** GUI yonetim paneli yok. Ancak:
- Proxy host sayisi az (5-10 site)
- Config degisikligi seyrek (ayda 1-2 kez)
- TonbilAiOS paneline basit bir "Reverse Proxy Yonetimi" sayfasi eklenebilir

### Alternatif Yaklasim: Caddy

Eger GUI-siz config dosyasi yonetimi istenmiyorsa **Caddy** iyi bir orta yol:
- Tek binary, ~20-30MB RAM
- Otomatik HTTPS (config'e domain yazmak yeterli)
- API uzerinden dinamik konfigürasyon (TonbilAiOS entegrasyonu icin ideal)
- Docker gerektirmez

### Uygulama Plani (Pure Nginx + Certbot Secilirse)

```
Asama 1: Mevcut NPM konfigurasyonunu disa aktar (proxy host'lar, SSL sertifikalari)
Asama 2: Pi'deki Nginx'e sites-available/ altinda yeni server block'lar ekle
Asama 3: Certbot ile SSL sertifikalari al (sudo certbot --nginx)
Asama 4: DNS kayitlarini Pi IP'sine yonlendir (176.88.250.236)
Asama 5: NAS'taki NPM container'ini durdur
Asama 6: Test et ve izle (1 hafta)
Asama 7: (Opsiyonel) TonbilAiOS paneline "Proxy Yonetimi" sayfasi ekle
```

### Kesin Karar Matrisi

| Senaryo | Oneri |
|---------|-------|
| Pi 4GB RAM, az sayida proxy host (<10) | **Pure Nginx + Certbot** → TASI |
| Pi 4GB RAM, cok sayida proxy host (>20) | **Caddy** → TASI |
| Pi 2GB RAM | **TASIMA** — kaynak yetersiz |
| Yuksek erisilebilirlik gerekliyse | **TASIMA** — SPOF riski kabul edilemez |
| NAS kaldirilacaksa | **Pure Nginx + Certbot** → ZORUNLU TASI |

---

## Kaynaklar

- [OPNsense Nginx WAF Tutorial](https://forum.opnsense.org/index.php?topic=19305.0)
- [OPNsense Reverse Proxy Docs](https://docs.opnsense.org/manual/reverse_proxy.html)
- [OPNsense + NPM in DMZ](https://homenetworkguy.com/how-to/deploy-nginx-proxy-manager-in-dmz-with-opnsense/)
- [OPNsense WAF NAXSI](https://www.zenarmor.com/docs/network-security-tutorials/how-to-configure-waf-on-opnsense-using-nginx-naxsi)
- [Pi NPM Install (Docker)](https://pimylifeup.com/raspberry-pi-nginx-proxy-manager/)
- [NPM Official Setup](https://nginxproxymanager.com/setup/)
- [NPM RAM Discussion](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3244)
- [NPM CPU Spike Issue](https://github.com/jc21/nginx-proxy-manager/issues/492)
- [NPM Memory Leak Issue](https://github.com/NginxProxyManager/nginx-proxy-manager/issues/4182)
- [Caddy vs Nginx vs Traefik](https://tolumichael.com/caddy-vs-nginx-vs-traefik-a-comprehensive-analysis/)
- [Reverse Proxy Comparison](https://www.programonaut.com/reverse-proxies-compared-traefik-vs-caddy-vs-nginx-docker/)
- [NPM vs Traefik vs Caddy (Stackademic)](https://blog.stackademic.com/npm-traefik-or-caddy-how-to-pick-the-reverse-proxy-youll-still-like-in-6-months-1e1101815e07)
- [NGINX vs HAProxy](https://www.openlogic.com/blog/nginx-vs-haproxy)
- [HAProxy vs Nginx Performance](https://last9.io/blog/haproxy-vs-nginx-performance/)
- [Pi SSL Let's Encrypt](https://pimylifeup.com/raspberry-pi-ssl-lets-encrypt/)
- [Certbot Pi Guide](https://fleetstack.io/blog/raspberry-pi-certbot-ssl-certificate)
- [Nginx Pi Performance](https://bobcares.com/blog/nginx-reverse-proxy-raspberry-pi-setup-guide/)
- [Pi 5 Nginx Performance](https://forum.digikey.com/t/raspberry-pi-5-vs-other-models-nginx-performance/53457)
