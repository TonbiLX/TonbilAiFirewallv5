# Quick 28 — Android App Bug Fixes + DDoS Harita

## Tamamlanan İşler

### BUG 1: Trafik JSON Parse ✅
- `SecurityDtos.kt` → `bpsIn/bpsOut` Long→Double
- `TrafficScreen.kt` → `formatSpeed(Double)` overload
- `SecurityScreen.kt` → `formatBps(Double)`

### BUG 3: Sistem Logları detay eksik ✅
- `SystemLogsScreen.kt` → action, hostname gösterimi eklendi

### BUG 4: IP Reputation mesaj yanlış ✅
- `IpReputationViewModel.kt` → başarılı test "basarili:" prefix

### Trafik Cihazlar sekmesi 0 değerler ✅
- `ExtendedDtos.kt` → `TrafficPerDeviceDto` SerialName düzeltmesi
  - `total_upload` → `upload_bytes`, `total_download` → `download_bytes`
  - `upload_speed` → `upload_bps`, `download_speed` → `download_bps`
  - `total_packets` → `connection_count`

### DDoS Saldırı Haritası ✅
- **DTO tamamen yeniden yazıldı** (`DdosFullDtos.kt`):
  - Backend field isimleri eşleştirildi: `ip`, `lat`, `lon`, `type`, `packets`, `bytes`
  - `DdosTargetDto`, `DdosAttackSummaryDto` eklendi (nested summary desteği)
  - `isp`, `bytes` field'ları eklendi
- **Canvas dünya haritası** (`DdosWorldMap.kt` — yeni dosya):
  - Compose Canvas ile polygon tabanlı kıta konturları (filled + stroke border)
  - 11 polygon: NA, SA, Europe, Africa, Asia, Australia, Greenland, UK, Japan, NZ, Madagascar
  - Mercator projeksiyon, grid arka plan
  - Saldırı çizgileri (dashed + glow) + pulsing noktalar
  - Hedef (Türkiye) pulsing cyan nokta
  - Renk kodlaması: SYN=kırmızı, UDP=amber, ICMP=magenta, Conn=mor
- **DdosMapScreen.kt güncellendi**: Harita + legend + ISP/bytes gösterimi

## Sonraki Oturum İçin Kalan İşler

### NAV BAR: Direkt Sayfa Geçişi (ÖNCELİKLİ)
- **İstek:** Alt navbar'dan bir ikona tıklayınca, hangi sayfada olursak olalım, direkt o sayfa açılsın. Geri çıkmaya gerek kalmasın.
- **Çözüm:** Navigation'da `popUpTo` + `launchSingleTop` kullanılmalı. Her navbar tıklamasında mevcut backstack temizlenip hedef sayfa açılmalı.
- **Dosyalar:** `MainNavHost.kt` veya `AppNavigation.kt` + `BottomNavBar.kt` incelenecek

### DDoS Haritası — İyileştirmeler (İSTEĞE BAĞLI)
- Harita polygon'ları daha da detaylandırılabilir
- Zoom/pan desteği eklenebilir
