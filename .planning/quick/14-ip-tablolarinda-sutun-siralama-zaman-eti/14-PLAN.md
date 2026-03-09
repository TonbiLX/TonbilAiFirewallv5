---
phase: quick-14
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/firewall/IpReputationTab.tsx
  - frontend/src/pages/IpManagementPage.tsx
autonomous: true
requirements: [QUICK-14]

must_haves:
  truths:
    - "Kontrol Edilen IP tablosunda tüm sütun başlıklarına tıklayarak sıralama yapılabilir"
    - "Güvenilir IP tablosunda sütun başlıklarına tıklayarak sıralama yapılabilir"
    - "Engellenen IP tablosunda sütun başlıklarına tıklayarak sıralama yapılabilir"
    - "Aktif sütun ok ikonu ile gösterilir (ArrowUp/ArrowDown), pasif sütunlar ArrowUpDown ile"
    - "Varsayılan sıralama tarihe göre yeniden eskiye (desc) şeklindedir"
    - "Sıralama tamamen frontend'de gerçekleşir, API çağrısı gerektirmez"
  artifacts:
    - path: "frontend/src/components/firewall/IpReputationTab.tsx"
      provides: "Kontrol Edilen IP tablosu sıralama state + sortable th'ler"
    - path: "frontend/src/pages/IpManagementPage.tsx"
      provides: "Güvenilir/Engellenen IP tabloları sıralama state + sortable th'ler"
  key_links:
    - from: "sortBy/sortOrder state"
      to: "useMemo ile filtrelenmiş + sıralanmış dizi"
      via: "localeCompare + numeric sort"
    - from: "th onClick"
      to: "setSortBy / setSortOrder toggle"
      via: "aynı sütuna tıklanırsa asc↔desc geçiş"
---

<objective>
3 ayrı tabloya (Kontrol Edilen IP, Güvenilir IP, Engellenen IP) sütun başlığı sıralaması eklemek.

Purpose: Kullanıcı sütun başlığına tıklayarak tabloyu istediği alana göre sıralayabilsin.
Output: Tamamen frontend'de çalışan, yeniden API çağrısı yapmayan sıralama sistemi.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Proje: TonbilAiOS v5, Cyberpunk Glassmorphism tema.
Ikonlar: lucide-react (ArrowUpDown, ArrowUp, ArrowDown zaten projede mevcuttur).
Build: cd /opt/tonbilaios/frontend && sudo npm run build
Deploy: Paramiko SFTP ile /tmp/ uzerinden sudo cp, sonra build + backend restart.
</context>

<interfaces>
<!-- IpReputationTab.tsx — mevcut state'ler -->
```typescript
// Mevcut state'ler (satır ~80-120 civarı)
const [ips, setIps] = useState<ReputationIp[]>([]);
const [filterFlagged, setFilterFlagged] = useState(false);
const [searchText, setSearchText] = useState("");

// Eklenecek state'ler
const [sortBy, setSortBy] = useState<keyof ReputationIp>("checked_at");
const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

// ReputationIp interface (satır 51-60)
interface ReputationIp {
  ip: string;
  abuse_score: number;
  total_reports: number;
  country: string;
  city: string;
  isp: string;
  org: string;
  checked_at: string;
}
```

<!-- IpManagementPage.tsx — mevcut state'ler -->
```typescript
// Eklenecek state'ler — Güvenilir IP tablosu
const [trustedSortBy, setTrustedSortBy] = useState<"ip_address" | "description" | "created_at">("created_at");
const [trustedSortOrder, setTrustedSortOrder] = useState<"asc" | "desc">("desc");

// Eklenecek state'ler — Engellenen IP tablosu
const [blockedSortBy, setBlockedSortBy] = useState<"ip_address" | "reason" | "blocked_at" | "is_manual">("blocked_at");
const [blockedSortOrder, setBlockedSortOrder] = useState<"asc" | "desc">("desc");

// TrustedIp type (types/index.ts'den)
interface TrustedIp { id: number; ip_address: string; description: string; created_at: string; }
// ManagedBlockedIp type
interface ManagedBlockedIp { id?: number; ip_address: string; reason?: string; blocked_at: string; is_manual: boolean; expires_at?: string; }
```

<!-- Ortak SortableHeader bileşeni pattern (inline, ayrı dosya oluşturma) -->
```tsx
// th onClick pattern
<th
  onClick={() => handleSort("ip")}
  className="... cursor-pointer select-none hover:text-white transition-colors"
>
  <span className="flex items-center gap-1">
    IP Adresi
    {sortBy === "ip" ? (
      sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
    ) : (
      <ArrowUpDown className="w-3 h-3 opacity-40" />
    )}
  </span>
</th>

// handleSort helper
function handleSort(col: typeof sortBy) {
  if (sortBy === col) setSortOrder(o => o === "asc" ? "desc" : "asc");
  else { setSortBy(col); setSortOrder("asc"); }
}

// Sıralama mantığı (useMemo veya inline)
const sortedIps = [...filteredIps].sort((a, b) => {
  const aVal = a[sortBy] ?? "";
  const bVal = b[sortBy] ?? "";
  const cmp = typeof aVal === "number"
    ? aVal - (bVal as number)
    : String(aVal).localeCompare(String(bVal));
  return sortOrder === "asc" ? cmp : -cmp;
});
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: IpReputationTab — Kontrol Edilen IP tablosuna sıralama ekle</name>
  <files>frontend/src/components/firewall/IpReputationTab.tsx</files>
  <action>
    1. Import satırına `ArrowUpDown, ArrowUp, ArrowDown` ekle (lucide-react, mevcut import bloğuna).

    2. Bileşen state'lerine ekle (filterFlagged state'inin yanına):
       ```typescript
       const [sortBy, setSortBy] = useState<keyof ReputationIp>("checked_at");
       const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
       ```

    3. handleSort fonksiyonu ekle (bileşen içinde, return'den önce):
       ```typescript
       function handleSort(col: keyof ReputationIp) {
         if (sortBy === col) setSortOrder(o => o === "asc" ? "desc" : "asc");
         else { setSortBy(col); setSortOrder("asc"); }
       }
       ```

    4. Mevcut filteredIps hesaplamasını bul (filterFlagged ve searchText kullanan kısım) — sonrasına sıralama ekle:
       ```typescript
       const sortedIps = [...filteredIps].sort((a, b) => {
         const aVal = a[sortBy] ?? "";
         const bVal = b[sortBy] ?? "";
         const cmp = typeof aVal === "number"
           ? (aVal as number) - (bVal as number)
           : String(aVal).localeCompare(String(bVal));
         return sortOrder === "asc" ? cmp : -cmp;
       });
       ```
       Eğer filteredIps mevcut değilse önce oluştur:
       ```typescript
       const filteredIps = ips.filter(ip =>
         (!filterFlagged || ip.abuse_score >= 50) &&
         (!searchText || ip.ip.includes(searchText) || ip.country?.includes(searchText) || ip.isp?.includes(searchText))
       );
       ```
       Ardından map içinde `ips` yerine `sortedIps` kullan.

    5. thead içindeki her th'yi tıklanabilir yap. Her sütun için:
       - `cursor-pointer select-none hover:text-white transition-colors` class'ı ekle
       - onClick={() => handleSort("ALAN_ADI")} ekle
       - İçeriği `<span className="flex items-center gap-1.5">BASLIK {sortIcon}</span>` ile sar
       - sortIcon: sortBy === "ALAN" ? (sortOrder === "asc" ? <ArrowUp className="w-3 h-3"/> : <ArrowDown className="w-3 h-3"/>) : <ArrowUpDown className="w-3 h-3 opacity-40"/>

       Sütun → alan eşlemesi:
       - "IP Adresi" → "ip"
       - "Skor" → "abuse_score"
       - "Ülke" → "country"
       - "Şehir" → "city"
       - "ISP" → "isp"
       - "Kontrol Tarihi" → "checked_at"

    NOT: `ips.map(...)` satırını bul ve `sortedIps.map(...)` olarak değiştir.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>IpReputationTab.tsx TypeScript hatası yok; Kontrol Edilen IP tablosunda 6 sütun da sıralanabilir; varsayılan sıralama "checked_at" desc.</done>
</task>

<task type="auto">
  <name>Task 2: IpManagementPage — Güvenilir IP ve Engellenen IP tablolarına sıralama ekle</name>
  <files>frontend/src/pages/IpManagementPage.tsx</files>
  <action>
    1. Import satırına `ArrowUpDown, ArrowUp, ArrowDown` ekle (mevcut import bloğuna).

    2. State tanımlarına (submitting state'inin yanına) ekle:
       ```typescript
       // Trusted IP sıralama
       const [trustedSortBy, setTrustedSortBy] = useState<"ip_address" | "description" | "created_at">("created_at");
       const [trustedSortOrder, setTrustedSortOrder] = useState<"asc" | "desc">("desc");
       // Blocked IP sıralama
       const [blockedSortBy, setBlockedSortBy] = useState<"ip_address" | "reason" | "blocked_at" | "is_manual">("blocked_at");
       const [blockedSortOrder, setBlockedSortOrder] = useState<"asc" | "desc">("desc");
       ```

    3. İki ayrı helper fonksiyon ekle (return'den önce):
       ```typescript
       function handleTrustedSort(col: typeof trustedSortBy) {
         if (trustedSortBy === col) setTrustedSortOrder(o => o === "asc" ? "desc" : "asc");
         else { setTrustedSortBy(col); setTrustedSortOrder("asc"); }
       }
       function handleBlockedSort(col: typeof blockedSortBy) {
         if (blockedSortBy === col) setBlockedSortOrder(o => o === "asc" ? "desc" : "asc");
         else { setBlockedSortBy(col); setBlockedSortOrder("asc"); }
       }
       ```

    4. Güvenilir IP render bloğuna (activeTab === "trusted" içine, tablo render'ından hemen önce) sıralanmış dizi ekle:
       ```typescript
       const sortedTrustedIps = [...trustedIps].sort((a, b) => {
         const aVal = a[trustedSortBy] ?? "";
         const bVal = b[trustedSortBy] ?? "";
         const cmp = String(aVal).localeCompare(String(bVal));
         return trustedSortOrder === "asc" ? cmp : -cmp;
       });
       ```
       `trustedIps.map(...)` → `sortedTrustedIps.map(...)` olarak değiştir.

    5. Güvenilir IP tablosunun thead'ini güncelle — her th tıklanabilir olsun:
       - "IP Adresi" → handleTrustedSort("ip_address")
       - "Açıklama" → handleTrustedSort("description")
       - "Ekleme Tarihi" → handleTrustedSort("created_at")
       - "İşlem" sütunu tıklanamaz (text-right, no onClick)

       Her th class'ına: `cursor-pointer select-none hover:text-white transition-colors` ekle.
       İçeriği `<span className="flex items-center gap-1.5">...</span>` ile sar, sortIcon ekle.

    6. Engellenen IP render bloğuna (activeTab === "blocked" içine, tablo render'ından hemen önce) sıralanmış dizi ekle:
       ```typescript
       const sortedBlockedIps = [...blockedIps].sort((a, b) => {
         const aVal = a[blockedSortBy] ?? "";
         const bVal = b[blockedSortBy] ?? "";
         if (blockedSortBy === "is_manual") {
           const cmp = (a.is_manual ? 1 : 0) - (b.is_manual ? 1 : 0);
           return blockedSortOrder === "asc" ? cmp : -cmp;
         }
         const cmp = String(aVal).localeCompare(String(bVal));
         return blockedSortOrder === "asc" ? cmp : -cmp;
       });
       ```
       `blockedIps.map(...)` → `sortedBlockedIps.map(...)` olarak değiştir.

    7. Engellenen IP tablosunun thead'ini güncelle — her th tıklanabilir olsun:
       - "IP Adresi" → handleBlockedSort("ip_address")
       - "Sebep" → handleBlockedSort("reason")
       - "Engel Tarihi" → handleBlockedSort("blocked_at")
       - "Kaynak" → handleBlockedSort("is_manual")
       - "Kalan Sure" sütunu: tıklanamaz (hesaplanan değer, string değil)
       - "İşlem" sütunu: tıklanamaz

       Her sıralanabilir th class'ına: `cursor-pointer select-none hover:text-white transition-colors` ekle.
       İçeriği `<span className="flex items-center gap-1.5">...</span>` ile sar, sortIcon ekle.

    NOT: sortIcon pattern her iki tablo için aynı — sadece state adları farklı (trustedSortBy vs blockedSortBy).
    NOT: "Kalan Sure" ve "İşlem" sütunları sıralanabilir OLMAYACAK — bu sütunlara onClick ve ikon ekleme.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>IpManagementPage.tsx TypeScript hatası yok; Güvenilir IP tablosunda 3 sütun (IP/Açıklama/Tarih) sıralanabilir; Engellenen IP tablosunda 4 sütun (IP/Sebep/Tarih/Kaynak) sıralanabilir; varsayılan sıralama her ikisinde de tarihe göre desc.</done>
</task>

<task type="auto">
  <name>Task 3: Build + Deploy</name>
  <files>deploy_quick14.py</files>
  <action>
    Aşağıdaki Python deploy scriptini oluştur ve çalıştır. Script:
    1. Frontend dosyalarını SFTP ile Pi'ye gönderir (IpReputationTab.tsx + IpManagementPage.tsx)
    2. Pi'de frontend build çalıştırır
    3. Backend restart YAPMAZ (sadece frontend değişikliği)

    ```python
    #!/usr/bin/env python3
    """Quick 14 deploy: IP tablo siralama — frontend only"""
    import paramiko, os, time

    JUMP_HOST = "pi.tonbil.com"
    JUMP_PORT = 2323
    PI_HOST = "192.168.1.2"
    USER = "admin"
    PASS = "benbuyum9087"
    LOCAL_BASE = "C:/Nextcloud2/TonbilAiFirevallv5/frontend/src"
    REMOTE_BASE = "/opt/tonbilaios/frontend/src"

    FILES = [
        ("components/firewall/IpReputationTab.tsx", "components/firewall/IpReputationTab.tsx"),
        ("pages/IpManagementPage.tsx", "pages/IpManagementPage.tsx"),
    ]

    def run(ssh, cmd):
        _, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out.strip())
        if err: print("ERR:", err.strip())
        return out

    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USER, password=PASS)
    transport = jump.get_transport()
    channel = transport.open_channel("direct-tcpip", (PI_HOST, 22), ("127.0.0.1", 0))

    pi = paramiko.SSHClient()
    pi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pi.connect(PI_HOST, username=USER, password=PASS, sock=channel)

    sftp = pi.open_sftp()
    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_BASE, local_rel).replace("\\", "/")
        tmp_path = f"/tmp/{os.path.basename(local_rel)}"
        remote_path = f"{REMOTE_BASE}/{remote_rel}"
        print(f"  Upload: {local_rel}")
        sftp.put(local_path, tmp_path)
        run(pi, f"sudo cp {tmp_path} {remote_path}")
    sftp.close()

    print("\nBuilding frontend...")
    run(pi, "cd /opt/tonbilaios/frontend && sudo npm run build 2>&1")
    print("Build complete.")

    pi.close()
    jump.close()
    print("\nDeploy OK — backend restart gerekmez.")
    ```

    Scripti kaydet ve çalıştır:
    ```bash
    python3 C:/Nextcloud2/TonbilAiFirevallv5/deploy_quick14.py
    ```

    Eğer build hatası alınırsa hata çıktısını analiz et ve TypeScript sorununu düzelt.
  </action>
  <verify>
    <automated>python3 C:/Nextcloud2/TonbilAiFirevallv5/deploy_quick14.py 2>&1 | tail -5</automated>
  </verify>
  <done>Deploy OK mesajı görünür; Pi'de frontend build başarılı tamamlanır; tarayıcıda IP tabloları sütun başlıklarına tıklanabilir.</done>
</task>

</tasks>

<verification>
- `npx tsc --noEmit` hata yok
- IpReputationTab: checked_at'e tıklanınca desc/asc toggle çalışır
- IpManagementPage trusted tab: created_at'e tıklanınca desc/asc toggle çalışır
- IpManagementPage blocked tab: blocked_at'e tıklanınca desc/asc toggle çalışır
- Aktif sütunda ArrowUp/ArrowDown, diğerlerinde ArrowUpDown (opacity-40) görünür
- "İşlem" ve "Kalan Sure" sütunlarında sıralama ikonu YOK
</verification>

<success_criteria>
3 tabloda toplam 13 sıralanabilir sütun başlığı çalışır:
- Kontrol Edilen IP: 6 sütun (ip, abuse_score, country, city, isp, checked_at)
- Güvenilir IP: 3 sütun (ip_address, description, created_at)
- Engellenen IP: 4 sütun (ip_address, reason, blocked_at, is_manual)
Varsayılan sıralama her tabloda tarihe göre yeniden eskiye (desc).
Build başarılı, Pi'de canlıya alındı.
</success_criteria>

<output>
Tamamlandıktan sonra `.planning/quick/14-ip-tablolarinda-sutun-siralama-zaman-eti/14-SUMMARY.md` dosyasını oluştur.
</output>
