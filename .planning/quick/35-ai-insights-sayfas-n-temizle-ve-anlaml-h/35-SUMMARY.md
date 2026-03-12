---
quick_task: 35
title: "AI Insights sayfasını temizle ve anlamlı hale getir"
date: 2026-03-12
status: completed
commit: 657580c
files_modified:
  - frontend/src/pages/InsightsPage.tsx
tech_added:
  - recharts AreaChart (saatlik trend görselleştirme)
  - /insights/hourly-trends?hours=24 endpoint entegrasyonu
  - /insights/domain-reputation/{domain} endpoint entegrasyonu
decisions:
  - Recharts AreaChart + gradyan fill ile 3 seri (toplam/engellenen/süpheli) tek grafikte gösterildi
  - Severity filtre tabları inline button olarak uygulandı (ayrı bileşen gerekmedi)
  - Domain reputation skoru 0-20 yeşil / 21-60 amber / 61-100 kırmızı renk skalası
  - Engellenen IP bölümü varsayılan kapalı, sayı badge header'da görünür
  - relativeTime() fonksiyonu inline tanımlandı (yeni dosya oluşturmadan)
---

# Quick Task 35: AI Insights Sayfası Tam Yeniden Yazım

**Tek cümle özet:** InsightsPage.tsx, daha önce kullanılmayan iki backend endpoint'ini entegre ederek saatlik DNS trend grafiği, domain reputation sorgulama paneli, severity filtre tabları ve göreceli zaman gösterimi eklenmiş zengin bir tehdit analiz sayfasına dönüştürüldü.

## Tamamlanan Değişiklikler

### 1. Özet İstatistik Kartları (İyileştirildi)
- 4 kart kompakt 2-satır grid yapısına taşındı (py-3 px-4)
- `last_threat_time` alanı göreceli zaman ile eklendi ("Son: 5 dk önce")

### 2. Saatlik Trend Grafik (YENİ)
- `/insights/hourly-trends?hours=24` endpoint'i çağrılıyor
- Recharts `AreaChart` + gradyan fill (3 alan: Toplam, Engellenen, Şüpheli)
- Neon renkleri: cyan (#00F0FF) / red (#FF003C) / amber (#FFB800)
- 60 saniyede bir otomatik yenileme
- Grafik açıklaması (legend) alt kısımda

### 3. Domain Reputation Sorgulama (YENİ)
- Input field + Enter key desteği + "Sorgula" butonu
- `/insights/domain-reputation/{domain}` endpoint'i çağrılıyor
- Sonuç: skor progress bar (renk kodlu, neon glow), risk seviyesi NeonBadge, faktörler listesi
- Hata durumunda kullanıcıya mesaj gösteriliyor

### 4. Severity Filtre Tabları (YENİ)
- "Tümü / Kritik / Uyarı / Bilgi" tab satırı
- Her tabda sayım badge'i
- Aktif tab ilgili neon rengiyle vurgulanıyor
- `filteredInsights` hesaplaması ile liste anlık filtreleniyor

### 5. Insight Listesi İyileştirmeleri
- `relativeTime()` fonksiyonu: "az önce", "5 dk önce", "2 saat önce", "dün", "N gün önce"
- Zaman üzerine hover ile tam tarih (title attribute)
- Kategori chip tasarımı iyileştirildi (border + bg)
- Tüm mevcut işlevler korundu (block IP, unblock IP, dismiss)

### 6. Engellenen IP Bölümü (İyileştirildi)
- Varsayılan kapalı, header'da `[N]` kırmızı badge ile sayı görünür
- ChevronDown/Up ikonu ile açılır/kapanır toggle
- Mevcut unblock işlevi korundu

## Teknik Notlar

- Yeni tip tanımları: `HourlyTrend`, `HourlyTrendsResponse`, `DomainReputationResponse` (inline)
- Yeni yardımcı fonksiyonlar: `relativeTime()`, `formatHourLabel()`, `getReputationColor/Label/Variant()`
- Grafik: CartesianGrid + XAxis + YAxis + Tooltip + 3x Area (gradientId benzersiz)
- İki bağımsız polling interval: loadData=10s, loadTrends=60s
- `AreaChart` margin `left: -20` ile YAxis label taşması önlendi

## Doğrulama

- Frontend build: `tsc && vite build` — 2680 modül, 11.96s, hata yok
- Commit: 657580c

## Sapmalar

Yok — plan tam olarak uygulandı.
