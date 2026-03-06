# Phase 6: Project Skeleton - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Gelistirme ortami hazir, bos Compose uygulamasi cihazda baslatilabiliyor, cyberpunk tema uygulanmis, navigasyon calisiyor, API client backend'e baglanabiliyor. Android projesi iskeleti — henuz ekran icerigi yok, sadece altyapi.

</domain>

<decisions>
## Implementation Decisions

### Bottom Navigation Yapisi
- 4 tab: Panel (Dashboard), Cihaz, Guvenlik, Ayar
- Guvenlik tab'i altinda: DNS Filtreleme, Firewall, VPN, DDoS Koruma
- Ayarlar tab'i altinda: AI Chat, Telegram, WiFi AP, DHCP, Guvenlik Ayarlari
- Trafik izleme: Dashboard icinde erisiliyor (bandwidth grafikten gecis + canli trafik karti)
- Profil yonetimi: Guvenlik > DNS icinde (web ile ayni mantik)
- Alt ekranlar icinde tab veya liste ile gecis yapilir

### Proje Konumu ve Yapisi
- Proje yeri: Bu repo icinde `android/` klasoru (TonbilAiFirevallv5/android/)
- Package adi: com.tonbil.aifirewall
- Package organizasyonu: Feature-based (com.tonbil.aifirewall.feature.dashboard, .feature.devices, .feature.security...)
- Min API: 31 (Android 12) — S24 Ultra hedefli, Material You destegi
- Target API: En guncel (Android 14+)

### Ilk Acilis Deneyimi
- Splash screen: Neon animasyonlu (Android 12+ SplashScreen API) — cyberpunk TonbilAiOS logosu + neon glow, 1-2 saniye
- Onboarding: 2 sayfa — 1) Hosgeldin + ozellik tanitimi, 2) Sunucu baglanti ayarlari
- Sunucu kesfetme: mDNS/LAN tarama + QR kod + manuel URL girisi
- Urun odakli tasarim: Baska bir kisi cihazi aldiginda kendi basina kurulum yapabilmeli
- Onboarding sadece ilk kurulumda gosterilir, sonraki acilislarda token varsa direkt Dashboard

### Mobil Tema Yaklasimi
- Glassmorphism: Sadelestirilmis cam efekti — yari saydam kartlar + hafif gradient border, minimal blur (performans onceligi)
- UI sistemi: Material 3 + ozel cyberpunk tema (neon cyan/magenta/green/amber/red renk paleti)
- Neon glow: Sadece onemli ogelerde — aktif tab ikonu, baglanti durumu gostergesi, kritik uyarilar, butonlar
- Arka plan: Koyu mor-siyah gradient (web ile tutarli)
- Uygulama ikonu: Neon cyan kalkan/firewall ikonu, koyu arka plan

### Claude's Discretion
- Exact Gradle/AGP version pinning
- Compose BOM version selection
- Koin module structure
- Ktor client engine choice (OkHttp vs CIO)
- Navigation graph implementation details
- Splash animation specifics (duration, easing)
- Feature module internal package structure

</decisions>

<specifics>
## Specific Ideas

- "Bunu bir urun olarak tasarliyoruz — baska bir kisi cihazi aldiginda ayarlari yapabilmeli"
- Sunucu kesfinde QR kod destegi — Pi web panelinde veya ekraninda gosterilen QR ile hizli baglanti
- Web arayuzundeki cyberpunk glassmorphism temasindan ilham alinacak ama mobilde sadelestirilmis versiyonu
- Bottom nav ikonu secimi: Panel (home), Cihaz (smartphone/devices), Guvenlik (shield), Ayar (settings gear)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- Backend REST API: Tum endpoint'ler mevcut — yeni endpoint gerekmez (Phase 6 icin)
- Web tema renkleri (CLAUDE.md): --neon-cyan: #00F0FF, --neon-magenta: #FF00E5, --neon-green: #39FF14, --neon-amber: #FFB800, --neon-red: #FF003C
- Web glassmorphism degerleri: glass-bg rgba(255,255,255,0.05), glass-border rgba(255,255,255,0.12)

### Established Patterns
- Backend API base: /api/v1/ prefix, JWT Bearer token auth
- WebSocket: /api/v1/ws endpoint (canli veri)
- Erisim: Yerel 192.168.1.2 veya uzak wall.tonbilx.com

### Integration Points
- API client test icin: GET /api/v1/dashboard/summary (auth gerektirmez veya basit health check)
- Auth icin: POST /api/v1/auth/login (email + password → JWT token)
- WebSocket: wss://wall.tonbilx.com/api/v1/ws veya ws://192.168.1.2/api/v1/ws

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-project-skeleton*
*Context gathered: 2026-03-06*
