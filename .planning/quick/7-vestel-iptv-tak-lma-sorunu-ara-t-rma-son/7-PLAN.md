---
plan_type: quick
task: "Vestel IPTV takılma sorunu — Redis sızıntı fix + eth1 ring buffer + poll interval optimizasyonu"
scope: backend performance fixes
estimated_tasks: 3
---

# Quick Plan 7: IPTV Streaming Performans Düzeltmeleri

## Bağlam

Vestel IPTV kutusu son değişikliklerden sonra görüntü takılarak ilerliyor. Paralel araştırma sonuçları:

1. **Redis client sızıntısı**: 1000 TCP bağlantı açık, Redis yeni komut kabul edemiyor
2. **eth1 ring buffer**: 100 (max 4096) — LAN tarafında paket kaybı
3. **POLL_INTERVAL=3s**: Dakikada 83 sudo çağrısı — gereksiz overhead
4. **IRQ dağılımı**: Tüm ağ interrupt'ları CPU0'da yığılmış

Vestel cihazına bandwidth limiti, profil, DNS filtreleme veya servis engeli uygulanmamış.

## Tasks

### Task 1: Redis bağlantı havuzu düzeltmesi
**files:** `backend/app/db/redis_client.py`
**action:** Redis client oluşturmada connection pool max_connections ve socket_timeout ekle. Singleton pattern ile tüm worker'ların aynı pool'u kullanmasını sağla.
**verify:** Redis client dosyasında max_connections ve timeout parametreleri mevcut
**done:** Redis bağlantı sızıntısı önlenmiş

### Task 2: Bandwidth monitor ve flow tracker poll interval optimizasyonu
**files:** `backend/app/workers/bandwidth_monitor.py`, `backend/app/workers/flow_tracker.py`
**action:**
- POLL_INTERVAL: 3 → 10 saniye (bandwidth monitor)
- wg show çağrısını ayrı interval ile 30 saniyeye çıkar
- Flow tracker conntrack -L timeout'unu 10 saniyeye düşür
**verify:** POLL_INTERVAL=10, wg interval=30, conntrack timeout=10
**done:** Sudo çağrıları dakikada 83'ten ~20'ye düşmüş

### Task 3: Pi'de eth1 ring buffer + IRQ fix deploy
**files:** deploy script (SSH)
**action:**
- `sudo ethtool -G eth1 rx 4096` — ring buffer artır
- RPS ayarı kontrol ve düzelt: `/sys/class/net/eth0/queues/rx-0/rps_cpus` = `f`
- Redis bağlantıları temizle: backend restart
- Değişiklikleri sysctl/rc.local ile kalıcı yap
**verify:** eth1 ring buffer 4096, RPS tüm core'larda, Redis bağlantı sayısı düşük
**done:** Pi performans iyileştirmeleri uygulanmış
