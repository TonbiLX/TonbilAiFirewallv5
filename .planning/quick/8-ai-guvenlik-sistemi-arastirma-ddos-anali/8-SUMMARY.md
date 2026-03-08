---
phase: quick
plan: 8
subsystem: ai-security-research
tags: [ai, ddos, ml, edge-ai, api-integration, threat-intelligence, research]
dependency_graph:
  requires: []
  provides: [ai-security-roadmap, api-cost-analysis, edge-ml-feasibility]
  affects: [threat_analyzer, ddos_service, dns_proxy, llm_service, telegram_service]
decisions:
  - Edge ML (scikit-learn + River) Pi 5'te mumkun — %5 CPU, +75MB RAM
  - Claude Haiku 4.5 guvenlik analizi icin en uygun maliyet/performans (~$14/ay)
  - AbuseIPDB + AlienVault OTX ucretsiz tier yeterli
  - Welford Z-score baseline sifir bagimlilik ile baslangic icin ideal
  - DeepSeek guvenlik riski — uretim icin onerilmez
metrics:
  duration: "5 min (5 paralel ajan)"
  completed: "2026-03-08"
  tasks_completed: 1
  tasks_total: 1
---

# Quick Plan 8: AI Guvenlik Sistemi Arastirma Ozeti

5 paralel Sonnet 4.6 ajani ile kapsamli AI guvenlik arastirmasi tamamlandi.

## Mevcut Sistem Analizi

### Var Olan AI Yetenekleri
| Bilesen | Dosya | Teknik | Durum |
|---------|-------|--------|-------|
| NLP Komut Motoru | ai_engine.py | TF-IDF + Fuzzy Matching | Iyi, Turkce NLP |
| LLM Chat | llm_service.py + llm_providers.py | 8 saglayici destegi | Iyi |
| Tehdit Analizi | threat_analyzer.py | Entropi + Rate Limit + Skor | Iyi, gelistirilebilir |
| DGA Tespiti | threat_analyzer.py | Shannon entropi >= 3.5 | Temel, iyilestirilebilir |
| Domain Reputation | domain_reputation.py | Statik skorlama (entropi + TLD + uzunluk) | Orta |
| DNS Fingerprint | dns_fingerprint.py | 14 kural ile OS/cihaz tespiti | Temel |
| Log Analizi | llm_log_analyzer.py | LLM'e ham log gonderme | Zayif |
| Telegram Bot | telegram_service.py + telegram_worker.py | 2 yonlu sohbet + bildirim | Iyi |

### Kritik Eksiklikler
- GeoIP entegrasyonu YOK (DDoS haritasi sahte veri gosteriyor)
- AbuseIPDB / VirusTotal YOK (bilinen kotu niyetli IP'ler tespit edilemiyor)
- ASN analizi YOK (datacenter/Tor/VPN ayirimi yapılamiyor)
- DNS tunneling tespiti YOK
- C2 beacon pattern tespiti YOK
- Data exfiltration tespiti YOK
- Port scan / lateral movement tespiti YOK
- Trafik baseline (normal vs anormal) YOK
- Gunluk ozet Telegram'a gonderilmiyor (fonksiyon var ama cagrilmiyor)
- Flow tracker + threat analyzer birlesik degil

## Onerilen AI Gelistirme Yol Haritasi

### Faz 1 — Sifir Bagimlilik, Yuksek Deger (1-2 gun)

| Oneri | Teknik | Pi Yuku | Kaynak |
|-------|--------|---------|--------|
| Welford Z-score Baseline | Saf Python, online learning | CPU <0.1% | traffic_baseline.py |
| IP Reputation Engine | Redis HASH, puan sistemi | CPU <0.1% | ip_reputation.py |
| Feature Extractor | flow_tracker verisinden ozellik cikarma | CPU <1% | anomaly_collector.py |
| DNS Tunneling Tespiti | Label uzunluk + Base64 pattern | CPU <0.1% | dns_proxy.py |
| Beacon Pattern Tespiti | Redis ZSET timestamp analizi | CPU <0.1% | advanced_dns_analyzer.py |
| Gunluk Telegram Ozeti | Mevcut fonksiyonu cagiran worker | CPU ~0 | summary_worker.py |

### Faz 2 — scikit-learn Edge ML (1-2 hafta)

| Oneri | Teknik | Pi Yuku | Kaynak |
|-------|--------|---------|--------|
| Isolation Forest | scikit-learn, 100 agac, Pi'de ~1.2s egitim | +50MB RAM, <1ms inference | anomaly_ml.py |
| DGA LSTM (TFLite) | Karakter-bazli LSTM, ~200KB model | +20MB RAM, <1ms/domain | dga_detector.tflite |
| River Online Learning | HalfSpaceTrees, incremental | +20MB RAM, <0.1ms/sorgu | ml_worker.py |
| ADWIN Concept Drift | Trafik pattern degisim tespiti | ~0 | TrafficPatternMonitor |

### Faz 3 — Dis API Entegrasyonu (Opsiyonel)

| API | Ucretsiz Kota | Aylik Maliyet | Kullanim |
|-----|-------------|---------------|----------|
| AbuseIPDB | 1.000 sorgu/gun | $0 | Saldirgan IP dogrulama |
| AlienVault OTX | Sinirsiz | $0 | Threat intelligence feed |
| IPinfo | 50.000/ay | $0 | GeoIP + ASN |
| VirusTotal | 500/gun | $0 | Supheli domain analizi |
| GreyNoise Community | ~50/gun | $0 | Gurultu vs hedefli ayirimi |
| MaxMind GeoLite2 | Sinirsiz (offline) | $0 | Offline geolocation |
| Claude Haiku 4.5 | Ucretli | ~$14/ay | Guvenlik analizi + rapor |
| Gemini 2.0 Flash | 1.000 req/gun | $0 | Alternatif LLM |

### Faz 4 — LLM Entegrasyon Gelistirme

| Oneri | Detay |
|-------|-------|
| Tool Use (Function Calling) | Claude block_ip, block_domain, send_telegram_alert araclari |
| Streaming Response | httpx SSE veya anthropic SDK ile canli analiz |
| Zenginlestirilmis LLM Prompt | Ham log yerine istatistiksel ozet gonderin |
| Batch API | Saatlik guvenlik analizi %50 indirimli |
| Gunluk Guvenlik Raporu | Claude ile otomatik rapor → Telegram |

## Pi 5 Edge ML Fizibilite

| Metrik | Deger |
|--------|-------|
| Mevcut RAM kullanimi | ~600 MB / 4 GB |
| ML icin kullanilabilir | ~800 MB - 1 GB |
| scikit-learn Isolation Forest | +50 MB RAM, ~1.2s egitim, <1ms inference |
| River online learning | +20 MB RAM, <0.1ms/sorgu |
| TFLite DGA dedektoru | +20 MB RAM, <1ms/domain |
| Toplam ek yuk | +75 MB RAM, <%5 CPU |
| Sonuc | UYGULANABILIR |

## Maliyet Analizi (Aylik)

| Senaryo | Maliyet |
|---------|---------|
| Sadece sohbet (Claude Haiku, 50/gun) | ~$5/ay |
| + Saatlik guvenlik analizi (Batch API) | +$9/ay |
| + Ucretsiz API'ler (AbuseIPDB, OTX, IPinfo) | $0 |
| TOPLAM onerilen hibrit | ~$14/ay |

## Mimari Karar: 3 Katmanli Hibrit Model

```
Katman 1 — EDGE (Ucretsiz, Anlik, <1ms)
├── Z-score anomali tespiti
├── IP reputation scoring (yerel)
├── DGA entropi + bigram + LSTM
├── DNS tunneling label kontrolu
├── OTX feed cache kontrolu
└── Beacon pattern Redis ZSET

Katman 2 — EVENT-DRIVEN (Ucuz, dakikalar icinde)
├── DDoS tetik → AbuseIPDB sorgusu
├── Yuksek risk IP → Claude Haiku analizi
├── Supheli domain → VirusTotal sorgusu
└── Kritik olay → Telegram bildirim + kullanici onayi

Katman 3 — BATCH (Orta maliyet, saatlik)
├── DNS + flow ozeti → Claude Haiku Batch API
├── Gunluk guvenlik raporu → Telegram
├── Cihaz cluster analizi (Jaccard)
└── Isolation Forest yeniden egitim
```

## Guvenlik Uyarisi

DeepSeek (llm_providers.py'de destekleniyor) 2026'da ciddi guvenlik ihlalleri yasadi:
- 1M+ hassas kayit (chat gecmisleri, API keyleri) aciga cikti
- %100 jailbreak basari orani raporlandi
- 7+ ulkede yasaklandi
- Router loglari gibi hassas veri gondermek risklidir
- URETIM KULLANIMI ONERILMEZ

## Sonraki Adimlar

Kullanicinin secebilecegi uygulanabilir isler:
1. `/gsd:quick` ile Faz 1 uygulamasi (Z-score + IP reputation + tunneling)
2. `/gsd:quick` ile AbuseIPDB + GeoIP entegrasyonu
3. `/gsd:quick` ile LLM prompt iyilestirmesi + gunluk Telegram ozeti
4. Phase olarak planlanabilir (daha buyuk kapsam)
