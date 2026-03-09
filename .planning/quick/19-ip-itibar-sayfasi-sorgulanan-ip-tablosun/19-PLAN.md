---
phase: quick-19
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/firewall/IpReputationTab.tsx
autonomous: true
requirements: [QUICK-19]

must_haves:
  truths:
    - "Kontrol Edilen IP'ler tablosunda IP adresi ile arama yapilabilir"
    - "Sayfa basina 50/100/150/200 secimi dropdown ile yapilabilir"
    - "Sayfalama kontrolleri (Onceki/Sonraki) ile sayfalar arasi gecis yapilabilir"
    - "Dropdown'lar siyah arka plan + neon cyan yazi ile gorunur (tema tutarliligi)"
  artifacts:
    - path: "frontend/src/components/firewall/IpReputationTab.tsx"
      provides: "IP itibar sorgulanan IP tablosu arama + sayfalama"
      contains: "ipSearchTerm"
  key_links:
    - from: "IpReputationTab search input"
      to: "sortedIps filtreleme"
      via: "ipSearchTerm state"
      pattern: "ipSearchTerm"
---

<objective>
IpReputationTab bilesenindeki "Kontrol Edilen IP'ler" tablosuna arama, sayfa basina secim ve sayfalama kontrolleri eklemek. IpManagementPage'deki birebir ayni deseni kullanmak.

Purpose: Sorgulanan IP tablosu yuzlerce kayit icerdiginde kullanilabilirlik sorunlari yasiyor — uzayip giden tablo gorunumunu iyilestirmek.
Output: Arama + sayfalama + dropdown temasi eklenmis IpReputationTab.tsx
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/firewall/IpReputationTab.tsx
@frontend/src/pages/IpManagementPage.tsx (referans: arama + sayfalama + dropdown deseni)
</context>

<tasks>

<task type="auto">
  <name>Task 1: IpReputationTab — arama + sayfalama + dropdown tema</name>
  <files>frontend/src/components/firewall/IpReputationTab.tsx</files>
  <action>
IpManagementPage'deki arama + sayfalama + dropdown desenini birebir IpReputationTab'in "Kontrol Edilen IP'ler" tablosuna (Bolum 5, ~satir 778-953) uygulamak.

Eklenecek state (mevcut state blogunun altina, ~satir 176 civari):
```typescript
// Sorgulanan IP arama + sayfalama
const [ipSearchTerm, setIpSearchTerm] = useState("");
const [ipPageSize, setIpPageSize] = useState(50);
const [ipCurrentPage, setIpCurrentPage] = useState(1);
```

filterFlagged veya sortBy degistiginde sayfayi 1'e resetle. Mevcut `filterFlagged` toggle butonunun onClick'ine `setIpCurrentPage(1)` ekle.

"Kontrol Edilen IP'ler" baslik satiri (flex row, satir ~780-823) icine uc yeni kontrol ekle. Mevcut "Sadece Isaretliler", "Yenile", "Onbellegi Temizle" butonlarinin SOLUNA:

1. **Arama inputu** — IpManagementPage ile ayni stil:
```tsx
<div className="relative">
  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
  <input
    type="text"
    value={ipSearchTerm}
    onChange={(e) => { setIpSearchTerm(e.target.value); setIpCurrentPage(1); }}
    placeholder="IP ara..."
    className="bg-black border border-glass-border rounded-lg px-3 py-2 pl-9 text-sm text-[#00F0FF] placeholder-gray-500 focus:outline-none focus:border-[#00F0FF]/50 w-64"
  />
</div>
```

2. **Sayfa basina dropdown** — Siyah arka plan + neon cyan yazi:
```tsx
<div className="flex items-center gap-2">
  <span className="text-xs text-gray-400">Sayfa:</span>
  <select
    value={ipPageSize}
    onChange={(e) => { setIpPageSize(Number(e.target.value)); setIpCurrentPage(1); }}
    style={{ backgroundColor: '#000' }}
    className="border border-glass-border rounded-lg px-2 py-2 text-sm text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]/50 appearance-none cursor-pointer w-20"
  >
    <option value={50} className="bg-black text-[#00F0FF]">50</option>
    <option value={100} className="bg-black text-[#00F0FF]">100</option>
    <option value={150} className="bg-black text-[#00F0FF]">150</option>
    <option value={200} className="bg-black text-[#00F0FF]">200</option>
  </select>
</div>
```

Mevcut `filteredIps` hesaplamasini (~satir 366-377) guncelle. Arama filtresi ekle:
```typescript
const filteredIps = ips.filter(ip =>
  (!filterFlagged || ip.abuse_score >= 50) &&
  (!ipSearchTerm || ip.ip.includes(ipSearchTerm))
);
```

Mevcut `sortedIps` hesaplamasindan sonra sayfalama ekle:
```typescript
const totalFilteredIps = sortedIps.length;
const totalIpPages = Math.ceil(totalFilteredIps / ipPageSize);
const ipStartIndex = (ipCurrentPage - 1) * ipPageSize;
const pagedIps = sortedIps.slice(ipStartIndex, ipStartIndex + ipPageSize);
```

Tablo tbody'sinde `sortedIps.map` yerine `pagedIps.map` kullan.

Kayit sayisi metnini (~satir 787 `{ips.length} kayit`) guncelle:
```tsx
<p className="text-xs text-gray-400">
  {ipSearchTerm ? `${totalFilteredIps} / ${ips.length}` : ips.length} kayit
</p>
```

Bos tablo mesajini arama durumuna gore guncelle:
```tsx
{ipSearchTerm ? `"${ipSearchTerm}" ile eslesen IP bulunamadi` : "Henuz kontrol edilen IP yok"}
```

Tablonun hemen altina (GlassCard kapanmadan once) sayfalama kontrolleri ekle. IpManagementPage ile ayni stil:
```tsx
{totalIpPages > 1 && (
  <div className="flex items-center justify-between px-1 py-2 mt-4 text-sm">
    <button
      onClick={() => setIpCurrentPage(p => Math.max(1, p - 1))}
      disabled={ipCurrentPage <= 1}
      className="px-3 py-1.5 text-[#00F0FF] border border-[#00F0FF]/30 rounded-lg hover:bg-[#00F0FF]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-xs"
    >
      &lt; Onceki
    </button>
    <span className="text-xs text-gray-400">
      Sayfa {ipCurrentPage} / {totalIpPages}
      {ipSearchTerm
        ? ` (filtrelenmis: ${totalFilteredIps} / ${ips.length} IP)`
        : ` (toplam ${totalFilteredIps} IP)`}
    </span>
    <button
      onClick={() => setIpCurrentPage(p => Math.min(totalIpPages, p + 1))}
      disabled={ipCurrentPage >= totalIpPages}
      className="px-3 py-1.5 text-[#00F0FF] border border-[#00F0FF]/30 rounded-lg hover:bg-[#00F0FF]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-xs"
    >
      Sonraki &gt;
    </button>
  </div>
)}
```

ONEMLI: `ChevronDown` lucide import'u zaten KULLANILMIYOR — import listesinde olmadigini dogrula, yoksa ekleme. `Search` zaten import ediliyor (satir 17).
  </action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5\frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
    - Kontrol Edilen IP tablosunda IP arama inputu var (w-64, bg-black, neon cyan text)
    - Sayfa basina 50/100/150/200 secimi dropdown var (bg-black, neon cyan text)
    - Sayfalama kontrolleri (Onceki/Sonraki) tablo altinda gorunuyor (1+ sayfa varsa)
    - Arama yapildiginda sayfa 1'e resetleniyor
    - Dropdown degistiginde sayfa 1'e resetleniyor
    - filterFlagged toggle'da sayfa 1'e resetleniyor
    - Bos sonuc mesaji arama durumuna gore degisiyor
    - TypeScript derleme hatasi yok
  </done>
</task>

</tasks>

<verification>
1. `npx tsc --noEmit` basarili (sifir hata)
2. Dosyada `ipSearchTerm`, `ipPageSize`, `ipCurrentPage` state degiskenleri mevcut
3. Sayfalama kontrolleri `totalIpPages > 1` kosulunda render ediliyor
4. Dropdown'larda `style={{ backgroundColor: '#000' }}` + `className="bg-black text-[#00F0FF]"` mevcut
</verification>

<success_criteria>
IpReputationTab'deki "Kontrol Edilen IP'ler" tablosu IpManagementPage ile ayni arama + sayfalama + dropdown tema desenine sahip. TypeScript derleme basarili.
</success_criteria>

<output>
After completion, create `.planning/quick/19-ip-itibar-sayfasi-sorgulanan-ip-tablosun/19-SUMMARY.md`
</output>
