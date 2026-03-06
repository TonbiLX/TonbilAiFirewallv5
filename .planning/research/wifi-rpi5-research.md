# Raspberry Pi 5 WiFi Access Point + Firewall Entegrasyonu Arastirma Raporu

**Tarih:** 2026-03-04
**Arastirma Modu:** Fizibilite + Ekosistem
**Genel Guven Seviyesi:** YUKSEK (cogu bulgu resmi kaynaklar ve topluluk deneyimleriyle dogrulanmistir)

---

## Yonetici Ozeti

Raspberry Pi 5, dahili Infineon CYW43455 WiFi cipiyle Access Point (AP) modunda calisabilir. Ancak bu cip, tek anten, tek spatial stream (1x1 MIMO) ve sinirli istemci kapasitesi (firmware seviyesinde ~10, teorik maksimum 25) nedeniyle **ticari bir AP'nin yerini tutamaz**. Mevcut TonbilAiOS bridge izolasyon mimarisine WiFi AP entegrasyonu teknik olarak mumkundur, ancak **routed (NAT) mod** tercih edilmelidir; cunku WiFi arayuzlerinin Linux bridge'e dogrudan eklenmesi ciddi teknik sinirlamalar tasir.

En pratik ve tavsiye edilen yaklasim: **TP-Link Deco X50 mesh sistemini Access Point moduna almak ve RPi 5'i router olarak tutmak**. Bu senaryoda Deco DHCP/DNS islemini yapmaz, sadece WiFi kapsama alani saglar. RPi 5'in kendi WiFi'si ise yonetim/IoT gibi ikincil amaclarla kullanilabilir.

---

## 1. Raspberry Pi 5 WiFi Donanim Ozellikleri

### WiFi Cipi: Infineon CYW43455

| Ozellik | Deger | Guven |
|---------|-------|-------|
| Cip | Infineon CYW43455 (eski adi Broadcom) | YUKSEK |
| Baglanti Arayuzu | SDIO (DDR50 mod destekli, Pi 4'e gore daha hizli) | YUKSEK |
| WiFi Standartlari | 802.11a/b/g/n/ac (Wi-Fi 5) | YUKSEK |
| Frekans Bantlari | 2.4 GHz + 5 GHz (cift bant) | YUKSEK |
| Kanal Genisligi | 20/40/80 MHz (80 MHz maksimum) | YUKSEK |
| Spatial Stream | 1x1 (tek akis) | YUKSEK |
| Maksimum PHY Hizi | ~433 Mbps (MCS 9, 80 MHz, kisa GI) | YUKSEK |
| Beamforming | Sadece SU Beamformee (beamformer degil) | YUKSEK |
| LDPC | HT rate'ler icin desteklenir | YUKSEK |
| Bluetooth | 5.0 (BLE destekli) | YUKSEK |
| Anten | Dahili PCB anten, tek anten, SMA konektoru YOK | YUKSEK |
| WPA3/SAE | **DESTEKLENMIYOR** (donanim sinirlamasi) | YUKSEK |

**Kaynak:** [Raspberry Pi 5 WiFi Analizi - WiFi Diving](https://wifidiving.substack.com/p/raspberry-pi-5-in-built-wifi), [Tom's Hardware RPi5 WiFi Testi](https://www.tomshardware.com/news/raspberry-pi-5-wi-fi-faster)

### AP Modu Yetenekleri

| Ozellik | Durum | Detay |
|---------|-------|-------|
| AP Modu | DESTEKLENIR | hostapd veya NetworkManager ile |
| STA+AP Esanli | DESTEKLENIR | CYW43455 concurrent AP+STA destekler (ayni bant, ayni kanal) |
| Maksimum Istemci (Firmware) | ~10 cihaz (pratikte) | Firmware RAM kisitlamasi nedeniyle |
| Maksimum Istemci (Teorik) | 25 cihaz | Infineon resmi dokumantasyonu |
| Cift Bant AP | DESTEKLENMIYOR | Ayni anda 2.4 + 5 GHz AP mumkun degil (RSDB yok) |
| 5 GHz AP | DESTEKLENIR | hw_mode=a, channel=36, ieee80211ac=1 |
| 2.4 GHz AP | DESTEKLENIR | hw_mode=g, channel=1/6/11 |

**Kaynak:** [Infineon CYW43455 AP/STA Desteği](https://community.infineon.com/t5/Wi-Fi-Combo/Does-CYW43455-support-AP-STA-mode-simultaneously/td-p/133917), [RPi Linux Issue #3010](https://github.com/raspberrypi/linux/issues/3010)

### Performans Degerlendirmesi

| Metrik | Deger | Kosul |
|--------|-------|-------|
| STA Modu Throughput | ~217 Mbps | iperf3, yakin mesafe, Pi 5 |
| AP Modu Throughput | ~90-100 Mbps | Pratikte gozlemlenen |
| PHY Verimlilik | %50-55 | Beklenen %75 TCP, %85 UDP |
| Kapsama Alani | 15m (duvar ile %56 sinyal) | Tek anten sinirlamasi |
| 20-30m + 3 duvar | Baglantiyi kaybeder | Kullanisiz seviye |

**Kritik Not:** Pi 5'in WiFi'si, Pi 4 ile **ayni CYW43455 cipini** kullanir. Fark sadece SDIO arayuzunun daha hizli olmasidir (DDR50). WiFi radyo performansi aynidir.

**Kaynak:** [RPi Forum - Pi 5 WiFi AP Kullanilabilirlik](https://forums.raspberrypi.com/viewtopic.php?t=367584)

---

## 2. hostapd / NetworkManager Yapilandirmasi

### Bookworm'da Iki Yaklasim

Raspberry Pi OS Bookworm, ag yonetimi icin **NetworkManager**'a gecmistir. Bu nedenle iki farkli yaklasim vardir:

### Yaklasim A: NetworkManager (nmcli) -- MODERN, TAVSIYE EDILEN

```bash
# AP olustur
sudo nmcli con add con-name TonbilAP ifname wlan0 type wifi ssid "TonbilAiOS"

# Guvenlik ayarlari (WPA2 - WPA3 desteklenmiyor!)
sudo nmcli con modify TonbilAP wifi-sec.key-mgmt wpa-psk
sudo nmcli con modify TonbilAP wifi-sec.psk "GuvenliSifre123"

# AP modu + 5 GHz bant + IP paylasimi (NAT)
sudo nmcli con modify TonbilAP 802-11-wireless.mode ap
sudo nmcli con modify TonbilAP 802-11-wireless.band a
sudo nmcli con modify TonbilAP ipv4.method shared

# Baslat
sudo nmcli con up TonbilAP
```

**Avantajlari:**
- Basit kurulum (3-4 komut)
- Bookworm native destegi
- Otomatik dnsmasq ve NAT yonetimi (`ipv4.method shared` kullanildiginda)

**Dezavantajlari:**
- Bridge modu zorluklar cikarir (NetworkManager WiFi bridge'i tam desteklemez)
- Gelismis hostapd parametreleri sinirli

### Yaklasim B: hostapd + dnsmasq -- GELENEKSEL, TAM KONTROL

```ini
# /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=TonbilAiOS
country_code=TR
hw_mode=a
channel=36
ieee80211d=1
ieee80211n=1
ieee80211ac=1
wmm_enabled=1
wpa=2
wpa_passphrase=GuvenliSifre123
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP

# 802.11ac (VHT) Ayarlari
ieee80211ac=1
vht_oper_chwidth=1
vht_oper_centr_freq_seg0_idx=42

# Bridge modu (opsiyonel - onerilen degil, asagiya bkz)
# bridge=br0
```

```ini
# /etc/dnsmasq.d/wifi-ap.conf (NAT modu icin)
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,12h
dhcp-option=3,192.168.50.1
dhcp-option=6,192.168.50.1
```

**Avantajlari:**
- Tam kontrol (kanal, TX gucu, 802.11ac parametreleri)
- TonbilAiOS mimarisine daha iyi entegrasyon
- nftables ile dogrudan calisabilir

**Dezavantajlari:**
- Daha fazla konfigrasyon
- NetworkManager ile catisma riski (disable edilmeli veya wlan0 unmanaged yapilmali)

### WPA3 Sinirlamasi

**CYW43455, WPA3/SAE sifrelemesini DESTEKLEMEZ.** Bu bir donanim sinirlamasidir:
- Desteklenen cipher: `00-0f-ac:2` (CCMP/WPA2)
- Desteklenmeyen cipher: `00-0f-ac:8` (SAE/WPA3)
- Dogrulama: `sudo iw phy phy0 info` komutu ile kontrol edilebilir

**Cozum:** WPA2-PSK (AES/CCMP) kullanmak. WPA3 gerekiyorsa harici USB WiFi adaptoru sart.

**Kaynak:** [RPi Forum - WPA3 Desteği](https://forums.raspberrypi.com/viewtopic.php?t=370531), [RPi Forum - RPI5 WPA3 Hotspot](https://forums.raspberrypi.com/viewtopic.php?t=364824)

### Turkiye Regulatory Domain

```bash
# Regulatory domain ayari
sudo raspi-config  # Localisation > WLAN Country > TR

# Veya dogrudan:
sudo iw reg set TR

# hostapd.conf icinde:
country_code=TR
ieee80211d=1
```

Turkiye'de 5 GHz icin genellikle kanal 36-48 (UNII-1) sorunsuz calisir. DFS kanallari (52-144) ek sinirlamalar getirir.

---

## 3. WiFi AP ile Bridge Firewall Mimarisi Entegrasyonu

### Mevcut TonbilAiOS Mimarisi

```
Internet <-> eth0 (WAN) <--br0 bridge--> eth1 (LAN) <-> LAN Cihazlari
                                |
                        RPi 5 (192.168.1.2)
                        nftables bridge isolation
                        NAT MASQUERADE
```

Mevcut sistemde:
- `br0` bridge: eth0 (WAN) + eth1 (LAN)
- Bridge izolasyon: L2 forwarding drop + NAT MASQUERADE
- nftables `bridge accounting` tablosu: MAC bazli upload/download sayaclari
- Cihaz kesfetme: ARP tablosu uzerinden (br0, eth0, eth1, wlan0 arayuzleri)
- Bant genisligi izleme: Bridge counter'lar uzerinden

### KRITIK: wlan0'i Bridge'e Eklemek

**Linux cekirdeginde WiFi arayuzlerini dogrudan bridge'e eklemek SINIRLIDIR:**

1. **802.11 Frame Sorunu:** WiFi, 3-adresli frame kullanir (kaynak, hedef, BSSID). Bridge icin 4-adresli frame (WDS/4addr modu) gerekir.

2. **Standart hostapd ile bridge:** hostapd yapilandirmasinda `bridge=br0` ayari kullanilabilir. Bu durumda hostapd, wlan0'i br0'a otomatik ekler. **ANCAK:**
   - Her istemci icin ayri bir sanal arayuz olusturulur (wlan0.sta1, wlan0.sta2...)
   - Bazi donanim/suruculerde bu calismaz
   - CYW43455 ile deneysel/guvenilmez

3. **Proxy ARP (parprouted) Cozumu:** WiFi istemcilerini ayni subnet'e koyar ama gercek bridge degil, ARP proxy + /32 host route kullanir. Daha guvenilir ama karmasik.

### TAVSIYE: Routed (NAT) Mod

WiFi AP icin **ayri subnet + NAT** en guvenilir yaklasimdir:

```
Internet <-> eth0 (WAN) <--br0--> eth1 (LAN) <-> LAN Cihazlari (192.168.1.0/24)
                                    |
                              RPi 5 (192.168.1.2)
                                    |
                              wlan0 (AP) <-> WiFi Cihazlari (192.168.50.0/24)
```

#### nftables Entegrasyonu (Routed Mod)

```nft
# WiFi AP icin NAT ve forwarding kurallari
table inet tonbilai {
    chain forward {
        # Mevcut kurallar...

        # WiFi -> LAN forwarding
        iifname "wlan0" oifname "br0" ct state new accept

        # LAN -> WiFi forwarding (established)
        iifname "br0" oifname "wlan0" ct state established,related accept
    }
}

# WiFi subnet icin MASQUERADE
table inet nat {
    chain postrouting {
        oifname "br0" ip saddr 192.168.50.0/24 masquerade
    }
}
```

#### Per-Device Trafik Izleme (WiFi Cihazlari)

WiFi cihazlarinin trafik izlemesi icin mevcut bridge accounting sistemi DOGRUDAN KULLANILAMAZ (wlan0 bridge'de degil). Alternatif:

**Secenek 1: nftables inet tablosunda WiFi chain'leri**
```nft
table inet wifi_accounting {
    chain wifi_upload {
        type filter hook forward priority -2; policy accept;
        iifname "wlan0" counter
        # Per-MAC kurallar eklenecek
    }
    chain wifi_download {
        type filter hook forward priority -2; policy accept;
        oifname "wlan0" counter
        # Per-MAC kurallar eklenecek
    }
}
```

**Secenek 2: conntrack + flow_tracker genisletme**
Mevcut flow_tracker.py zaten conntrack kullanarak per-flow takip yapiyor. WiFi subnet'inden gelen trafik de conntrack'te gorunecektir. `flow_tracker.py` icinde WiFi subnet tanima eklemek yeterli olabilir.

### DHCP Yapilandirmasi

| Senaryo | LAN DHCP | WiFi DHCP | DNS |
|---------|----------|-----------|-----|
| Ayri Subnet (NAT) | 192.168.1.100-200 (mevcut dnsmasq) | 192.168.50.10-50 (wlan0 dnsmasq) | RPi DNS proxy (192.168.50.1) |
| Ayni Subnet (Bridge) | Tek havuz 192.168.1.100-250 | Ayni havuz | RPi DNS proxy |

**Tavsiye:** Ayri subnet. Boylece WiFi cihazlari LAN cihazlarindan izole edilebilir, profil bazli farkli kurallar uygulanabilir.

---

## 4. Ag Mimarisi Secenekleri

### Secenek A: RPi Standalone WiFi AP (hostapd)

**Senaryo:** RPi 5, kendi dahili WiFi'si ile Access Point calistirir.

```
Internet <-> Modem <-> RPi 5 (eth0/eth1 bridge + wlan0 AP)
                            |              |
                       LAN Cihazlari   WiFi Cihazlari
```

| Avantaj | Dezavantaj |
|---------|------------|
| Tek cihaz, basit mimari | Cok sinirli kapsama alani (15-20m) |
| Tam kontrol (firewall, DNS, QoS) | Maks ~10 istemci |
| WiFi cihazlari icin ayni filtreleme | ~90-100 Mbps throughput |
| Ek maliyet yok | Tek anten, MIMO yok |
| | Termal sorunlar (yuk altinda) |
| | WPA3 desteği yok |

**Degerlendirme:** Sadece kucuk oda, 3-5 cihaz, dusuk bant genisligi gereksinimleri icin uygun. **Birincil WiFi AP olarak ONERILMEZ.**

### Secenek B: RPi WiFi Yonetim/IoT Agi -- TAVSIYE EDILEN IKINCIL KULLANIM

**Senaryo:** RPi 5 WiFi'si sadece ozel amacli bir ikincil ag olarak kullanilir.

```
Internet <-> Modem <-> RPi 5 <-> Deco X50 (AP modu)
                  |         |              |
              LAN Cihazlar  |         Ana WiFi Cihazlari
                            |
                     wlan0 (AP: "TonbilAiOS-IoT")
                            |
                     IoT/Yonetim Cihazlari
```

| Avantaj | Dezavantaj |
|---------|------------|
| IoT cihazlarini ana agdan izole eder | Iki farkli WiFi agi yonetimi |
| Guvenlik segmentasyonu | IoT cihazlari sinirli bant genisliginde |
| RPi yonetim arayuzune dogrudan erisim | Ekstra konfigrasyon |
| Ana WiFi Deco tarafindan saglanir | |

**Kullanim Alanlari:**
- Akilli ev cihazlari (IoT) icin izole ag
- RPi yonetim paneline kablosuz erisim
- Misafir agi (captive portal ile)
- Gecici debug/test agi

### Secenek C: RPi Mesh Node -- ONERILMEZ

**Senaryo:** RPi 5, Deco X50 mesh agina katilir.

**Bu secenek UYGULANAMAZ cunku:**
- TP-Link Deco, tescilli (proprietary) mesh protokolu kullanir
- 802.11s / batman-adv gibi acik mesh protokolleri ile uyumlu DEGIL
- RPi'nin CYW43455 cipi, Deco'nun mesh protokolunu desteklemez
- Wired backhaul node olarak bile katilim MUMKUN DEGIL (Deco firmware kisitlamasi)

### Secenek D: RPi Router + Deco X50 AP Modu -- EN IYI SECENEK

**Senaryo:** Deco X50 mesh sistemi Access Point moduna alinir, DHCP/DNS/firewall tamamen RPi tarafindan yonetilir.

```
Internet <-> Modem (bridge/passthrough)
                |
           RPi 5 (Router)
           ├── eth0: WAN
           ├── eth1 (br0): LAN
           ├── nftables firewall
           ├── DNS proxy + filtreleme
           ├── DHCP (dnsmasq)
           └── wlan0 (opsiyonel IoT AP)
                |
           Deco X50 (AP Modu)
           ├── Ana WiFi kapsama (mesh)
           ├── DHCP: DEVRE DISI
           ├── Wired backhaul: eth1 -> Deco
           └── Tum istemciler RPi uzerinden
```

| Avantaj | Dezavantaj |
|---------|------------|
| En iyi WiFi performansi (Deco WiFi 6, MIMO) | Deco AP modunda bazi gelismis ozellikler kapali |
| Tam firewall/DNS kontrolu | Iki cihaz yonetimi |
| Tum cihazlar TonbilAiOS'tan gorunur | Deco firmware guncelleme gerektirebilir |
| Mesh kapsama alani korunur | |
| RPi'nin WiFi sinirlamalari onemli degil | |
| Mevcut mimariyle tamamen uyumlu | |

---

## 5. TP-Link Deco X50 Mesh Entegrasyonu

### Deco X50 Access Point Modu

TP-Link Deco X50, Access Point modunu resmi olarak destekler:

**Kurulum:**
1. Deco uygulamasinda: More > Advanced > Operation Mode > Access Point
2. Deco'yu RPi'nin eth1 (LAN) portuna Ethernet ile bagla
3. Deco DHCP sunucusunu otomatik olarak devre disi birakir
4. Tum istemciler, RPi'den (dnsmasq) IP alir

**Wired Backhaul:**
- AP modunda Deco uniteler arasi Ethernet backhaul DESTEKLENIR
- Deco uniteler arasi WiFi backhaul de calisir
- Ethernet backhaul, WiFi backhaul'dan cok daha guvenilir ve hizli

**Bilinen Kisitlamalar:**
- AP modunda bazi gelismis Deco ozellikleri (QoS, parental controls) kapanabilir
- Firmware guncellemesi bazen AP modunu sifirlar (nadir)
- Deco uygulamasindan gorunen istatistikler sinirli kalabilir

### RPi ile Deco Uyumu

**RPi Router, Deco AP senaryosu icin gerekli ayarlar:**

1. **RPi DHCP (dnsmasq):** `dhcp-option=3,192.168.1.2` (gateway olarak RPi)
2. **RPi DNS:** `dhcp-option=6,192.168.1.2` (DNS olarak RPi)
3. **Deco:** AP moduna alinir, DHCP otomatik kapanir
4. **ARP/Cihaz Kesfetme:** Deco bridge modunda calisir, istemci MAC adresleri RPi'ye seffaf olarak iletilir

**ONEMLI:** Deco AP modunda WiFi istemcilerinin MAC adresleri RPi'ye gorunur (bridge/transparent mod). Bu, TonbilAiOS'un mevcut MAC bazli cihaz takip, DNS filtreleme ve bant genisligi izleme sistemlerinin calismaya devam etmesini saglar.

### RPi Mesh Node Olarak Deco'ya Katilim -- MUMKUN DEGIL

| Soru | Cevap | Aciklama |
|------|-------|----------|
| RPi, Deco mesh'e katilabilir mi? | HAYIR | Deco tescilli protokol kullanir |
| 802.11s uyumlu mu? | HAYIR | Deco, 802.11s kullanmaz |
| batman-adv ile uyumlu mu? | HAYIR | Farkli katman ve protokol |
| Wired backhaul node olarak? | HAYIR | Deco sadece kendi unitlerini taniyor |
| OpenWrt yuklenebilir mi? | HAYIR | Deco X50 OpenWrt desteklemiyor |

**Kaynak:** [TP-Link Deco AP Modu Kurulumu](https://www.tp-link.com/us/support/faq/1842/), [TP-Link Wired Backhaul SSS](https://www.tp-link.com/us/support/faq/1794/)

---

## 6. Pratik Degerlendirmeler

### WiFi Performansi: RPi 5 vs Ozel AP

| Metrik | RPi 5 (CYW43455) | Deco X50 | Ozel AP (Ornek) |
|--------|-------------------|----------|-----------------|
| WiFi Standardi | Wi-Fi 5 (802.11ac) | Wi-Fi 6 (802.11ax) | Wi-Fi 6/6E |
| Spatial Streams | 1x1 | 2x2 | 2x2 / 4x4 |
| Maks PHY Hizi | 433 Mbps | 2402 Mbps (5 GHz) | Degisken |
| Pratik Throughput | 90-100 Mbps | 500-800 Mbps | Degisken |
| Istemci Kapasitesi | ~10 | 128+ | 50-200+ |
| Kapsama | 15-20m (tek duvar) | 230 m2+ (mesh) | Degisken |
| Anten | 1x dahili PCB | 4x dahili | Degisken |
| MU-MIMO | YOK | DESTEKLENIR | Genellikle var |
| Beam Steering | YOK | DESTEKLENIR | Genellikle var |
| WPA3 | YOK | DESTEKLENIR | Genellikle var |

**Sonuc:** RPi 5'in WiFi'si, birincil AP olarak **kesinlikle yetersizdir**. Deco X50 veya benzeri bir ozel AP, performans acisindan cok daha ustundur.

### Termal ve Guc Degerlendirmeleri

| Faktor | Detay |
|--------|-------|
| CPU Throttling | 80C'de yumusak, 85C'de sert throttle |
| WiFi AP Yuku | Ek CPU yuku minimal (~%1-3) |
| Sogutma Gereksinimi | Aktif sogutucu (fan) KESINLIKLE TAVSIYE EDILIR |
| Guc Tuketimi | WiFi AP aktif: ~0.5W ek tuketim |
| Uzun Sureli Calisma | Fan ile sorun olmaz; fansiz termal birikme riski |

**Not:** TonbilAiOS zaten ag islemleri (DNS proxy, nftables, conntrack, bandwidth izleme) yapiyor. WiFi AP eklenmesi marginal ek yuk getirir. Asil termal sorun zaten mevcut islerden kaynaklaniyor.

### Kanal Girisim Onlemleri

RPi WiFi AP'si, mevcut Deco X50 mesh AP'leri ile ayni ortamda calisacaksa:

1. **Farkli bant sec:** Deco 5 GHz kullaniyorsa, RPi'yi 2.4 GHz'de calistir (veya tam tersi)
2. **Kanal ayirimi:** Ayni bantta calisacaklarsa, en az 5 kanal aralik birak
3. **TX gucu:** RPi'nin TX gucunu dusur (`iwconfig wlan0 txpower 10`)
4. **Fiziksel mesafe:** Mumkunse farkli odalara yerlestir

### NetworkManager vs wpa_supplicant

| Ozellik | NetworkManager | wpa_supplicant + hostapd |
|---------|---------------|------------------------|
| Bookworm Varsayilani | EVET | HAYIR (legacy) |
| AP Modu Destegi | EVET (nmcli ile) | EVET (hostapd ile) |
| Bridge Destegi | SINIRLI (WiFi bridge sorunlu) | DAHA IYI (hostapd bridge=br0) |
| NAT/Routing | Otomatik (ipv4.method shared) | Manuel (iptables/nftables) |
| Esneklik | ORTA | YUKSEK |
| TonbilAiOS Entegrasyonu | ZOR (NM cakismalari) | KOLAY (dogrudan kontrol) |

**Tavsiye:** TonbilAiOS icin **hostapd + manuel nftables** kullanmak. NetworkManager, wlan0 icin `unmanaged` yapilmali:

```ini
# /etc/NetworkManager/conf.d/99-unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:wlan0
```

---

## 7. TonbilAiOS Entegrasyon Plani (Tavsiye Edilen Yaklasim)

### Asamali Uygulama

#### Asama 1: Deco X50'yi AP Moduna Alma (En Az Effor, En Cok Kazanc)

**Ne yapilir:**
- Deco X50, Access Point moduna alinir
- RPi, DHCP ve DNS sunucusu olarak yapilandirilir (zaten var)
- Deco, RPi'nin LAN portuna (eth1) baglanir
- Tum WiFi istemcileri RPi uzerinden gecer

**TonbilAiOS Degisiklikleri:**
- Minimal. Mevcut mimari zaten calisiyor.
- Deco bridge modunda MAC adresleri RPi'ye seffaf.
- device_discovery.py, bandwidth_monitor.py, dns_proxy.py degisiklik GEREKTIRMEZ.

#### Asama 2 (Opsiyonel): RPi WiFi AP - IoT/Yonetim Agi

**Ne yapilir:**
- RPi wlan0 uzerinde ikincil AP baslatilir (hostapd)
- Ayri subnet: 192.168.50.0/24
- IoT cihazlari, misafir agi veya yonetim erisimleri icin

**TonbilAiOS Degisiklikleri:**
- `linux_nftables.py`: WiFi subnet icin NAT ve forwarding kurallari
- `linux_dhcp_driver.py`: WiFi subnet icin DHCP pool
- `device_discovery.py`: wlan0 ARP/neighbor izleme (zaten wlan0 destekliyor)
- `flow_tracker.py`: WiFi subnet trafik tanima
- `bandwidth_monitor.py`: WiFi icin ayri accounting chain'leri
- Frontend: WiFi AP yonetim sayfasi (SSID, sifre, kanal, istemci listesi)

### Mimari Diyagram (Tam Entegrasyon)

```
                    Internet
                       |
                    Modem (Bridge/NAT)
                       |
                    eth0 (WAN)
                       |
            +----- RPi 5 (192.168.1.2) ------+
            |          |                       |
            |       br0 bridge                 |
            |          |                       |
            |       eth1 (LAN)            wlan0 (AP)
            |          |               "TonbilAiOS-IoT"
            |          |               192.168.50.0/24
            |    Deco X50 (AP)              |
            |    "Ev WiFi"             IoT Cihazlari
            |    192.168.1.0/24
            |          |
            |    WiFi Cihazlari
            |    (telefon, laptop...)
            |
            +-- nftables firewall
            +-- DNS proxy + filtreleme
            +-- DHCP (dnsmasq)
            +-- Bandwidth izleme
            +-- Traffic flow tracking
            +-- AI analiz motoru
            +-- Telegram bildirimler
            +-- WireGuard VPN
```

---

## 8. Sonuc ve Tavsiyeler

### Kesin Tavsiyeler

1. **YAPMA: RPi 5'i birincil WiFi AP olarak kullanma.** Performans, kapsama, istemci kapasitesi ve guvenlik (WPA3 yok) acisindan yetersiz.

2. **YAP: Deco X50'yi AP moduna al, RPi'yi router olarak tut.** En iyi performans/kontrol dengesi. Minimum degisiklik gerektirir.

3. **OPSIYONEL: RPi WiFi'yi IoT/yonetim agi olarak kullan.** Guvenlik segmentasyonu icin degerli. Ayri subnet ile.

4. **YAPMA: RPi'yi Deco mesh'e katmayi dene.** Teknik olarak imkansiz (tescilli protokol).

5. **YAPMA: wlan0'i br0 bridge'e eklemeyi dene.** Guvenilmez, CYW43455 ile sorunlu. NAT/routed mod kullan.

6. **YAP: hostapd kullan, NetworkManager degil.** TonbilAiOS'un dogrudan kontrol modeli ile daha uyumlu.

### Uygulama Oncelikleri

| Oncelik | Is Kalemi | Effor | Etki |
|---------|-----------|-------|------|
| 1 (HEMEN) | Deco X50 AP moduna alma | DUSUK (sadece Deco ayari) | YUKSEK |
| 2 (KISA VADE) | RPi DHCP/DNS'in Deco istemcilerini yonettigini dogrulama | DUSUK | YUKSEK |
| 3 (ORTA VADE) | RPi WiFi IoT AP (hostapd yapilandirmasi) | ORTA | ORTA |
| 4 (ORTA VADE) | nftables WiFi entegrasyonu | ORTA | ORTA |
| 5 (UZUN VADE) | Frontend WiFi yonetim sayfasi | YUKSEK | DUSUK |

### Guven Degerlendirmesi

| Alan | Guven | Aciklama |
|------|-------|----------|
| CYW43455 donanim ozellikleri | YUKSEK | Infineon ve coklu kaynaklarla dogrulanmis |
| AP modu calisabilirligi | YUKSEK | Topluluk deneyimleri ve resmi dokumantasyon |
| Performans sinirlari | YUKSEK | Birden fazla bagimsiz benchmark |
| WPA3 sinirlamasi | YUKSEK | Donanim cipher listesi ile dogrulanmis |
| Bridge mod sinirlari | YUKSEK | Linux cekirdek mimarisi ve topluluk deneyimi |
| Deco X50 AP modu | YUKSEK | TP-Link resmi dokumantasyon |
| Deco mesh uyumsuzlugu | YUKSEK | Tescilli protokol, topluluk dogrulamasi |
| nftables entegrasyonu | ORTA | Mimarisi bilinir ama TonbilAiOS'a ozel test gerekir |
| Termal etkiler | ORTA | Genel RPi5 verileri mevcut, WiFi AP spesifik veri az |

---

## Kaynaklar

### Resmi / Yetkili Kaynaklar
- [Raspberry Pi 5 Product Brief (Subat 2026)](https://pip.raspberrypi.com/documents/RP-008348-DS-3-raspberry-pi-5-product-brief.pdf)
- [Raspberry Pi Documentation - Configuration](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [TP-Link Deco AP Modu Kurulumu](https://www.tp-link.com/us/support/faq/1842/)
- [TP-Link Deco Wired Backhaul SSS](https://www.tp-link.com/us/support/faq/1794/)
- [nftables Wiki - NAT](https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT))

### Teknik Analiz
- [Raspberry Pi 5 WiFi Analizi - WiFi Diving](https://wifidiving.substack.com/p/raspberry-pi-5-in-built-wifi)
- [Tom's Hardware - RPi5 WiFi Hiz Testi](https://www.tomshardware.com/news/raspberry-pi-5-wi-fi-faster)
- [Jeff Geerling - WiFi 7 on RPi5](https://www.jeffgeerling.com/blog/2025/exploring-wifi-7-2-gbps-on-raspberry-pi-5/)

### Infineon (Chip Uretici)
- [CYW43455 AP/STA Concurrent Mode](https://community.infineon.com/t5/Wi-Fi-Combo/Does-CYW43455-support-AP-STA-mode-simultaneously/td-p/133917)
- [CYW43455 Concurrent STA+AP Config](https://community.infineon.com/t5/Wi-Fi-Combo/Configure-CYW43455-Wifi-AP-and-Station-mode-Concurrently/td-p/185604)
- [CYW43455 Dual Band AP Sinirlamasi](https://community.infineon.com/t5/Wi-Fi-Combo/CYW43455-AP-configuration-for-dual-band-use/td-p/42638)

### Topluluk / Forum
- [RPi Forum - Pi 5 Ana WiFi AP Kullanilabilirlik](https://forums.raspberrypi.com/viewtopic.php?t=367584)
- [RPi Forum - WPA3/SAE Desteği](https://forums.raspberrypi.com/viewtopic.php?t=370531)
- [RPi Forum - RPi5 WPA3 Hotspot NM](https://forums.raspberrypi.com/viewtopic.php?t=364824)
- [RPi Forum - WiFi AP Bridge](https://forums.raspberrypi.com/viewtopic.php?t=383907)
- [RPi Forum - WiFi Istemci Siniri](https://github.com/raspberrypi/linux/issues/3010)
- [RPi Forum - Bookworm AP Kurulumu](https://forums.raspberrypi.com/viewtopic.php?t=357998)

### Rehberler
- [RaspberryTips - AP Kurulum Rehberi](https://raspberrytips.com/access-point-setup-raspberry-pi/)
- [DEV Community - 5 GHz AP + Client Mode](https://dev.to/andreamancuso/setting-up-a-wi-fi-access-point-on-raspberry-pi-with-5-ghz-and-client-mode-5a56)
- [RaspAP Dokumantasyon](https://docs.raspap.com/features-core/ap-basics/)
- [Debian Wiki - Bridge Proxy ARP](https://wiki.debian.org/BridgeNetworkConnectionsProxyArp)
