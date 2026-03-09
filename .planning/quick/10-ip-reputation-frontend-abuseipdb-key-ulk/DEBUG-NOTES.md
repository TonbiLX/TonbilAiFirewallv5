# IP Reputation Tab — Debug Notları

## Sorun
Güvenlik Duvarı → "IP İtibar" tab'ına tıklanınca siyah/boş ekran.

## Yapılan Kontroller
- TSC: hata yok
- Frontend build: başarılı (exit=0)
- FirewallPage.tsx: import + render doğru
- IpReputationTab.tsx: Pi'de mevcut (24KB)
- Backend API: /ip-reputation/config, /summary, /ips çalışıyor (401 = auth gerekli, normal)
- Build çıktısı: minified JS'de component var (isim mangling yüzünden grep bulamıyor)

## Muhtemel Sorun
Runtime crash — React component mount olurken JS hatası veriyor.
Olası nedenler:
1. API yanıt formatı uyumsuzluğu (kısmen düzeltildi — ips.data.ips, masked key)
2. Emoji karakter encoding sorunu (flag emojiler: 🇨🇳🇷🇺 vb.)
3. Bir state değişkenine undefined erişim

## Yapılacak
1. Tarayıcıda F12 → Console'daki hata mesajını oku
2. Veya component'i minimal hale getirip test et:
   - Önce sadece `return <div>IP Itibar Tab Test</div>` ile test et
   - Çalışırsa kademeli olarak bölümleri ekle
3. Düzeltilecek dosya: `frontend/src/components/firewall/IpReputationTab.tsx`

## Son Commit
- f91a3fa: API response mapping fix (ipsRes.data.ips, masked key kaldırma)
