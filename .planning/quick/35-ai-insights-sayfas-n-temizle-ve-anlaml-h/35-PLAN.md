---
quick_task: 35
title: "AI Insights sayfasını temizle ve anlamlı hale getir"
date: 2026-03-12
---

# Plan: AI Insights Sayfasını Temizle ve Anlamlı Hale Getir

## Mevcut Durum Analizi

InsightsPage.tsx şu anda:
- 4 basit istatistik kartı (Engelli IP, Otomatik Engel, Şüpheli Sorgu, Dış Sorgu)
- Engellenen IP listesi (düz liste)
- Insight akışı (düz kart listesi, severity badge + aksiyon butonları)

**Sorunlar:**
1. Backend'de `/hourly-trends` endpoint mevcut ama frontend kullanMIYOR
2. Backend'de `/domain-reputation/{domain}` endpoint mevcut ama frontend kullanMIYOR
3. Severity filtreleme YOK — tüm insight'lar karışık listeleniyor
4. Kategori filtreleme YOK (anomaly/security/optimization)
5. Arama/filtre yok
6. Grafik/görselleştirme yok — tamamen metin bazlı
7. Zaman bilgisi göreceli değil (sadece tam tarih)

## Yapılacaklar

### Task 1: InsightsPage.tsx tam yeniden yazım

**Dosyalar:** `frontend/src/pages/InsightsPage.tsx`

**Değişiklikler:**

1. **Üst kısım — Özet istatistik kartları (mevcut, iyileştirilecek)**
   - 4 kartı daha kompakt hale getir, son tehdit zamanını ekle

2. **Saatlik trend grafik (YENİ)**
   - `/insights/hourly-trends?hours=24` endpoint'ini çağır
   - Recharts AreaChart ile son 24 saatlik DNS tehdit trendi göster
   - Alan: total_queries, blocked_queries, suspicious_queries

3. **Severity filtre tabları (YENİ)**
   - Tümü / Kritik / Uyarı / Bilgi tab'ları
   - Her tab'da sayı badge'i
   - Aktif tab neon vurgu

4. **Domain reputation sorgulama (YENİ)**
   - Arama kutusu ile domain sorgulatma
   - `/insights/domain-reputation/{domain}` endpoint'ini çağır
   - Sonuç: skor (0-100 renk bar), risk seviyesi, faktörler listesi

5. **Insight listesi iyileştirmesi**
   - Göreceli zaman gösterimi ("5 dk önce", "2 saat önce")
   - Kategori filtresi (anomaly/security/optimization chip'ler)
   - Daha iyi kart düzeni

6. **Engellenen IP bölümü (mevcut, iyileştirilecek)**
   - Açılır/kapanır panel (varsayılan kapalı, sayı göster)

**Verify:** Frontend build başarılı, tüm endpoint'ler çağrılıyor, chart render ediliyor
**Done:** Sayfa zengin veri gösteriyor, filtreler çalışıyor, grafik mevcut
