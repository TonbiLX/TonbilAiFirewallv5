---
phase: quick-22
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/models/device.py
  - backend/app/schemas/device.py
  - backend/app/api/v1/devices.py
  - backend/app/workers/dns_proxy.py
  - backend/app/hal/linux_nftables.py
  - backend/app/main.py
  - frontend/src/types/index.ts
  - frontend/src/pages/DeviceDetailPage.tsx
  - frontend/src/pages/DevicesPage.tsx
autonomous: true
requirements: [IPTV-01]
must_haves:
  truths:
    - "IPTV olarak isaretlenen cihazlarin DNS sorgulari filtrelenmeden direkt upstream'e yonlendirilir"
    - "Multicast (224.0.0.0/4) ve IGMP paketleri conntrack bypass ile tasinir"
    - "DeviceDetailPage'de IPTV toggle acilip kapatilabilir"
    - "DevicesPage'de IPTV cihazlari gorsel olarak isaretlenir"
  artifacts:
    - path: "backend/app/models/device.py"
      provides: "is_iptv Boolean column"
      contains: "is_iptv"
    - path: "backend/app/hal/linux_nftables.py"
      provides: "ensure_iptv_rules() fonksiyonu"
      contains: "ensure_iptv_rules"
    - path: "backend/app/workers/dns_proxy.py"
      provides: "IPTV cihaz DNS bypass mantigi"
      contains: "iptv:device_ids"
  key_links:
    - from: "backend/app/api/v1/devices.py"
      to: "Redis iptv:device_ids SET"
      via: "PATCH endpoint is_iptv field handling"
      pattern: "iptv:device_ids"
    - from: "backend/app/workers/dns_proxy.py"
      to: "Redis iptv:device_ids SET"
      via: "SISMEMBER check in handle_query"
      pattern: "iptv:device_ids"
    - from: "frontend/src/pages/DeviceDetailPage.tsx"
      to: "PATCH /devices/{id}"
      via: "updateDevice({ is_iptv })"
      pattern: "is_iptv"
---

<objective>
IPTV cihaz destegi ekle: is_iptv flag ile DNS filtreleme bypass, nftables multicast/IGMP notrack kurallari ve frontend toggle/badge.

Purpose: Vestel TV (192.168.1.158) gibi IPTV cihazlarinin Turkcell TV+ izlerken takilmasini onlemek. DNS filtreleme, conntrack ve multicast kurallari IPTV trafigini bozuyor.
Output: Backend is_iptv modeli + API + DNS bypass + nftables IPTV kurallari + frontend toggle + badge
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@backend/app/models/device.py
@backend/app/schemas/device.py
@backend/app/api/v1/devices.py
@backend/app/workers/dns_proxy.py
@backend/app/hal/linux_nftables.py
@backend/app/main.py
@frontend/src/types/index.ts
@frontend/src/pages/DeviceDetailPage.tsx
@frontend/src/pages/DevicesPage.tsx

<interfaces>
<!-- Mevcut Device modeli ve API yapisi -->

From backend/app/models/device.py:
```python
class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mac_address = Column(String(17), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    hostname = Column(String(255), nullable=True)
    is_blocked = Column(Boolean, default=False)
    is_online = Column(Boolean, default=True)
    bandwidth_limit_mbps = Column(Integer, nullable=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    # ... diger alanlar
```

From backend/app/schemas/device.py:
```python
class DeviceUpdate(BaseModel):
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    manufacturer: Optional[str] = None
    profile_id: Optional[int] = None

class DeviceResponse(BaseModel):
    id: int
    mac_address: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    is_blocked: bool = False
    is_online: bool = True
    bandwidth_limit_mbps: Optional[int] = None
    # ... diger alanlar
    class Config:
        from_attributes = True
```

From frontend/src/types/index.ts:
```typescript
export interface Device {
  id: number;
  mac_address: string;
  ip_address: string | null;
  hostname: string | null;
  is_blocked: boolean;
  is_online: boolean;
  bandwidth_limit_mbps: number | null;
  device_type: string | null;
  risk_score: number;
  risk_level: "safe" | "suspicious" | "dangerous";
  // ... diger alanlar
}
```

From backend/app/workers/dns_proxy.py handle_query():
```python
# Siralama: is_ip_blocked → source_type → device_blocked → query_type → custom_rule → whitelist → servis engelleme → profil/global blocklist → reputation
# IPTV bypass en basa (device_blocked kontrolunden ONCE) eklenmeli
```

From backend/app/hal/linux_nftables.py:
```python
NFT_BIN = "/usr/sbin/nft"
TABLE_NAME = "inet tonbilai"
async def run_nft(args: List[str], check: bool = True) -> str
async def ensure_tonbilai_table()
```

From backend/app/main.py lifespan():
```python
# Startup sirasi: DB tables → Redis → Driver → Seed → Firewall sync → VPN → DDoS → Security → WiFi → Bridge isolation → Category/Profile cache → Workers
# IPTV rules ensure_bridge_isolation'dan sonra, worker'lardan once eklenmeli
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — Device modeli + API + DNS proxy bypass + nftables IPTV kurallari</name>
  <files>
    backend/app/models/device.py
    backend/app/schemas/device.py
    backend/app/api/v1/devices.py
    backend/app/workers/dns_proxy.py
    backend/app/hal/linux_nftables.py
    backend/app/main.py
  </files>
  <action>
**1. Device modeli (`backend/app/models/device.py`):**
- `is_iptv = Column(Boolean, default=False)` ekle, `bandwidth_limit_mbps` satirindan sonra.

**2. Device schemalari (`backend/app/schemas/device.py`):**
- `DeviceUpdate` sinifina `is_iptv: Optional[bool] = None` ekle.
- `DeviceResponse` sinifina `is_iptv: bool = False` ekle.

**3. Device API (`backend/app/api/v1/devices.py`):**
- `update_device` PATCH endpoint'inde, `await db.flush()` satirindan sonra (profil degisikligi blogundan sonra), is_iptv degisikligi icin yeni blok ekle:
```python
# IPTV cihaz degisikligi → Redis iptv:device_ids SET guncelle
if "is_iptv" in update_data and device.ip_address:
    if device.is_iptv:
        await redis_client.sadd("iptv:device_ids", device.ip_address)
        _logger.info(f"IPTV cihaz eklendi: {device.hostname} ({device.ip_address})")
    else:
        await redis_client.srem("iptv:device_ids", device.ip_address)
        _logger.info(f"IPTV cihaz cikarildi: {device.hostname} ({device.ip_address})")
```

**4. Startup IPTV Redis sync (`backend/app/main.py`):**
- lifespan() icinde, bridge isolation blogundan sonra (satir ~487 civari), worker'lardan once:
```python
# IPTV cihazlari Redis'e sync et
try:
    from app.hal.linux_nftables import ensure_iptv_rules
    await ensure_iptv_rules()
    # IPTV cihaz IP'lerini Redis'e yukle
    async with async_session_factory() as session:
        from app.models.device import Device as DeviceModel
        result = await session.execute(
            select(DeviceModel).where(DeviceModel.is_iptv == True)
        )
        iptv_devices = result.scalars().all()
        if iptv_devices:
            iptv_ips = [d.ip_address for d in iptv_devices if d.ip_address]
            if iptv_ips:
                await redis_client.delete("iptv:device_ids")
                await redis_client.sadd("iptv:device_ids", *iptv_ips)
                logger.info(f"IPTV cihazlar Redis'e yuklendi: {len(iptv_ips)} cihaz")
    logger.info("IPTV nftables kurallari ve Redis sync hazir")
except Exception as e:
    logger.error(f"IPTV kurulum hatasi: {e}")
```
- Gerekli import'lar: `select` zaten mevcut, `async_session_factory` zaten mevcut (scan_devices'da kullaniliyor, import kontrolu yap).

**5. DNS Proxy bypass (`backend/app/workers/dns_proxy.py`):**
- `handle_query()` icinde, `self.stats["total_queries"] += 1` satirindan HEMEN SONRA (ve `blocked = False` satirindan ONCE), IPTV bypass kontrolu ekle:
```python
# IPTV cihaz bypass — tum filtrelemeyi atla, direkt upstream'e yonlendir
try:
    _dev_id_iptv = await self.redis.get(f"dns:ip_to_device:{client_ip}")
    if _dev_id_iptv:
        _is_iptv = await self.redis.sismember("iptv:device_ids", client_ip)
        if _is_iptv:
            # IPTV cihazi: filtreleme yok, direkt upstream
            response = await self.forward_to_upstream(data)
            if response:
                elapsed = (time.monotonic() - start_time) * 1000
                self.transport.sendto(response, addr)
                self.query_log.append({
                    "client_ip": client_ip,
                    "domain": domain,
                    "query_type": qtype_name,
                    "blocked": False,
                    "block_reason": "iptv_bypass",
                    "upstream_response_ms": elapsed,
                    "answer_ip": "",
                    "timestamp": datetime.utcnow(),
                    "destination_port": 53,
                    "wan_ip": get_wan_ip(),
                    "source_type": _source_type,
                })
            return
except Exception:
    pass
```
- AYRICA `handle_dot()` fonksiyonunda da (DoT handler) benzer bypass ekle. `handle_dot` icinde, qtype engelleme kontrolunden ONCE (blocking kontrol baslamadan once) ayni IPTV bypass mantigi ekle.

**6. nftables IPTV kurallari (`backend/app/hal/linux_nftables.py`):**
- Dosyanin sonuna `ensure_iptv_rules()` fonksiyonu ekle:
```python
async def ensure_iptv_rules():
    """IPTV multicast ve IGMP icin nftables kurallari.

    - Multicast (224.0.0.0/4) ve IGMP paketlerini notrack yap (conntrack bypass)
    - Forward chain'de multicast ve IGMP accept kurallari ekle
    """
    ruleset = await run_nft(["list", "ruleset"], check=False)

    # 1) raw_iptv tablosu — multicast + IGMP notrack
    if "table inet raw_iptv" not in ruleset:
        logger.info("IPTV raw tablosu olusturuluyor...")
        nft_commands = """
table inet raw_iptv {
    chain prerouting {
        type filter hook prerouting priority raw; policy accept;
        ip daddr 224.0.0.0/4 notrack
        ip protocol igmp notrack
    }
    chain output {
        type filter hook output priority raw; policy accept;
        ip daddr 224.0.0.0/4 notrack
        ip protocol igmp notrack
    }
}
"""
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=nft_commands.encode())
        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error(f"IPTV raw tablo olusturma hatasi: {err}")
        else:
            logger.info("IPTV raw tablosu olusturuldu (multicast + IGMP notrack)")
    else:
        logger.debug("IPTV raw tablosu zaten mevcut")

    # 2) inet tonbilai forward chain'e multicast + IGMP accept ekle
    forward_out = await run_nft(["list", "chain", "inet", "tonbilai", "forward"], check=False)

    if "ip daddr 224.0.0.0/4 accept" not in forward_out:
        await run_nft(
            ["insert", "rule", "inet", "tonbilai", "forward",
             "ip", "daddr", "224.0.0.0/4", "accept"],
            check=False,
        )
        logger.info("IPTV: forward multicast accept kurali eklendi")

    if "ip protocol igmp accept" not in forward_out:
        await run_nft(
            ["insert", "rule", "inet", "tonbilai", "forward",
             "ip", "protocol", "igmp", "accept"],
            check=False,
        )
        logger.info("IPTV: forward IGMP accept kurali eklendi")
```

**7. Migration SQL (main.py lifespan icinde):**
- Mevcut migration blogunun altina (satir ~433 civari, `for idx_stmt` blogundan sonra) ekle:
```python
# Migration: devices tablosuna is_iptv sutunu
try:
    await conn.execute(text("ALTER TABLE devices ADD COLUMN is_iptv BOOLEAN DEFAULT FALSE"))
    logger.info("Migration OK: devices.is_iptv sutunu eklendi")
except Exception:
    pass  # Sutun zaten varsa sessizce gec
```

**ONEMLI NOTLAR:**
- DNS proxy'de `forward_to_upstream` metodu mevcut — upstream DNS'e sorgu yonlendirmesi icin kullanilan mevcut metod. Kullanmadan once `self` uzerinde hangi isimle tanimli oldugunu kontrol et. dns_proxy.py'de `_forward_query` veya `_query_upstream` olarak da tanimli olabilir — dosyadaki gercek metod adini kullan.
- `handle_dot()` fonksiyonunda da IPTV bypass eklemeyi UNUTMA. DoT (DNS-over-TLS) uzerinden gelen sorgular da bypass edilmeli.
- Redis key: `iptv:device_ids` — bu bir SET, IP adresleri icerir (device_id degil). Cihazin IP adresi degisirse eski IP'yi silmek gerekir ama bu edge case simdilik ihmal edilebilir (cihaz IP'si genelde sabit).
  </action>
  <verify>
    Backend dosyalari syntax kontrolu:
    - `python -c "import ast; ast.parse(open('backend/app/models/device.py').read())"` hata vermez
    - `python -c "import ast; ast.parse(open('backend/app/schemas/device.py').read())"` hata vermez
    - `python -c "import ast; ast.parse(open('backend/app/api/v1/devices.py').read())"` hata vermez
    - `python -c "import ast; ast.parse(open('backend/app/hal/linux_nftables.py').read())"` hata vermez
    - `grep -c "is_iptv" backend/app/models/device.py` en az 1 sonuc verir
    - `grep -c "ensure_iptv_rules" backend/app/hal/linux_nftables.py` en az 1 sonuc verir
    - `grep -c "iptv:device_ids" backend/app/workers/dns_proxy.py` en az 1 sonuc verir
    - `grep -c "iptv:device_ids" backend/app/api/v1/devices.py` en az 1 sonuc verir
    - `grep -c "ensure_iptv_rules" backend/app/main.py` en az 1 sonuc verir
  </verify>
  <done>
    - Device modelinde is_iptv Boolean kolonu mevcut
    - DeviceUpdate ve DeviceResponse semalarinda is_iptv alani mevcut
    - PATCH /devices/{id} endpoint'i is_iptv degisikliginde Redis iptv:device_ids SET'ini gunceller
    - DNS proxy handle_query ve handle_dot'ta IPTV cihazlari tum filtrelemeyi bypass eder
    - nftables ensure_iptv_rules() multicast notrack + forward accept kurallari olusturur
    - main.py lifespan'da is_iptv migration + IPTV rules + Redis sync calisir
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — IPTV toggle (DeviceDetailPage) + IPTV badge (DevicesPage)</name>
  <files>
    frontend/src/types/index.ts
    frontend/src/pages/DeviceDetailPage.tsx
    frontend/src/pages/DevicesPage.tsx
  </files>
  <action>
**1. TypeScript tip (`frontend/src/types/index.ts`):**
- `Device` interface'ine `is_iptv: boolean;` ekle, `bandwidth_limit_mbps` satirindan sonra.

**2. DeviceDetailPage.tsx — IPTV Toggle:**
- Lucide import'larina `Tv2` (veya mevcut `Tv` kullan) ekle.
- "Cihaz Bilgileri" GlassCard'inda, "Bant Genisligi" bölümünden SONRA (satir ~924 civari, `</div>` kapanisinin hemen oncesine), IPTV toggle ekle:

```tsx
{/* IPTV Cihazi */}
<div className="flex items-center justify-between">
  <div className="flex flex-col">
    <span className="text-xs text-gray-500 uppercase tracking-wide">IPTV Cihazi</span>
    <span className="text-[10px] text-gray-600 mt-0.5">DNS filtreleme devre disi, multicast oncelikli</span>
  </div>
  <button
    onClick={async () => {
      try {
        await updateDevice(device.id, { is_iptv: !device.is_iptv });
        setFeedback({
          type: 'success',
          message: device.is_iptv ? 'IPTV modu kapatildi.' : 'IPTV modu acildi. DNS filtreleme devre disi.'
        });
        await loadDevice();
      } catch {
        setFeedback({ type: 'error', message: 'IPTV durumu guncellenirken hata olustu.' });
      }
    }}
    className={`relative w-11 h-6 rounded-full transition-all duration-300 ${
      device.is_iptv
        ? 'bg-neon-cyan/30 border border-neon-cyan/50 shadow-[0_0_10px_rgba(0,240,255,0.3)]'
        : 'bg-white/10 border border-white/20'
    }`}
  >
    <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-all duration-300 ${
      device.is_iptv
        ? 'translate-x-5 bg-neon-cyan shadow-[0_0_8px_rgba(0,240,255,0.5)]'
        : 'translate-x-0 bg-gray-500'
    }`} />
  </button>
</div>
```

**3. DevicesPage.tsx — IPTV badge:**
- Cihaz kartindaki hostname satirinda (satir ~558 civari), hostname metninden sonra ve Pencil butonundan once, IPTV badge ekle:

```tsx
{device.is_iptv && (
  <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20">
    <Tv size={10} />
    IPTV
  </span>
)}
```

- Bu badge, hostname ile edit butonu arasina yerlestirilmeli:
```
{device.hostname || "Bilinmeyen Cihaz"}  →  {is_iptv badge}  →  <Pencil> butonu
```

- `Tv` zaten import edilmis (satir 29'da `Tv` import'u mevcut), ekstra import gerekmez.

**CYBERPUNK TEMA UYUMLULUGU:**
- Toggle switch: neon-cyan (#00F0FF) glow efekti acikken, gri kapaninca
- Badge: neon-cyan arka plan/border ile kucuk IPTV etiketi
- Tum renkler mevcut Tailwind config'deki `neon-cyan`, `neon-green` vb. siniflarla uyumlu
  </action>
  <verify>
    Frontend build kontrolu:
    - `cd frontend && npx tsc --noEmit` hata vermez (veya mevcut hatalar disinda yeni hata uretmez)
    - `grep -c "is_iptv" frontend/src/types/index.ts` en az 1 sonuc verir
    - `grep -c "IPTV" frontend/src/pages/DeviceDetailPage.tsx` en az 2 sonuc verir (toggle + aciklama)
    - `grep -c "IPTV" frontend/src/pages/DevicesPage.tsx` en az 1 sonuc verir (badge)
  </verify>
  <done>
    - Device TypeScript interface'inde is_iptv alani mevcut
    - DeviceDetailPage'de cyberpunk temali IPTV toggle switch calisiyor
    - Toggle acildiginda PATCH /devices/{id} ile is_iptv: true gonderiliyor
    - DevicesPage'de IPTV cihazlari kucuk neon-cyan "IPTV" badge'i ile isaretleniyor
  </done>
</task>

</tasks>

<verification>
1. Backend: `is_iptv` kolonu Device modelinde, DeviceUpdate/DeviceResponse semalarinda mevcut
2. API: PATCH endpoint is_iptv degisikliginde Redis `iptv:device_ids` SET guncelleniyor
3. DNS Proxy: IPTV cihazlarin sorgulari `iptv_bypass` olarak loglanip filtresiz yonlendiriliyor
4. nftables: `table inet raw_iptv` multicast+IGMP notrack, `inet tonbilai forward` multicast+IGMP accept
5. Startup: Migration + ensure_iptv_rules + Redis sync lifespan'da calisiyor
6. Frontend: DeviceDetailPage toggle + DevicesPage badge gorsel olarak calisiyor
</verification>

<success_criteria>
- IPTV olarak isaretlenen cihazin DNS sorgulari filtrelenmeden upstream'e yonlendiriliyor
- Multicast ve IGMP paketleri conntrack'ten gecmeden kabul ediliyor (notrack)
- DeviceDetailPage'de IPTV toggle acilip kapatilabiliyor (neon-cyan glow efekti ile)
- DevicesPage'de IPTV cihazlar kucuk TV ikonlu badge ile isaretleniyor
- Backend restart sonrasi IPTV cihazlar otomatik Redis'e yukleniyor
</success_criteria>

<output>
After completion, create `.planning/quick/22-iptv-cihaz-destegi-device-iptv-toggle-mu/22-SUMMARY.md`
</output>
