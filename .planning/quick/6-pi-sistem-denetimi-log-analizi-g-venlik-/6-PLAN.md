---
type: quick-plan
task: "Pi sistem denetimi: log analizi, güvenlik testi, firewall performansı, saldırı tepki ölçümü"
date: 2026-03-08
---

# Quick Task 6: Pi Sistem Denetimi

## Görev
6 paralel Sonnet 4.6 ajan ile Pi router'ın kapsamlı güvenlik ve performans denetimi.

## Ajanlar
1. Sistem Log Analizi — backend, Redis, MariaDB, kernel logları
2. Güvenlik Zafiyet Taraması — açık portlar, SSH, SSL, dosya izinleri
3. Firewall Performans Testi — nftables kuralları, conntrack, RPS/IRQ
4. DDoS/Saldırı Tepki Ölçümü — rate limiting, meter setleri, simülasyon
5. API Endpoint Güvenlik Testi — auth bypass, SQLi, XSS, CORS
6. Servis Sağlık & Kaynak İzleme — CPU, RAM, disk, sıcaklık, DB

## Çıktı
Kapsamlı denetim raporu + iyileştirme önerileri (6-SUMMARY.md)
