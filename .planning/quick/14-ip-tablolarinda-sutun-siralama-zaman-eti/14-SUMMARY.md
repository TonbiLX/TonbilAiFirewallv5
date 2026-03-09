# Quick 14: IP Tablolarinda Sutun Siralama

## Ozet

3 tabloya (Kontrol Edilen IP, Guvenilir IP, Engellenen IP) sutun basligi siralama ozelligi eklendi. Toplam 13 siralanabilir sutun.

## Yapilan Degisiklikler

### Task 1: IpReputationTab.tsx (Commit: d16f05a)
- 6 siralanabilir sutun: IP Adresi, Skor, Ulke, Sehir, ISP, Kontrol Tarihi
- Varsayilan: checked_at DESC (yeniden eskiye)
- ArrowUp/ArrowDown aktif sutun, ArrowUpDown pasif sutunlar
- Numeric sort (abuse_score) + string localeCompare (diger sutunlar)

### Task 2: IpManagementPage.tsx (Commit: 2925c87)
- Guvenilir IP: 3 siralanabilir sutun (IP/Aciklama/Tarih), Islem haric
- Engellenen IP: 4 siralanabilir sutun (IP/Sebep/Tarih/Kaynak), Kalan Sure + Islem haric
- Varsayilan: created_at/blocked_at DESC
- is_manual icin boolean sort, diger sutunlar localeCompare

### Task 3: Deploy
- SFTP upload + Pi frontend build (11.92s) basarili
- Backend restart gerekmedi (sadece frontend degisikligi)

## Teknik Detaylar

- Siralama tamamen frontend'de, API cagrisi yok
- sortBy + sortOrder state'leri ile toggle mantigi
- Ayni sutuna tiklaninca asc<->desc, farkli sutuna gecilince asc'den baslar
- TypeScript dogrulama: 0 hata
