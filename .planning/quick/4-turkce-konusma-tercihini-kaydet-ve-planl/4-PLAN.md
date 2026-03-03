---
phase: quick-4
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [CLAUDE.md]
autonomous: true
requirements: [QUICK-4]

must_haves:
  truths:
    - "CLAUDE.md dosyasinda Turkce iletisim zorunlulugu acikca belirtilmis"
    - "Yeni oturumlar bu talimati okuyarak Turkce iletisim kurar"
  artifacts:
    - path: "CLAUDE.md"
      provides: "Dil / Language bolumu"
      contains: "Dil / Language"
  key_links: []
---

<objective>
CLAUDE.md dosyasina "Dil / Language" bolumu ekleyerek tum gelecek oturumlarin kullaniciyla Turkce iletisim kurmasini saglamak.

Purpose: Kullanicinin dil tercihini proje talimatlarinda kalici hale getirmek
Output: Guncellenmis CLAUDE.md dosyasi
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: CLAUDE.md dosyasina Dil / Language bolumu ekle</name>
  <files>CLAUDE.md</files>
  <action>
CLAUDE.md dosyasinin EN BASINA (ilk satir olarak, "# TonbilAiOS v5" basligindan ONCE) asagidaki bolumu ekle:

```markdown
## Dil / Language

**ZORUNLU:** Kullaniciyla tum iletisim Turkce yapilmalidir. Commit mesajlari, kod yorumlari ve degisken isimleri Ingilizce kalabilir ancak kullaniciyla yapilan her konusma, aciklama, soru ve rapor Turkce olmalidir.

---
```

Bu bolum dosyanin en basinda olmali ki her oturumda ilk okunan talimat olsun. Dosyanin geri kalani (# TonbilAiOS v5 basligindan itibaren) aynen korunmali.
  </action>
  <verify>
    <automated>grep -n "Dil / Language" CLAUDE.md && grep -n "ZORUNLU" CLAUDE.md && head -8 CLAUDE.md</automated>
  </verify>
  <done>CLAUDE.md dosyasinin ilk satirlarinda "## Dil / Language" bolumu mevcut ve Turkce iletisim zorunlulugu acikca belirtilmis</done>
</task>

</tasks>

<verification>
- CLAUDE.md dosyasinin ilk bolumleri "## Dil / Language" iceriyor
- "ZORUNLU" kelimesi ve Turkce iletisim talimati mevcut
- Dosyanin geri kalan icerigi bozulmamis (# TonbilAiOS v5 basligi ve sonrasi aynen duruyor)
</verification>

<success_criteria>
- CLAUDE.md dosyasinda Turkce iletisim talimati kalici olarak yer aliyor
- Talimat dosyanin en basinda konumlanmis (ilk okunan bolum)
</success_criteria>

<output>
After completion, create `.planning/quick/4-turkce-konusma-tercihini-kaydet-ve-planl/4-SUMMARY.md`
</output>
