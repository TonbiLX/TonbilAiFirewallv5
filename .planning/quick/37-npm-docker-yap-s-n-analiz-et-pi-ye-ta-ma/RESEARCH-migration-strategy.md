# NPM Docker Yapisi Tasima Strateji Raporu

**Tarih:** 2026-03-13
**Hazirlayan:** Claude Opus 4.6

---

## Mevcut Durum Analizi

### 192.168.1.4 (TonbiLX-N0 / raspberrypi5)
- **Donanim:** Raspberry Pi 5, 8GB RAM
- **OS:** Debian Bookworm, aarch64, Linux 6.12.62
- **Docker:** v29.3.0, Docker Compose v5.1.0
- **NPM:** v2.14.0 (jc21/nginx-proxy-manager), container adi: `npm`
- **NPM Kaynak Tuketimi:** CPU %0.70, Net I/O: 135GB/135GB (yuksek trafik)
- **NPM Data Boyutu:** 203MB (/data dizini icinde: database.sqlite, nginx configs, SSL certs, logs)
- **Diger Container'lar:** 10 adet (Nextcloud, PhotoPrism, FileBrowser, Portainer, Redis, MariaDB, Watchtower)
- **Toplam RAM Kullanimi:** ~2GB / 7.9GB (mevcut)

### 192.168.1.2 (TonbilAiRouter / Pi)
- **Donanim:** Raspberry Pi 4, 4GB RAM (tahmini)
- **OS:** Linux, nginx port 80+93 (TonbilAiOS frontend/backend)
- **Mevcut Servisler:** FastAPI (port 8000), nginx (port 80/93), MariaDB, Redis, nftables, WireGuard, DNS proxy
- **Docker:** KURULU DEGIL (docker --version hata veriyor)
- **Port Kullanimi:** 80 (nginx), 93 (nginx), 8000 (uvicorn), 53 (DNS), 3306 (MariaDB), 6379 (Redis)

### NPM Proxy Host Envanteri (25 aktif conf)

| # | Domain | Hedef IP:Port | SSL | Aciklama |
|---|--------|--------------|-----|----------|
| 1 | pi.tonbil.com | 192.168.1.4:82 | LE npm-30 | Jump host web |
| 13 | npm.tonbil.com | 192.168.1.4:81 | LE npm-29 | NPM yonetim paneli |
| 2 | docker.tonbil.com | 192.168.1.4:9443 | LE npm-2 | Portainer |
| 4 | nextcloud.tonbil.com | 192.168.1.4:8081 | LE npm-33 | Nextcloud |
| 5 | photo.tonbil.com | 192.168.1.4:2342 | LE npm-5 | PhotoPrism |
| 32 | node1.tonbilx.com | 192.168.1.5:84 | LE npm-38 | Node 1 |
| 33 | node2.tonbilx.com | 192.168.1.9:85 | LE npm-39 | Node 2 (NAS) |
| 35 | plex.tonbilx.com | 192.168.1.5:32400 | LE npm-41 | Plex |
| 36 | ombi.tonbilx.com | 192.168.1.5:3579 | LE npm-42 | Ombi |
| 38 | radarr.tonbilx.com | 192.168.1.5:7878 | LE npm-44 | Radarr |
| 39 | bazarr.tonbilx.com | 192.168.1.5:6767 | LE npm-45 | Bazarr |
| 40 | sonarr.tonbilx.com | 192.168.1.5:8989 | LE npm-46 | Sonarr |
| 41 | nzb.tonbilx.com | 192.168.1.5:6789 | LE npm-47 | NZBGet |
| 42 | torrent.tonbilx.com | 192.168.1.5:8112 | LE npm-48 | Torrent |
| 43 | prowlarr.tonbilx.com | 192.168.1.5:9696 | LE npm-49 | Prowlarr |
| 44 | stats.tonbilx.com | 192.168.1.5:8181 | LE npm-50 | Tautulli/Stats |
| 45 | pihole.tonbilx.com | 192.168.1.7:86 | LE npm-51 | Pi-hole |
| 46 | dns.tonbilx.com | 192.168.1.7:5380 | LE npm-52 | Technitium DNS |
| 47 | file-n1.tonbilx.com | 192.168.1.5:3970 | LE npm-53 | FileBrowser N1 |
| 48 | file-n0.tonbilx.com | 192.168.1.4:3970 | LE npm-54 | FileBrowser N0 |
| 49 | file-n2.tonbilx.com | 192.168.1.9:3970 | LE npm-55 | FileBrowser N2 |
| 52 | a.previous.social | 192.168.1.4:9553 | LE npm-61 | Mastodon/Social |
| 53 | luci.tonbilx.com | 192.168.1.9:8765 | LE npm-63 | LuCI |
| 54 | wall.tonbilx.com | 192.168.1.2:93 | LE npm-66 | TonbilAiOS panel |
| 55 | guard.tonbilx.com | 192.168.1.2:8000 | LE npm-65 | DoH + API |

### Kritik Tespitler

1. **Pi'ye yonlendiren proxy'ler:** Sadece 2 adet (wall.tonbilx.com → :93, guard.tonbilx.com → :8000)
2. **Diger hedefler:** 192.168.1.4 (8 proxy), 192.168.1.5 (10 proxy), 192.168.1.9 (3 proxy), 192.168.1.7 (2 proxy)
3. **guard.tonbilx.com ozel konfigurasyonu:** `/dns-query` lokasyonu DoH endpointi icin ozel proxy_pass kurallari var
4. **Tum sertifikalar Let's Encrypt:** NPM otomatik yenileme yapiyor
5. **ISP port forwarding:** 80, 443 → 192.168.1.4

---

## SENARYO A: NPM Docker'i Pi'ye Tasi

### Konsept
Pi'ye Docker kurulur, NPM container'i ayni yapida calistirilir. /data dizini kopyalanir, port forwarding degistirilir.

### Uygulama Adimlari

1. **Docker kurulumu:** Pi'ye Docker Engine + Docker Compose kur
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker admin
   ```

2. **Pi nginx port cakismasi cozumu:** Mevcut nginx'i port 80'den kaldirip baska porta (ornegin 8080) tasi
   ```
   listen 8080;  # 80 yerine
   listen 93;    # ayni kalabilir
   ```

3. **NPM /data dizinini kopyala:** SCP veya rsync ile 203MB veri tasima
   ```bash
   rsync -avz admin@192.168.1.4:/data/compose/npm/ /opt/npm-data/
   ```

4. **docker-compose.yml olustur:**
   ```yaml
   version: '3.8'
   services:
     npm:
       image: jc21/nginx-proxy-manager:latest
       restart: unless-stopped
       ports:
         - '80:80'
         - '443:443'
         - '81:81'
       volumes:
         - /opt/npm-data/data:/data
         - /opt/npm-data/letsencrypt:/etc/letsencrypt
   ```

5. **Tum proxy host konfigurasyonlarinda hedef IP guncelle:** wall.tonbilx.com ve guard.tonbilx.com 192.168.1.2'ye isaret ediyor ama su an port 80 NPM'de olacak, iç istekler 127.0.0.1 uzerinden gidecek

6. **ISP modem port forwarding degistir:** 80, 443 → 192.168.1.2 (192.168.1.4 yerine)

7. **DNS propagation bekle ve test et:** Tum domain'leri kontrol et

8. **Eski NPM container'i durdur:** `docker stop npm` (192.168.1.4'te)

### On Kosullar
- Pi'de Docker kurulumu (disk alani: ~1GB ek)
- Pi'de port 80/443 serbest olmali (mevcut nginx tasima)
- ISP modem erisimi (port forwarding degisikligi)
- 203MB veri transfer imkani

### Tahmini Kesinti Suresi
- **Planlanan:** 15-30 dakika (port forwarding degistirme + DNS propagation)
- **Risk senaryosu:** 1-2 saat (sorun yasanirsa)

### Rollback Plani
1. ISP modem port forwarding'i 192.168.1.4'e geri al
2. Eski NPM container'i baslat: `docker start npm` (192.168.1.4)
3. Pi'deki nginx'i port 80'e geri al
4. Toplam rollback suresi: 5-10 dakika

### Risk Matrisi

| Risk | Seviye | Aciklama |
|------|--------|----------|
| Port cakismasi | **YUKSEK** | Pi'de nginx zaten 80'de; NPM de 80 istiyor. Biri tasimali |
| RAM yetersizligi | **YUKSEK** | Pi 4 (4GB) zaten TonbilAiOS + MariaDB + Redis calistiriyor. Docker + NPM ~200-400MB ek RAM |
| Disk alani | ORTA | Docker engine + images + NPM data ~1.5GB ek |
| SSL sertifika yenileme | DUSUK | Let's Encrypt HTTP-01 challenge port 80 uzerinden, NPM halledecek |
| DNS proxy cakismasi | ORTA | Docker kendi DNS resolver'i kullanir, Pi'deki DNS proxy ile cakisabilir |
| Network namespace | ORTA | Docker bridge network ile Pi'nin ag yapisi karisabilir |

### Pi Kaynak Etkisi
- **RAM:** +200-400MB (NPM container) + ~100MB (Docker daemon) = **+300-500MB**
- **CPU:** +%0.5-1 (NPM idle)
- **Disk:** +1.5GB (Docker + NPM data)
- **Net I/O:** Tum reverse proxy trafigi Pi uzerinden gececek (~270GB toplam)
- **TOPLAM RAM:** ~3.5GB / 4GB → **KRITIK ESIK** (swap'a dusmesi muhtemel)

---

## SENARYO B: Native Nginx + Certbot + Custom Panel

### Konsept
NPM tamamen birakilir. Pi'deki mevcut nginx genisletilir. 25 proxy host konfigurasyonu elle yazilir. Certbot ile SSL yonetimi yapilir. TonbilAiOS paneline nginx yonetim sayfasi eklenir.

### Uygulama Adimlari

1. **Certbot kurulumu:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **ISP modem port forwarding degistir:** 80, 443 → 192.168.1.2

3. **Nginx multi-site konfigurasyonu:** /etc/nginx/sites-available/ altina her domain icin ayri conf dosyasi olustur

4. **25 proxy host conf dosyasi olustur:** NPM'deki her proxy host icin nginx server blogu yaz
   ```nginx
   # /etc/nginx/sites-available/nextcloud.tonbil.com
   server {
       listen 80;
       server_name nextcloud.tonbil.com;
       return 301 https://$host$request_uri;
   }
   server {
       listen 443 ssl http2;
       server_name nextcloud.tonbil.com;
       ssl_certificate /etc/letsencrypt/live/nextcloud.tonbil.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/nextcloud.tonbil.com/privkey.pem;
       location / {
           proxy_pass http://192.168.1.4:8081;
           include proxy_params;
       }
   }
   ```

5. **SSL sertifikalari al:** Her domain icin certbot komutu calistir
   ```bash
   sudo certbot --nginx -d nextcloud.tonbil.com -d photo.tonbil.com ...
   ```

6. **Certbot auto-renewal cron:** Zaten varsayilan olarak kuruluyor

7. **TonbilAiOS paneline Nginx yonetim sayfasi ekle:**
   - Backend: `/api/v1/nginx-proxy/` endpoint'leri (conf dosyasi CRUD, nginx reload)
   - Frontend: NginxProxyPage.tsx (proxy host listele/ekle/sil)
   - `nginx -t && nginx -s reload` ile guvenli reload

8. **Mevcut TonbilAiOS nginx conf'u guncelle:** default_server olmaya devam etsin, diger domain'ler ayri conf

9. **Test ve dogrulama:** Her domain'i kontrol et

10. **Eski NPM container'i durdur**

### On Kosullar
- Certbot kurulumu
- ISP modem port forwarding degisikligi
- Nginx multi-site yapisi bilgisi
- 25 conf dosyasi hazirligi (otomatiklestirebilir)
- TonbilAiOS paneline yeni sayfa gelistirme (3-5 saat)

### Tahmini Kesinti Suresi
- **Planlanan:** 30-60 dakika (conf hazirligi onceden yapilir, sadece gecis ani)
- **Risk senaryosu:** 2-4 saat (sertifika sorunlari)

### Rollback Plani
1. ISP modem port forwarding'i 192.168.1.4'e geri al
2. Pi'deki nginx'i eski haline dondur (sadece TonbilAiOS conf)
3. Eski NPM container'i baslat
4. Toplam: 5-10 dakika

### Risk Matrisi

| Risk | Seviye | Aciklama |
|------|--------|----------|
| Konfigurasyon hatasi | **YUKSEK** | 25 conf dosyasi elle yonetmek hata riski tasir |
| SSL sertifika sorunlari | ORTA | Let's Encrypt rate limitleri (haftada 5 sertifika/domain), wildcard icin DNS challenge gerekir |
| Nginx crash | ORTA | Yanlis conf ile nginx dusebilir → TonbilAiOS erisim kaybeder |
| Panel gelistirme suresi | ORTA | Yeni sayfa gelistirme 3-5 saat is yuku |
| Bakım zorlugu | DUSUK | Certbot auto-renewal genellikle sorunsuz calisir |

### Pi Kaynak Etkisi
- **RAM:** +0MB (nginx zaten calisiyor, ek worker yok)
- **CPU:** +%0.1-0.5 (trafik artisi)
- **Disk:** +50MB (sertifikalar + conf dosyalari)
- **KAYNAK ETKISI: MINIMAL** — Docker overhead yok

---

## SENARYO C: Uzaktan Yonetim (Tasima Yok)

### Konsept
NPM oldugu yerde kalir (192.168.1.4). TonbilAiOS panelinden NPM API'sine (192.168.1.4:81) proxy yapilarak tek panelden yonetim saglanir.

### Uygulama Adimlari

1. **Backend: NPM API client yazimi** (npm_client.py)
   - httpx ile async HTTP client
   - Token yonetimi (POST /api/tokens → JWT)
   - Proxy host, certificate, stream CRUD sarmalama

2. **Backend: API endpoint'ler** (nginx_proxy.py)
   - `/api/v1/nginx-proxy/hosts` — Proxy host CRUD
   - `/api/v1/nginx-proxy/certificates` — SSL sertifika listele/talep
   - `/api/v1/nginx-proxy/status` — NPM durumu

3. **Frontend: NginxProxyPage.tsx**
   - Tab yapili sayfa (Proxy Hosts | SSL | Streams | Durum)
   - Cyberpunk Glassmorphism tema uyumu
   - CRUD modal/form

4. **Frontend: nginxProxyApi.ts + types/index.ts**
   - Axios fonksiyonlari + TypeScript interface'ler

5. **Router + Sidebar entegrasyonu**
   - App.tsx route ekleme
   - Sidebar.tsx menu ogesi ekleme

6. **NPM API erisim testi:** 192.168.1.2 → 192.168.1.4:81 HTTP erisilebilirlik kontrolu

7. **Deploy:** Backend dosya transfer + restart, Frontend build

### On Kosullar
- NPM API'nin ic agdan erisilebilir olmasi (192.168.1.4:81) — ZATEN MEVCUT
- NPM API credential'lari (emre@tonbil.com / benbuyum9087) — ZATEN BILINIYOR
- Gelistirme suresi: 3-4 saat

### Tahmini Kesinti Suresi
- **SIFIR** — Hicbir altyapi degisikligi yok

### Rollback Plani
- Gerek yok — sadece yeni panel ozelligini geri alir veya devre disi birakir

### Risk Matrisi

| Risk | Seviye | Aciklama |
|------|--------|----------|
| NPM API erisim hatasi | DUSUK | Ic ag, guvenilir. Status endpoint ile kontrol |
| 192.168.1.4 down oldugunda | ORTA | NPM down → tum reverse proxy down → panel da NPM'e erisamez. Ama bu zaten mevcut durum |
| API versiyon uyumsuzlugu | DUSUK | NPM v2 API stabil |
| Guvenlik | DUSUK | API credential'lari backend config'de tutulur |
| Tek nokta arizasi | **DEGISMEZ** | .4 hala tek nokta ariza — bu senaryoda bu sorun cozulmez |

### Pi Kaynak Etkisi
- **RAM:** +0MB
- **CPU:** +0%
- **Disk:** +0MB
- **KAYNAK ETKISI: YOK**

---

## SENARYO D: Hybrid (Kritik Proxy'ler Pi'ye)

### Konsept
Sadece guard.tonbilx.com ve wall.tonbilx.com gibi Pi'ye yonelen, guvenlik acisından kritik proxy'ler Pi'nin kendi nginx'ine alinir. Diger 23 proxy host NPM'de kalir.

### Uygulama Adimlari

1. **guard.tonbilx.com icin Pi nginx konfigurasyonu:**
   ```nginx
   # /etc/nginx/sites-available/guard.tonbilx.com
   server {
       listen 443 ssl http2;
       server_name guard.tonbilx.com;
       ssl_certificate /etc/letsencrypt/live/guard.tonbilx.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/guard.tonbilx.com/privkey.pem;

       location /dns-query {
           proxy_pass http://127.0.0.1:8000/api/v1/doh/dns-query;
           # DoH header'lari...
       }
       location / {
           proxy_pass http://127.0.0.1:8000;
       }
   }
   ```

2. **wall.tonbilx.com icin Pi nginx konfigurasyonu:**
   ```nginx
   server {
       listen 443 ssl;
       server_name wall.tonbilx.com;
       ssl_certificate /etc/letsencrypt/live/wall.tonbilx.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/wall.tonbilx.com/privkey.pem;
       location / {
           proxy_pass http://127.0.0.1:8000;
       }
   }
   ```

3. **Certbot ile sadece 2 domain icin SSL al:**
   ```bash
   sudo certbot certonly --webroot -w /opt/tonbilaios/frontend/dist -d guard.tonbilx.com -d wall.tonbilx.com
   ```

4. **ISP modem'e ek port forwarding:** 443 → hem 192.168.1.2 hem 192.168.1.4 (MUMKUN DEGIL — ayni port iki hedefe gidemez!)

5. **COZUM: Split DNS veya SNI routing:**
   - **Secenek 1:** guard ve wall domainleri icin DNS A kaydini degistir (Pi'nin public IP'sine)
   - **Secenek 2:** NPM'de guard/wall proxy'lerini silmeden, Pi'nin nginx'i port 443'te dinlesin ama sadece o domainler icin
   - **Secenek 3:** Tum 443 trafigini Pi'ye yonlendir, Pi baska domainleri .4'e reverse proxy yapsin

6. **En pratik cozum (Secenek 3):**
   - ISP modem: 80, 443 → 192.168.1.2
   - Pi nginx: guard.tonbilx.com, wall.tonbilx.com → lokal
   - Pi nginx: diger tum *.tonbil.com, *.tonbilx.com → proxy_pass 192.168.1.4 (NPM'e)
   - Ama bu durumda Pi zaten TUM trafigi isler → Senaryo A/B'ye yakin

7. **TonbilAiOS paneline NPM API entegrasyonu** (Senaryo C gibi)

### On Kosullar
- Port forwarding yapisal degisikligi (ayni port tek hedefe gidebilir)
- SNI routing veya Pi uzerinden catch-all proxy gerekliligi
- Certbot kurulumu
- NPM API entegrasyonu (Senaryo C gibi)

### Tahmini Kesinti Suresi
- **Planlanan:** 20-40 dakika (Secenek 3 icin)
- **Risk senaryosu:** 1-2 saat

### Rollback Plani
1. ISP modem port forwarding'i 192.168.1.4'e geri al
2. Pi'deki ek nginx conf'lari sil
3. Toplam: 5-10 dakika

### Risk Matrisi

| Risk | Seviye | Aciklama |
|------|--------|----------|
| Port forwarding karmasikligi | **YUKSEK** | Ayni port iki hedefe yonlendirilemez, SNI veya catch-all gerekir |
| Cift katman proxy | ORTA | Pi → NPM → hedef = 2 hop, latency artar |
| SSL sertifika yonetimi | ORTA | Bazi sertifikalar Pi'de, bazilari NPM'de — karisiklik |
| Mimari karmasiklik | **YUKSEK** | Iki ayri reverse proxy yonetmek zor |
| Bakım yuku | ORTA | Her iki tarafta da konfigurasyonlar bakımı gerekir |

### Pi Kaynak Etkisi
- **Secenek 3 secilirse:** Tum 443 trafigi Pi'den gecer → Senaryo A/B ile ayni
- **RAM:** +50-100MB (ek nginx worker'lar)
- **CPU:** +%0.5-1
- **Disk:** +10MB

---

## KARSILASTIRMA TABLOSU

| Kriter | A: NPM Docker | B: Native Nginx | C: Uzaktan Yonetim | D: Hybrid |
|--------|---------------|-----------------|--------------------|------------|
| **Kesinti suresi** | 15-30 dk | 30-60 dk | 0 dk | 20-40 dk |
| **Uygulama zorlugu** | Orta | Yuksek | Dusuk | Cok Yuksek |
| **Pi RAM etkisi** | +300-500MB | +0MB | +0MB | +50-100MB |
| **Pi disk etkisi** | +1.5GB | +50MB | +0MB | +10MB |
| **Tek nokta ariza** | Cozulur | Cozulur | Cozulmez | Kismen cozulur |
| **Bakim kolayligi** | Kolay (NPM GUI) | Orta (conf + certbot) | Kolay (panel) | Zor (iki sistem) |
| **Rollback suresi** | 5-10 dk | 5-10 dk | Aninda | 5-10 dk |
| **Gelistirme is yuku** | 1 saat | 5-8 saat | 3-4 saat | 6-10 saat |
| **Pi 4 uygunlugu** | KRITIK (RAM) | IDEAL | IDEAL | Uygun |
| **Uzun vadeli** | Iyi | En iyi | Gecici cozum | Karisik |

---

## ONERILEN SENARYO: C (Uzaktan Yonetim) + Gelecekte B'ye Gecis

### Neden C?

1. **SIFIR kesinti:** Hicbir altyapi degisikligi gerekmez. Trafik akisi degismez.

2. **SIFIR kaynak etkisi:** Pi 4'un sinirli 4GB RAM'inde her megabyte onemli. Docker kurulumu (+300-500MB) Pi'yi swap'a dusurur ve TonbilAiOS performansini ciddi sekilde etkiler.

3. **Hizli uygulama:** RESEARCH-tonbilaios-architecture.md belgesi zaten mimariyi detayli tanimlamis. 3-4 saatte tamamlanabilir.

4. **Risk yok:** Hicbir mevcut yapiyi bozmaz. NPM oldugu gibi calisir.

5. **Zaten planlandi:** Mimari analiz belgesinde (RESEARCH-tonbilaios-architecture.md) NPM API Proxy yaklasimi zaten detayli tasarlandi.

### Neden A veya B HEMEN DEGIL?

- **Senaryo A (Docker):** Pi 4'un 4GB RAM'i ile Docker + NPM container calistirmak **cok riskli**. Mevcut servisler (FastAPI + MariaDB + Redis + nginx + DNS proxy + nftables + WireGuard) zaten RAM'in ~2-2.5GB'ini kullaniyor. Docker daemon + NPM container ile toplam 3.5-4GB'a ulasir ve swap thrashing baslar. Bu, DNS cozumleme ve firewall performansini dogrudan etkiler.

- **Senaryo B (Native Nginx):** Uzun vadede en iyi cozum ama uygulama suresi 5-8 saat, 25 conf dosyasi yazmak + SSL sertifika sorunlari riski var. Bu, planlanan ve kontrollü bir gecis olarak ileriye saklanmali.

- **Senaryo D (Hybrid):** Port forwarding sinirlamalari nedeniyle pratik degil. Cift katman proxy karmasikligi bakım yuku arttirir.

### Onerilen Yol Haritasi

```
ASAMA 1 (SIMDI):  Senaryo C — NPM API panel entegrasyonu
                   → TonbilAiOS'tan NPM'i gorebilme ve yonetebilme
                   → Is yuku: 3-4 saat
                   → Kesinti: 0

ASAMA 2 (GELECEK): Pi 5'e gecis veya RAM upgrade sonrasi
                   → Senaryo B (Native Nginx + Certbot)
                   → NPM tamamen birakilir
                   → TonbilAiOS panel uzerinden tam nginx yonetimi
                   → Is yuku: 5-8 saat
                   → Planlanan kesinti: 30-60 dakika (bakım penceresi)
```

### Asama 1 (Senaryo C) Uygulama Kontrol Listesi

- [ ] `backend/app/services/npm_client.py` — NPM API istemcisi
- [ ] `backend/app/api/v1/nginx_proxy.py` — API endpoint'ler
- [ ] `backend/app/schemas/nginx_proxy.py` — Pydantic semalar
- [ ] `backend/app/api/v1/router.py` — Router kaydi
- [ ] `backend/app/config.py` — NPM credential'lari
- [ ] `frontend/src/services/nginxProxyApi.ts` — API cagrilari
- [ ] `frontend/src/types/index.ts` — TypeScript interface'ler
- [ ] `frontend/src/pages/NginxProxyPage.tsx` — Panel sayfasi
- [ ] `frontend/src/App.tsx` — Route ekleme
- [ ] `frontend/src/components/layout/Sidebar.tsx` — Menu ogesi
- [ ] Deploy + test

---

## SONUC

**Kisa vadeli en uygun senaryo: C (Uzaktan Yonetim)** — sifir kesinti, sifir kaynak etkisi, dusuk risk.

Pi 4'un 4GB RAM sinirlamasi, Docker tabanli cozumleri (Senaryo A) pratikte uygulanmaz kiliyor. Native Nginx (Senaryo B) uzun vadede ideal ama hemen uygulanmasi gereksiz risk tasir. Hybrid (Senaryo D) mimari karmasiklik getirerek bakım yukunu artirir.

Senaryo C, mevcut NPM altyapisini koruyarak TonbilAiOS'a guzel bir yonetim arayuzu kazandirir ve ileriye donuk B senaryosuna gecisin de onunu acar.
