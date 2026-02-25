---
status: testing
phase: 02-accounting-chain-migration
source: 02-01-SUMMARY.md
started: 2026-02-25T14:00:00Z
updated: 2026-02-25T14:00:00Z
---

## Current Test

number: 1
name: Upload/Download Chain Existence
expected: |
  After backend restart, `nft list table bridge accounting` shows two chains:
  - `chain upload` with hook input, priority -2, iifname "eth1"
  - `chain download` with hook output, priority -2, oifname "eth1"
awaiting: user response

## Tests

### 1. Upload/Download Chain Existence
expected: After backend restart, `nft list table bridge accounting` shows `chain upload` (hook input, priority -2, iifname eth1) and `chain download` (hook output, priority -2, oifname eth1)
result: [pending]

### 2. Device Counter Rules Present
expected: For connected devices, `nft list chain bridge accounting upload` shows `ether saddr {mac} counter` rules and `nft list chain bridge accounting download` shows `ether daddr {mac} counter` rules
result: [pending]

### 3. Counter Values Accumulate
expected: After a device sends/receives traffic, running `nft list chain bridge accounting upload` and `nft list chain bridge accounting download` shows non-zero byte/packet counters for that device's MAC
result: [pending]

### 4. Bandwidth Data in Dashboard
expected: Dashboard bandwidth widget shows device traffic data updating — devices have non-zero upload/download values
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
