# Bridge Izolasyonu — Seffaf Koprudan Router Moduna Gecis

## Ozet

Pi (.2) uzerindeki seffaf kopruyu (transparent bridge) izole router moduna cevir.
Modem (.1) sadece Pi'yi gorsun, bireysel LAN cihazlari modemden tamamen gizlensin.

---

## Mevcut Durum

```
[Cihazlar] ←─ eth1 ─→ br0 (bridge) ←─ eth0 ─→ [ZTE Modem .1] ←→ Internet
                          │
                       Pi (.2)
```

- br0 = eth0 + eth1 (seffaf kopru)
- Modem tum cihazlarin MAC'lerini gorebiliyor
- DHCP gateway: .1 (modem)
- DNS: .2 (Pi)
- MASQUERADE + MAC rewrite aktif (bridge_masquerade_fix)

## Hedef Durum

```
[Cihazlar] ←─ eth1 ─→ br0 ──Pi IP Stack── br0 ←─ eth0 ─→ [ZTE Modem .1]
                       (L2 forwarding KAPALI)
                          │
                       Pi (.2)
                    Gateway + NAT
```

- Bridge L2 forwarding tamamen engelli (eth0↔eth1 arasi)
- Tum trafik Pi'nin IP stack'i uzerinden route edilir
- Modem sadece Pi'nin MAC/IP'sini gorur
- DHCP gateway: .2 (Pi)
- MAC rewrite gereksiz (Pi kendi MAC'i ile gonderir)

---

## ADIM 1: linux_nftables.py — Bridge Izolasyon Fonksiyonlari

### Dosya: `backend/app/hal/linux_nftables.py`

### 1a. Yeni fonksiyon: `ensure_bridge_isolation()`

Satir ~960 civarına (mevcut `ensure_bridge_masquerade()` yerine) eklenecek:

```python
async def ensure_bridge_isolation():
    """Bridge izolasyonu: L2 forwarding engelle, router moduna gec.

    Modem sadece Pi'yi gorur. Tum trafik Pi'nin IP stack'inden gecer.
    """
    # 1. ip_forward aktif oldugundan emin ol
    await _run_system_cmd(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

    # 2. br_netfilter yuklu oldugundan emin ol
    await _run_system_cmd(["sudo", "modprobe", "br_netfilter"], check=False)
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"], check=False
    )

    # 3. ICMP redirect'leri devre disi birak
    # (Pi, cihazlara "dogrudan .1'e git" demeyecek)
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.all.send_redirects=0"], check=False
    )
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.br0.send_redirects=0"], check=False
    )

    # 4. Bridge forward zincirinde izolasyon kurallari
    wan_iface = await _get_wan_bridge_port()  # "eth0"
    ruleset = await run_nft(["list", "ruleset"], check=False)

    if "bridge_isolation_lan_wan" not in ruleset:
        # LAN -> WAN dogrudan L2 iletimi engelle
        await run_nft([
            "add", "rule", "bridge", "filter", "forward",
            "iifname", "eth1", "oifname", wan_iface, "drop",
            "comment", '"bridge_isolation_lan_wan"',
        ])
        logger.info(f"Bridge izolasyon: eth1->{wan_iface} forwarding engellendi")

    if "bridge_isolation_wan_lan" not in ruleset:
        # WAN -> LAN dogrudan L2 iletimi engelle
        await run_nft([
            "add", "rule", "bridge", "filter", "forward",
            "iifname", wan_iface, "oifname", "eth1", "drop",
            "comment", '"bridge_isolation_wan_lan"',
        ])
        logger.info(f"Bridge izolasyon: {wan_iface}->eth1 forwarding engellendi")

    # 5. MASQUERADE kuralinin varligini dogrula
    lan_subnet = await _detect_lan_subnet()
    if "bridge_lan_masq" not in ruleset:
        await ensure_nat_postrouting_chain()
        masq_rule = (
            f'add rule inet nat postrouting '
            f'ip saddr {lan_subnet} ip daddr != {lan_subnet} '
            f'masquerade comment "bridge_lan_masq"'
        )
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=masq_rule.encode())
        if proc.returncode != 0:
            logger.error(f"MASQUERADE kurali eklenemedi: {stderr.decode().strip()}")
        else:
            logger.info(f"MASQUERADE kurali eklendi ({lan_subnet})")

    # 6. Eski bridge masquerade_fix tablosunu kaldir (MAC rewrite artik gereksiz)
    if BRIDGE_MASQ_TABLE in ruleset:
        await run_nft(["delete", "table", BRIDGE_MASQ_TABLE], check=False)
        logger.info("Eski bridge masquerade_fix tablosu kaldirildi (router modunda gereksiz)")

    # 7. Persist
    await persist_nftables()
    logger.info("Bridge izolasyonu aktif — router modu")
```

### 1b. Yeni fonksiyon: `remove_bridge_isolation()`

```python
async def remove_bridge_isolation():
    """Bridge izolasyonunu kaldir (seffaf kopru moduna don)."""
    out = await run_nft(["-a", "list", "chain", "bridge", "filter", "forward"], check=False)
    if out:
        for line in out.splitlines():
            if "bridge_isolation" in line and "handle" in line:
                handle_match = re.search(r"handle\s+(\d+)", line)
                if handle_match:
                    handle = handle_match.group(1)
                    await run_nft([
                        "delete", "rule", "bridge", "filter", "forward",
                        "handle", handle,
                    ], check=False)

    # ICMP redirect'leri geri ac
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.all.send_redirects=1"], check=False
    )

    await persist_nftables()
    logger.info("Bridge izolasyonu kaldirildi — seffaf kopru moduna donuldu")
```

### 1c. `ensure_bridge_masquerade()` fonksiyonunu kaldir veya deprecated isaretle

Bu fonksiyon artik gereksiz. `ensure_bridge_isolation()` ayni isi yapiyor.
`remove_bridge_masquerade()` fonksiyonunu da kaldir.

---

## ADIM 2: linux_nftables.py — Bridge Accounting Yeniden Yapılandırma

### Dosya: `backend/app/hal/linux_nftables.py`

### 2a. `ensure_bridge_accounting_chain()` guncelle

Eski (forward hook):
```python
table bridge accounting {
    chain per_device {
        type filter hook forward priority -2; policy accept;
    }
}
```

Yeni (input + output hooks):
```python
table bridge accounting {
    chain upload {
        type filter hook input priority -2; policy accept;
        # iifname "eth1" ether saddr MAC counter "bw_MAC_up"
    }
    chain download {
        type filter hook output priority -2; policy accept;
        # oifname "eth1" ether daddr MAC counter "bw_MAC_down"
    }
}
```

Gecis stratejisi:
1. Eski `per_device` chain varsa, counter degerlerini oku (kaybet)
2. Eski chain'i sil
3. Yeni `upload` ve `download` chain'lerini olustur
4. Mevcut counter kurallarini yeni chain'lere tasi

### 2b. `add_device_counter(mac)` guncelle

Eski:
```python
# per_device chain'e 2 kural ekle
await run_nft(["add", "rule", "bridge", "accounting", "per_device",
    "ether", "saddr", mac, "counter", "comment", f'"bw_{mac}_up"'])
await run_nft(["add", "rule", "bridge", "accounting", "per_device",
    "ether", "daddr", mac, "counter", "comment", f'"bw_{mac}_down"'])
```

Yeni:
```python
# upload chain'e saddr kurali (eth1'den gelen = cihazdan upload)
await run_nft(["add", "rule", "bridge", "accounting", "upload",
    "iifname", "eth1", "ether", "saddr", mac,
    "counter", "comment", f'"bw_{mac}_up"'])

# download chain'e daddr kurali (eth1'e giden = cihaza download)
await run_nft(["add", "rule", "bridge", "accounting", "download",
    "oifname", "eth1", "ether", "daddr", mac,
    "counter", "comment", f'"bw_{mac}_down"'])
```

### 2c. `remove_device_counter(mac)` guncelle

Her iki chain'den (`upload` ve `download`) handle ile sil.
Mevcut mantik ayni, sadece chain adi degisiyor.

### 2d. `read_device_counters()` guncelle

Eski: tek chain oku
```python
out = await run_nft(["list", "chain", "bridge", "accounting", "per_device"])
```

Yeni: iki chain oku ve birlestir
```python
out_up = await run_nft(["list", "chain", "bridge", "accounting", "upload"], check=False)
out_down = await run_nft(["list", "chain", "bridge", "accounting", "download"], check=False)
combined = (out_up or "") + "\n" + (out_down or "")
# Ayni regex ile parse et (comment formati ayni)
```

### 2e. `sync_device_counters(macs)` guncelle

Ayni mantik, `BRIDGE_CHAIN` yerine `"upload"` ve `"download"` chain isimlerini kullan.

---

## ADIM 3: linux_tc.py — TC Marking Yeniden Yapılandırma

### Dosya: `backend/app/hal/linux_tc.py`

### 3a. `_ensure_tc_mark_chain()` guncelle

Eski:
```python
table bridge accounting {
    chain tc_mark {
        type filter hook forward priority -1; policy accept;
    }
}
```

Yeni:
```python
table bridge accounting {
    chain tc_mark_up {
        type filter hook input priority -1; policy accept;
    }
    chain tc_mark_down {
        type filter hook output priority -1; policy accept;
    }
}
```

### 3b. `add_device_limit(mac, rate, ceil)` guncelle

Eski mark kurallari:
```python
# Upload (ether saddr) + Download (ether daddr) ayni chain
await run_nft(["add", "rule", "bridge", "accounting", "tc_mark",
    "ether", "saddr", mac, "meta", "mark", "set", str(mark)])
await run_nft(["add", "rule", "bridge", "accounting", "tc_mark",
    "ether", "daddr", mac, "meta", "mark", "set", str(mark)])
```

Yeni:
```python
# Upload: bridge input, eth1'den gelen
await run_nft(["add", "rule", "bridge", "accounting", "tc_mark_up",
    "iifname", "eth1", "ether", "saddr", mac,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac}_up"'])

# Download: bridge output, eth1'e giden
await run_nft(["add", "rule", "bridge", "accounting", "tc_mark_down",
    "oifname", "eth1", "ether", "daddr", mac,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac}_down"'])
```

### 3c. `remove_device_limit(mac)` ve `_remove_nft_mark_rule(mac)` guncelle

Her iki chain'den mark kurallarini temizle.

### 3d. TC qdisc degisikligi YOK

HTB qdiscleri eth0 ve eth1 uzerinde aynen kalir. Mark'lar SKB uzerinde
IP stack routing sirasinda korunur.

---

## ADIM 4: main.py — Startup Guncelleme

### Dosya: `backend/app/main.py`

### 4a. `lifespan()` fonksiyonunda degisiklik

Eski (satir ~319-327):
```python
# Bridge masquerade: modem/router uyumlulugu
try:
    from app.hal.linux_nftables import ensure_bridge_masquerade
    await ensure_bridge_masquerade()
    logger.info("Bridge masquerade kurallari hazir (modem uyumlulugu)")
except Exception as e:
    logger.error(f"Bridge masquerade kurulum hatasi: {e}")
```

Yeni:
```python
# Bridge izolasyonu: router modu — modem cihazlari goremez
try:
    from app.hal.linux_nftables import ensure_bridge_isolation
    await ensure_bridge_isolation()
    logger.info("Bridge izolasyonu aktif (router modu)")
except Exception as e:
    logger.error(f"Bridge izolasyon hatasi: {e}")
```

---

## ADIM 5: DHCP Gateway Degisikligi

### 5a. Pi uzerinde config dosyasi guncelle (SSH ile)

```bash
# /etc/dnsmasq.d/pool-1.conf icinde:
# Eski: dhcp-option=3,192.168.1.1
# Yeni: dhcp-option=3,192.168.1.2
sudo sed -i 's/dhcp-option=3,192.168.1.1/dhcp-option=3,192.168.1.2/' /etc/dnsmasq.d/pool-1.conf

# dnsmasq reload
sudo systemctl reload dnsmasq
```

### 5b. Veritabanini guncelle (SSH ile)

```bash
# MariaDB'de dhcp_pools tablosundaki gateway'i guncelle
sudo mysql -u root tonbilaios -e "UPDATE dhcp_pools SET gateway='192.168.1.2' WHERE gateway='192.168.1.1';"
```

### 5c. Ana dnsmasq.conf kontrolu

`/etc/dnsmasq.conf` icindeki statik dhcp-host satirlarinda gateway yok,
sadece MAC-IP eslesmesi var. Degisiklik gerektirmez.

---

## ADIM 6: Pi Uzerinde Temizlik ve Uygulama (SSH)

### 6a. Sirayla calistirilacak komutlar:

```bash
# 1. Bridge masquerade_fix tablosunu sil (MAC rewrite artik gereksiz)
sudo nft delete table 'bridge masquerade_fix' 2>/dev/null

# 2. Bridge forward'a izolasyon kurallari ekle
sudo nft add rule bridge filter forward iifname eth1 oifname eth0 drop comment '"bridge_isolation_lan_wan"'
sudo nft add rule bridge filter forward iifname eth0 oifname eth1 drop comment '"bridge_isolation_wan_lan"'

# 3. ICMP redirect devre disi
sudo sysctl -w net.ipv4.conf.all.send_redirects=0
sudo sysctl -w net.ipv4.conf.br0.send_redirects=0

# 4. DHCP gateway degistir
sudo sed -i 's/dhcp-option=3,192.168.1.1/dhcp-option=3,192.168.1.2/' /etc/dnsmasq.d/pool-1.conf
sudo systemctl reload dnsmasq

# 5. DB guncelle
sudo mysql -u root tonbilaios -e "UPDATE dhcp_pools SET gateway='192.168.1.2' WHERE gateway='192.168.1.1';"

# 6. sysctl kalici yap
echo 'net.ipv4.conf.all.send_redirects=0' | sudo tee -a /etc/sysctl.d/99-bridge-isolation.conf
echo 'net.ipv4.conf.br0.send_redirects=0' | sudo tee -a /etc/sysctl.d/99-bridge-isolation.conf

# 7. nftables persist
sudo nft list ruleset | sudo tee /tmp/nft_check.txt > /dev/null
echo '#!/usr/sbin/nft -f' | sudo tee /etc/nftables.conf > /dev/null
echo 'flush ruleset' | sudo tee -a /etc/nftables.conf > /dev/null
echo '' | sudo tee -a /etc/nftables.conf > /dev/null
sudo nft list ruleset | sudo tee -a /etc/nftables.conf > /dev/null
```

### 6b. Bridge accounting gecisi (eski forward → yeni input/output)

```bash
# Eski per_device chain'ini sil (veriler kaybolur - beklenen)
sudo nft delete chain bridge accounting per_device 2>/dev/null
sudo nft delete chain bridge accounting tc_mark 2>/dev/null

# Yeni chain'leri olustur
sudo nft add chain bridge accounting upload '{ type filter hook input priority -2; policy accept; }'
sudo nft add chain bridge accounting download '{ type filter hook output priority -2; policy accept; }'

# TC mark chain'lerini olustur
sudo nft add chain bridge accounting tc_mark_up '{ type filter hook input priority -1; policy accept; }'
sudo nft add chain bridge accounting tc_mark_down '{ type filter hook output priority -1; policy accept; }'
```

---

## ADIM 7: Dogrulama Testleri

### 7a. Modem izolasyonu
```bash
# Modem ARP tablosunda sadece Pi olmali
# Pi uzerinden: (modem'e SSH ile erisim yoksa, tcpdump ile dogrula)
sudo tcpdump -i eth0 arp -c 20  # Sadece Pi'nin ARP'leri gorunmeli
```

### 7b. Cihaz internet erisimi
```bash
# Mevcut cihazlar icin conntrack kontrolu
sudo conntrack -L | grep 192.168.1.57 | grep ESTABLISHED | wc -l  # > 0
sudo conntrack -L | grep 192.168.1.39 | grep ESTABLISHED | wc -l  # > 0
```

### 7c. Yapay cihaz testi
```bash
# Namespace + veth ile test cihazi olustur
sudo ip netns add ns_test
sudo ip link add vtest type veth peer name vtest_br
sudo ip link set vtest_br master br0 && sudo ip link set vtest_br up
sudo ip link set vtest netns ns_test
sudo ip netns exec ns_test ip link set vtest address 02:aa:bb:cc:dd:01
sudo ip netns exec ns_test ip link set vtest up
sudo ip netns exec ns_test busybox udhcpc -i vtest -s /tmp/udhcpc_script.sh -n -q

# Gateway .2 mi kontrol et
sudo ip netns exec ns_test ip route show  # "default via 192.168.1.2" olmali

# Internet erisimi
sudo ip netns exec ns_test curl -s --connect-timeout 10 -o /dev/null -w '%{http_code}' https://www.google.com
# 200 beklenir

# Temizlik
sudo ip netns del ns_test
```

### 7d. Bridge forwarding engeli dogrulama
```bash
# Bridge forwarding istatistikleri - 0 olmali
sudo nft list chain bridge filter forward  # drop kurallari gorunmeli
```

### 7e. Pi internet erisimi
```bash
curl -s --connect-timeout 5 -o /dev/null -w '%{http_code}' https://www.google.com  # 200
```

### 7f. DNS calisiyor mu
```bash
dig +short google.com @127.0.0.1  # IP donmeli
```

### 7g. Bridge accounting calisiyor mu
```bash
sudo nft list chain bridge accounting upload   # counter'lar artmali
sudo nft list chain bridge accounting download # counter'lar artmali
```

---

## Geri Alma (Rollback)

Sorun cikarsa seffaf kopru moduna donmek icin:

```bash
# 1. Izolasyon kurallarini kaldir
sudo nft -a list chain bridge filter forward
# handle numaralarini bul ve sil:
sudo nft delete rule bridge filter forward handle XX
sudo nft delete rule bridge filter forward handle YY

# 2. DHCP gateway'i .1'e geri al
sudo sed -i 's/dhcp-option=3,192.168.1.2/dhcp-option=3,192.168.1.1/' /etc/dnsmasq.d/pool-1.conf
sudo systemctl reload dnsmasq

# 3. ICMP redirect geri ac
sudo sysctl -w net.ipv4.conf.all.send_redirects=1

# 4. Bridge masquerade_fix'i geri yukle (gerekirse)
# ensure_bridge_masquerade() cagir

# 5. nftables persist
```

---

## Etki Analizi

| Bilesen | Etki | Aciklama |
|---------|------|----------|
| Cihaz IP'leri | DEGISMEZ | Ayni subnet (192.168.1.x) |
| DNS | DEGISMEZ | Zaten .2 uzerinde |
| VPN Server (wg0) | DEGISMEZ | wg0 bagimsiz interface |
| Fail2ban | DEGISMEZ | SSH korumasi devam |
| DDoS koruma | DEGISMEZ | inet tonbilai tablosu aynen |
| Bandwidth accounting | GUNCELLENIR | forward → input/output |
| TC bandwidth limit | GUNCELLENIR | forward → input/output marking |
| DHCP gateway | DEGISIR | .1 → .2 |
| Bridge MAC rewrite | KALDIRILIR | Router modunda gereksiz |
