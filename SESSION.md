# Quick 29 — Nav Fix + Sort Chips + Cihaz Yönetim Hazırlık

## Tamamlanan İşler

### 1. Bottom Nav Direkt Navigasyon ✅
- `popUpTo<DashboardRoute>` — SplashRoute/LoginRoute sorununu çözdü
- `saveState/restoreState` kaldırıldı — alt sayfada kalma sorunu giderildi
- Child route eşleştirmesi — alt sayfalarda doğru tab highlighted
- **Dosya:** `BottomNavBar.kt`

### 2. Sıralama Butonları (Sort Chips) ✅
- **TrafficScreen** — 4 tab'a sıralama eklendi:
  - Canlı: Hız↓, Boyut↓, Protokol, İsim
  - Büyük: Boyut↓, Hız↓, Hedef
  - Geçmiş: Yeni Önce, Eski Önce, Boyut↓, Hedef
  - Cihazlar: Hız↓, Upload↓, Download↓, İsim
- **SystemLogsScreen** — Yeni Önce, Eski Önce, Önem↓, Kategori
- Cyberpunk glassmorphism chip tasarımı, seçili=cyan
- **Dosyalar:** `TrafficScreen.kt`, `SystemLogsScreen.kt`

### 3. Cihaz Yönetim Altyapı (Kısmen) ✅
- `DeviceResponseDto` → `isIptv`, `deviceType`, `riskScore`, `riskLevel` eklendi
- `DeviceUpdateDto` → `isIptv` eklendi
- `DeviceDetailViewModel` → `updateHostname()`, `updateBandwidth()`, `toggleIptv()` eklendi
- **Dosyalar:** `DeviceDto.kt`, `DeviceDetailViewModel.kt`

## Sonraki Oturum — Cihaz Yönetim Tab (ÖNCELİKLİ)

### DeviceDetailScreen 4. Tab: "Yönetim"
Aşağıdakilerin UI'ını ekle:

1. **Hostname düzenleme** — text field + kaydet butonu
   - `viewModel.updateHostname(name)` kullan
2. **Bandwidth limit** — slider (0-100 Mbps) + sayı gösterimi
   - `viewModel.updateBandwidth(mbps)` kullan, null=limitsiz
3. **IPTV modu toggle** — Switch
   - `viewModel.toggleIptv()` kullan
4. **Servis Engelleme butonu** → DeviceServicesScreen'e navigate
   - `onNavigateToServices` callback ekle
   - `AppNavHost.kt`'de DeviceDetailScreen'e navigation parametresi geç
   - DeviceServicesRoute(deviceId, deviceName) kullan
5. **Engelle/Kaldır butonu** (zaten var ama tab'a da ekle)
6. **Cihaz bilgi kartı** — MAC, IP, üretici, cihaz tipi, risk skoru

### Navigation Değişikliği
- `DeviceDetailScreen` → `onNavigateToServices: (deviceId: Int, deviceName: String) -> Unit` parametresi ekle
- `AppNavHost.kt` → DeviceDetailRoute composable'da:
  ```kotlin
  onNavigateToServices = { id, name ->
      navController.navigate(DeviceServicesRoute(id.toString(), name))
  }
  ```

### Mevcut Altyapı (Hazır)
- `DeviceServicesScreen` + `DeviceServicesViewModel` → tam çalışıyor
- `DeviceServiceRepository` → toggle, bulk update hazır
- `DeviceRepository.updateBandwidth()` → hazır
- Backend endpoint'ler: devices/{id}/bandwidth, services/devices/{id}/toggle
