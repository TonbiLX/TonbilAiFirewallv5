---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md
autonomous: true
requirements: [QUICK-2]
must_haves:
  truths:
    - "CLAUDE.md title reads TonbilAiOS v5"
    - "No references to TonbilAiFirewallV41 remain in the file"
    - "Local copy path points to TonbilAiFirevallv5"
  artifacts:
    - path: "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md"
      provides: "Updated project documentation for v5"
      contains: "TonbilAiOS v5"
  key_links: []
---

<objective>
Update CLAUDE.md in TonbilAiFirevallv5 directory to reflect v5 naming.

Purpose: The V5 copy still has V41 references in project title and local paths. These must be updated so Claude and developers working in the V5 directory see correct project identity and paths.
Output: Updated CLAUDE.md with all V41 references replaced by V5 equivalents.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update CLAUDE.md references from V41 to V5</name>
  <files>E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md</files>
  <action>
    Read E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md and apply these specific changes:

    1. Line 1 title: Change `# TonbilAiOS - AI-Powered Router Management System` to `# TonbilAiOS v5 - AI-Powered Router Management System`

    2. Line 329 sync script comment: Change `E:\Nextcloud-Yeni\TonbilAiFirewallV41` to `E:\Nextcloud-Yeni\TonbilAiFirevallv5`
       (inside: `# Tum frontend + backend dosyalarini E:\Nextcloud-Yeni\TonbilAiFirewallV41 altina indirir`)

    3. Line 339 Onemli Dosya Konumlari table: Change `E:\Nextcloud-Yeni\TonbilAiFirewallV41` to `E:\Nextcloud-Yeni\TonbilAiFirevallv5`
       (inside: `| Lokal kopya | E:\Nextcloud-Yeni\TonbilAiFirewallV41 | PC sync dizini |`)

    These are the ONLY three occurrences of the old naming. Do NOT change any other content. Use the Edit tool for surgical changes.
  </action>
  <verify>
    <automated>grep -c "TonbilAiFirewallV41" "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md" || true</automated>
    <manual>Grep must return 0 (no remaining V41 references). Also verify "TonbilAiOS v5" appears on line 1.</manual>
  </verify>
  <done>
    - Title reads "TonbilAiOS v5 - AI-Powered Router Management System"
    - Zero occurrences of "TonbilAiFirewallV41" in the file
    - Both local path references point to "TonbilAiFirevallv5"
    - All other content unchanged
  </done>
</task>

</tasks>

<verification>
- `grep -c "TonbilAiFirewallV41" "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md"` returns 0
- `grep -c "TonbilAiOS v5" "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md"` returns 1
- `grep -c "TonbilAiFirevallv5" "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md"` returns 2
</verification>

<success_criteria>
CLAUDE.md in TonbilAiFirevallv5 directory has project name updated to v5, all local directory paths reference TonbilAiFirevallv5, and no TonbilAiFirewallV41 references remain.
</success_criteria>

<output>
After completion, create `.planning/quick/2-tonbilaifirevallv5-klasorunde-claude-md-/2-SUMMARY.md`
</output>
