---
phase: quick-18
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/IpManagementPage.tsx
autonomous: true
requirements: [QUICK-18]
must_haves:
  truths:
    - "Engellenen IP tablosunda IP adresi ile arama yapilabilir"
    - "Tablo sayfalama ile bolunmus: 50/100/150/200 IP secenegi var"
    - "Sayfa basina IP sayisi dropdown ile seciliyor"
    - "Dropdown arka plani siyah, yazilar neon — tema ile uyumlu"
    - "Beyaz arka plan + beyaz yazi sorunu duzeltilmis"
  artifacts:
    - path: "frontend/src/pages/IpManagementPage.tsx"
      provides: "IP arama + sayfalama + dropdown tema duzeltmesi"
  key_links:
    - from: "IpManagementPage.tsx search input"
      to: "blockedIps array filter"
      via: "client-side filter by ip_address"
      pattern: "filter.*ip_address.*includes.*searchTerm"
---

<objective>
IP Yonetimi sayfasinin Engellenen IP sekmesine IP arama ve sayfalama ozellikleri ekle. Tum select/dropdown elemanlarin arka planini siyah, yazilarini neon renkli yap (cyberpunk temaya uyumlu).

Purpose: Cok sayida engellenen IP oldugunda (AbuseIPDB blacklist 10K IP) kullanilabilirlik icin arama ve sayfalama sart. Ayrica beyaz arka plan + beyaz yazi dropdown sorunu duzeltilecek.
Output: Guncelenmis IpManagementPage.tsx
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/IpManagementPage.tsx
@frontend/src/services/ipManagementApi.ts
@CLAUDE.md

Tema renkleri:
- --neon-cyan: #00F0FF (ana vurgu)
- --neon-magenta: #FF00E5
- --neon-green: #39FF14
- --neon-amber: #FFB800
- --neon-red: #FF003C
- --glass-bg: rgba(255,255,255,0.05)
- Arka plan: koyu mor-siyah

Mevcut select class:
```typescript
const selectClass = "w-full bg-surface-800 border border-glass-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-cyan/50 transition-colors appearance-none cursor-pointer";
```

Sorun: Native HTML `<select>` ve `<option>` elementlerinde `bg-surface-800` uygulanmiyor, tarayici varsayilan beyaz arka plan gosteriyor. `<option>` elementlerine de acikca siyah arka plan ve beyaz/neon yazi rengi verilmeli.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Engellenen IP sekmesine arama, sayfalama ve dropdown tema duzeltmesi</name>
  <files>frontend/src/pages/IpManagementPage.tsx</files>
  <action>
IpManagementPage.tsx dosyasinda asagidaki degisiklikleri yap:

**1. Yeni state'ler ekle (mevcut state'lerin altina):**
- `blockedSearchTerm: string` — IP arama metni (useState, bos string)
- `blockedPageSize: number` — Sayfa basina IP sayisi (useState, varsayilan 50)
- `blockedCurrentPage: number` — Mevcut sayfa numarasi (useState, varsayilan 1)
- `Search` ikonunu lucide-react import'una ekle

**2. Engellenen IP arama + sayfa basina secim UI:**
Engellenen IP sekmesinde "Engellenen IP Listesi" basligiyla "IP Engelle" butonu arasina (div.flex.items-center.justify-between icine) bir arama input'u ve sayfa basina secim dropdown'u ekle:

Arama input'u:
- Sol tarafta Search ikonu olan bir text input
- placeholder: "IP ara..."
- Degistiginde `blockedSearchTerm` guncelle ve `blockedCurrentPage`'i 1'e sifirla
- Stil: `bg-black border border-glass-border rounded-lg px-3 py-2 pl-9 text-sm text-[#00F0FF] placeholder-gray-500 focus:outline-none focus:border-[#00F0FF]/50 w-64`

Sayfa basina secim:
- Label: "Sayfa:"
- `<select>` ile secenekler: 50, 100, 150, 200
- Degistiginde `blockedPageSize` guncelle ve `blockedCurrentPage`'i 1'e sifirla
- Her `<option>` elementine: `className="bg-black text-[#00F0FF]"` ver
- Select stili: `bg-black border border-glass-border rounded-lg px-2 py-2 text-sm text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]/50 appearance-none cursor-pointer w-20`

Layout: Baslik solda, arama + sayfa basina + ekle butonu sag tarafa flex gap-3 ile dizilsin.

**3. Filtreleme ve sayfalama mantigi:**
Siralama isleminden sonra (sortedBlockedIps hesaplandiktan sonra), asagidaki islemleri uygula:

```typescript
// Arama filtresi
const filteredBlockedIps = sortedBlockedIps.filter(ip =>
  !blockedSearchTerm || ip.ip_address.includes(blockedSearchTerm)
);

// Sayfalama
const totalFiltered = filteredBlockedIps.length;
const totalPages = Math.ceil(totalFiltered / blockedPageSize);
const startIndex = (blockedCurrentPage - 1) * blockedPageSize;
const pagedBlockedIps = filteredBlockedIps.slice(startIndex, startIndex + blockedPageSize);
```

Tablo `return sortedBlockedIps.map(...)` yerine `pagedBlockedIps.map(...)` kullansin.

"Tumunu sec" checkbox mantigi: sadece mevcut sayfadaki IP'leri secsin (pagedBlockedIps).

**4. Sayfalama kontrolleri (tablo altina):**
Tablo GlassCard'in icinde, `</table>` kapanis tag'inden sonra, sayfalama kontrolleri ekle:

```
| < Onceki | Sayfa X / Y (toplam Z IP) | Sonraki > |
```

- "Onceki" butonu: `blockedCurrentPage > 1` ise aktif, tiklaninca sayfa -1
- "Sonraki" butonu: `blockedCurrentPage < totalPages` ise aktif, tiklaninca sayfa +1
- Ortada: "Sayfa {current} / {total} (toplam {filteredCount} IP)" yazisi
- Arama aktifse: "(filtrelenmis: {filteredCount} / {totalCount})" goster
- Stil: flex justify-between items-center, butonlar text-[#00F0FF], disabled ise opacity-30
- totalPages <= 1 ise sayfalama kontrollerini gizle

**5. Tum dropdown/select `<option>` elementlerini duzelt:**
Sayfadaki TUM `<option>` elementlerine `style={{ backgroundColor: '#000', color: '#00F0FF' }}` veya `className="bg-black text-[#00F0FF]"` ekle. Bu su alanlari kapsar:
- Engelleme suresi select (form icindeki)
- Sure degistirme inline select (tablo icindeki editingDurationIp)
- Toplu islem sure select
- Yeni eklenen sayfa basina select

Ayrica tum `<select>` elementlerinin kendisine de `style={{ backgroundColor: '#000' }}` ekle — bazi tarayicilarda `bg-surface-800` Tailwind class'i yetersiz kalir.

**6. Guvenilir IP sekmesine de ayni arama ekle (opsiyonel ama yapilmali):**
Guvenilir IP listesi kucuk olabilir ama tutarlilik icin ayni arama pattern'i ekle:
- `trustedSearchTerm: string` state
- Guvenilir IP Listesi basliginin yanina kucuk bir arama input'u
- Filtreleme: ip_address veya description icerigine gore
- Sayfalama GEREKMEZ (guvenilir IP listesi genelde kucuk)
</action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5\frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
- Engellenen IP sekmesinde IP adresi ile arama yapilabilir
- Sayfa basina 50/100/150/200 IP secenegi calisiyor
- Sayfalama kontrolleri (onceki/sonraki) dogru calisiyor
- Arama yapildiginda sayfalama sifirlaniyor
- Tum select/option elementleri siyah arka plan + neon cyan yazi
- Guvenilir IP sekmesinde de arama var
- TypeScript hatasiz derleniyor
</done>
</task>

</tasks>

<verification>
1. `npx tsc --noEmit` — TypeScript hatasiz
2. `npm run build` — Vite build basarili
3. Gorsel kontrol: Dropdown'lar siyah arka plan + neon yazi
4. Gorsel kontrol: Arama input'u calisiyor, sayfalama dogru geciyor
</verification>

<success_criteria>
- Engellenen IP tablosunda arama input'u var ve IP adresine gore filtreliyor
- Sayfa basina IP sayisi 50/100/150/200 arasinda secilebilinir
- Sayfalama kontrolleri onceki/sonraki butonlari ile calisiyor
- Tum dropdown arka planlari siyah, yazilari neon cyan
- Beyaz arka plan + beyaz yazi sorunu tamamen giderilmis
- TypeScript ve build hatasiz
</success_criteria>

<output>
After completion, create `.planning/quick/18-ip-yonetimi-engellenen-ip-sayfasina-aram/18-SUMMARY.md`
</output>
