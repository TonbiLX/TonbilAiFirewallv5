# Codebase Concerns

**Analysis Date:** 2026-02-25

## Tech Debt

**Large monolithic files:**
- Files: `backend/app/api/v1/chat.py` (1983 lines), `backend/app/services/ai_engine.py` (1321 lines), `backend/app/workers/threat_analyzer.py` (1379 lines), `backend/app/hal/linux_nftables.py` (1409 lines)
- Impact: Difficult to test, maintain, and reason about. Complex interdependencies between functions increase bug surface area.
- Fix approach: Decompose into smaller modules with clear responsibility boundaries. Extract common patterns (entity detection, domain matching, rate limiting) into reusable utilities.

**Global mutable state in workers:**
- Files: `backend/app/workers/dns_proxy.py` (lines 37-88: `_wan_ip_cache`, `_rate_limit_buckets`), `backend/app/workers/flow_tracker.py` (lines 43-45: `_prev_counters`, `_last_seen`), `backend/app/workers/device_discovery.py` (lines 27-30: `_known_ips`, `_FAILED_IPS`)
- Impact: Race conditions in multi-worker scenarios, unpredictable behavior during concurrent updates, memory leaks from stale data structures.
- Fix approach: Replace module-level globals with proper class-based state management. Use asyncio.Lock for thread-safe updates. Implement proper cleanup mechanisms (TTL-based eviction).

**Bare exception handlers:**
- Files: `backend/app/workers/dns_proxy.py` (56-57: `except Exception: continue`), `backend/app/workers/blocklist_worker.py` (62-64, 72-73: bare except), `backend/app/workers/device_discovery.py` (58: `except Exception: pass`)
- Impact: Swallows errors silently, makes debugging impossible, masks real failures under generic handlers.
- Fix approach: Catch specific exception types (ConnectionError, TimeoutError, etc.). Log all exceptions with context. Re-raise or handle explicitly based on recovery strategy.

**Inconsistent error handling patterns:**
- Files: `backend/app/api/v1/devices.py`, `backend/app/api/v1/firewall.py`, `backend/app/api/v1/dns.py`
- Impact: Some endpoints return 500 on recoverable errors, others silently fail, inconsistent error message format across API.
- Fix approach: Create centralized error handling middleware. Define standard error responses. Use custom exception classes for different error categories.

## Known Bugs

**WAN IP detection fragility:**
- Symptoms: DNS proxy fails to report client IP correctly when using DNS-over-TLS from external clients; cloud-based IP detection services may be unavailable
- Files: `backend/app/workers/dns_proxy.py` (lines 42-58: `_detect_wan_ip()`)
- Trigger: Network outage from external services (api.ipify.org, ifconfig.me, icanhazip.com) or environment variable `WAN_IP` not set
- Workaround: Set `WAN_IP` environment variable manually on router; DNS proxy falls back to empty string on detection failure

**Rate limiting bucket memory leak:**
- Symptoms: Memory usage of DNS proxy increases over time; stale IPs accumulate indefinitely during quiet periods
- Files: `backend/app/workers/dns_proxy.py` (lines 85-103: rate limit cleanup)
- Trigger: Cleanup runs only every 60 seconds; if buckets are created and never accessed again, they remain indefinitely
- Workaround: Restart DNS proxy worker periodically (systemd timer) or reduce cleanup interval

**Per-flow tracking loses data between syncs:**
- Symptoms: Short-lived flows (<20 seconds) may not appear in MariaDB at all; only Redis captures all flows
- Files: `backend/app/workers/flow_tracker.py` (lines 27-29: `FLOW_TRACK_INTERVAL=20s`, `FLOW_DB_SYNC_INTERVAL=60s`)
- Trigger: Connection completes before 60-second DB sync interval; flow only exists in Redis (TTL 60s)
- Workaround: Use Redis live flow data for real-time dashboard; accept historical data from DB is incomplete for very short flows

**Device discovery hostname resolution hangs:**
- Symptoms: Device page loading freezes; DNS lookups block on unresponsive devices
- Files: `backend/app/workers/device_discovery.py` (lines 32-33: ThreadPoolExecutor with timeout)
- Trigger: Devices with non-responsive DNS names or network connectivity issues
- Workaround: Timeout is in place (5s in subprocess.run), but ThreadPoolExecutor context is global and may queue tasks

**DNS profil domain rebuild race condition:**
- Symptoms: New profile with categories created, but domain filtering doesn't apply immediately; devices assigned to profile may hit old Redis key
- Files: `backend/app/workers/blocklist_worker.py`, `backend/app/api/v1/profiles.py`
- Trigger: Profile creation → domain rebuild async task takes time; device assignment executes before Redis key exists
- Workaround: Manual refresh of DNS rules (API endpoint); page reload forces new Redis checks

## Security Considerations

**Session/Token IP validation can be bypassed in proxy scenarios:**
- Risk: IP binding in JWT prevents legitimate proxy usage (shared network, load balancers); strict IP checking may lock out users on network changes
- Files: `backend/app/api/deps.py` (lines 141-152: IP validation), `backend/app/config.py` (TRUSTED_PROXIES)
- Current mitigation: `TRUSTED_PROXIES` configuration allows bypassing IP check for known proxies; X-Forwarded-For header trusted only from these proxies
- Recommendations: Log IP mismatches as warnings (not errors); add grace period (5 min) before enforcing re-auth on IP change; document proxy configuration clearly

**DNS proxy accepts unsafe query types without rate limiting per type:**
- Risk: Attackers can craft high-entropy queries (TXT, ANY) to evade DGA detection and flood logs; suspicious query types allowed from local network
- Files: `backend/app/workers/dns_proxy.py` (lines 137-139: BLOCKED_QTYPES = {10, 252, 255}), `backend/app/workers/threat_analyzer.py` (line 32: SUSPICIOUS_QTYPES)
- Current mitigation: Local queries to TXT not blocked; threat analyzer detects DGA pattern after fact
- Recommendations: Add per-qtype rate limits; block ANY/HINFO/NULL completely (not just AXFR); validate query format strictly before processing

**Redis cache keys predictable (no namespace isolation):**
- Risk: If Redis accessed without auth, attacker can enumerate `dns:*` keys and modify domain blocklists in-memory
- Files: `backend/app/db/redis_client.py`, all workers using Redis
- Current mitigation: Redis bound to localhost (127.0.0.1) only; no network exposure
- Recommendations: Add Redis AUTH password; namespace keys with application UUID; implement Redis ACL for feature separation

**SSRF protection in blocklist download bypassed by localhost:**
- Risk: Malicious blocklist URL could point to internal services (http://127.0.0.1:8000 for API access)
- Files: `backend/app/workers/blocklist_worker.py` (lines 82-150 approx: URL download)
- Current mitigation: SSRF check prevents special/private IPs (10.x, 172.16-31.x, 192.168.x)
- Recommendations: Add explicit allowlist for CDNs only (Cloudflare, GitHub raw); block http:// scheme entirely (https only); validate domain TLD against ICANN registry

**AI chat command execution inadequate input validation:**
- Risk: Chat parser creates database/firewall objects from user input with limited validation; malformed entity values could cause crashes
- Files: `backend/app/api/v1/chat.py` (lines 98-500 approx: execute_commands), `backend/app/services/ai_engine.py` (lines 170-250 approx: entity extraction)
- Current mitigation: Confidence threshold (0.15) filters low-confidence intents; TF-IDF intent classification
- Recommendations: Add strict schema validation before DB/hardware operations; sanitize all chat-derived strings; implement dry-run mode for destructive commands

## Performance Bottlenecks

**Chat API blocks on LLM inference:**
- Problem: Chat endpoint waits for full LLM response (potentially 5-10 seconds); blocks browser until complete
- Files: `backend/app/api/v1/chat.py` (lines 500-1000 approx: chat handler), `backend/app/services/llm_service.py` (LLM call)
- Cause: Synchronous LLM API call without streaming or worker queue
- Improvement path: Implement streaming response (SSE); move LLM to background worker with WebSocket feedback; cache common answers

**Threat analyzer scans all DNS queries in memory:**
- Problem: Every query hits Python dictionary/set lookups for entropy, patterns, IPs; O(n) complexity for pattern matching
- Files: `backend/app/workers/threat_analyzer.py` (lines 100-300 approx: threat detection)
- Cause: No indexing on threat scores; subnet flood detection iterates all recent IPs per query
- Improvement path: Use Redis sorted sets (ZSET) for threat scores with TTL; pre-compute subnet masks; batch analysis every N queries

**Frontend loads all widgets instantly:**
- Problem: DashboardPage renders all 11 widgets simultaneously; network requests fire in parallel, blocking rendering
- Files: `frontend/src/pages/DashboardPage.tsx`
- Cause: No lazy loading or suspense boundaries
- Improvement path: Implement React.lazy() for widget components; use Suspense with fallback skeletons; stagger API requests by widget priority

**Flow tracker iterates all flows every 20 seconds:**
- Problem: `conntrack -L | grep ...` output parsed as plain text; no connection pooling or incremental tracking
- Files: `backend/app/workers/flow_tracker.py` (lines 400-500 approx: conntrack parsing)
- Cause: Full conntrack state dump fetched each cycle, even if only small changes occurred
- Improvement path: Use libnetfilter_conntrack API for incremental updates; implement efficient diff algorithm; cache flow state with version numbers

**MariaDB disk I/O from 60-second sync intervals:**
- Problem: Every 60 seconds, all flow/traffic data bulk-inserted; creates write spikes and lock contention
- Files: `backend/app/workers/flow_tracker.py` (line 28: FLOW_DB_SYNC_INTERVAL), `backend/app/workers/traffic_monitor.py`
- Cause: Batching all writes into single interval instead of continuous insert
- Improvement path: Switch to incremental inserts (every 5s for high-volume tables); implement write-ahead log; add database connection pooling with queue

## Fragile Areas

**DNS proxy authentication bypass possible in DoT mode:**
- Files: `backend/app/workers/dns_proxy.py` (lines 300-400 approx: DoT handler)
- Why fragile: TLS certificate validation may not enforce hostname matching; self-signed certs accepted without verification
- Safe modification: Read DoT handler code completely before changes; add unit tests for certificate validation; document cert pinning requirements
- Test coverage: No explicit DoT integration tests visible; gaps in TLS parameter validation

**Device profiling logic depends on both DB and Redis consistency:**
- Files: `backend/app/api/v1/profiles.py`, `backend/app/workers/blocklist_worker.py`, `backend/app/models/device.py`
- Why fragile: Profile → Device relationship must be synced to Redis cache; if rebuild fails silently, device reverts to old profile or loses filtering
- Safe modification: Always rebuild after profile change; add Redis validation endpoint; implement double-write pattern (DB then Redis)
- Test coverage: No integration tests for profile reassignment; gaps in cache invalidation scenarios

**Firewall rule synchronization between nftables and DB:**
- Files: `backend/app/hal/linux_nftables.py`, `backend/app/api/v1/firewall.py`, `backend/app/main.py` (lines 101-120: sync on startup)
- Why fragile: nftables rules can be modified externally; no polling to detect divergence; missing rules after unplanned restart
- Safe modification: Before any nftables change, read current state; use JSON snapshots for diff; implement audit log of all changes
- Test coverage: No tests for ruleset corruption recovery; gaps in external modification detection

**LLM chat response schema mismatch:**
- Files: `backend/app/api/v1/chat.py`, `backend/app/services/chat_formatter.py`, `frontend/src/pages/ChatPage.tsx`
- Why fragile: LLM output format not strictly validated; parser assumes response contains specific fields; missing fields cause null reference errors
- Safe modification: Add strict Pydantic schema validation; implement fallback formatter for unparseable responses; add response schema version
- Test coverage: No end-to-end LLM response tests; gaps in malformed response handling

## Scaling Limits

**Redis as single cache layer (no persistence):**
- Current capacity: ~10,000 active flows, 1,000 DNS blocked domains, 100 device profiles
- Limit: On restart, all cache keys lost; DNS filtering unavailable until rebuild (5-10 min); leads to temporary unblocked ads/malware
- Scaling path: Enable Redis RDB/AOF persistence; use Redis Sentinel for HA; implement cache warming on startup

**MariaDB connection pool size fixed:**
- Current capacity: Likely 5-10 connections
- Limit: Peak traffic (all users refresh simultaneously) hits pool exhaustion; API returns 503
- Scaling path: Increase pool size; implement request queuing with timeout; add connection pool metrics/alerts; consider read replicas for dashboards

**WebSocket broadcast to all connected clients:**
- Current capacity: ~10-20 concurrent browser connections
- Limit: Broadcasting to 100+ clients causes thread blocking; real-time data updates lag
- Scaling path: Implement message batching; use pub/sub with client-side subscriptions; compress WebSocket payloads; consider GraphQL subscriptions

**DNS query logging to MariaDB (every query):**
- Current capacity: ~1,000 queries/minute (home network typical)
- Limit: High-traffic networks (ISP, business) = millions/day → disk full in days
- Scaling path: Implement sampling (log 1 in 10); aggregate queries by domain hourly; use time-series DB (InfluxDB); implement retention policy

**Threat analyzer subnet scanning (O(n) per query):**
- Current capacity: ~100 queries/min from untrusted IPs
- Limit: Coordinated attack with 10,000 queries/min triggers 100% CPU in Python thread
- Scaling path: Pre-compute /24 subnets into Redis ZSET; use bitwise operations for pattern matching; offload to nftables rules layer

## Dependencies at Risk

**FastAPI/Pydantic schema generation for 30+ models:**
- Risk: Circular import dependencies; schema validation overhead grows quadratically with models; model changes break multiple endpoints
- Files: `backend/app/models/`, `backend/app/schemas/`
- Impact: Adding new field requires updates to 3+ files (model, schema, migration); easy to forget → validation gaps
- Migration plan: Consolidate into single schema module; use Pydantic model_validate_json for direct DB-to-API serialization; implement schema versioning

**Custom DNS proxy implementation vs. standard BIND:**
- Risk: Complex DNS parsing logic duplicates BIND functionality; bugs in recursive resolution, DNSSEC validation, zone transfers
- Files: `backend/app/workers/dns_proxy.py` (~1100 lines)
- Impact: If DNS-over-TLS fails, users lose network entirely (no fallback to system resolver)
- Migration plan: Evaluate dnsmasq integration (simpler); implement BIND on separate port for redundancy; use dnscrypt-proxy for DoT

**React 18 + TypeScript strict mode + 50+ component files:**
- Risk: Type safety gaps in large files (1200+ lines); prop drilling through 5+ component levels; state synchronization bugs
- Files: `frontend/src/pages/*`, `frontend/src/components/*`
- Impact: Runtime errors in production (null reference in DeviceDetailPage for large data)
- Migration plan: Migrate to Zustand/Jotai for global state; split large pages into smaller components; enable TypeScript strict checking everywhere

**Custom AI NLP engine vs. OpenAI/Gemini:**
- Risk: Custom TF-IDF parser incomplete for Turkish; fuzzy matching may miss intent; updates require retraining entire engine
- Files: `backend/app/services/ai_engine.py`, `backend/app/api/v1/chat.py`
- Impact: Chat fails for uncommon commands; requires manual keyword updates
- Migration plan: Integrate Vertex AI (Turkish support); implement fallback to keyword-based rules; cache successful parses for reuse

## Missing Critical Features

**No backup/restore for DNS blocklists and firewall rules:**
- Problem: If MariaDB corrupted, all rules lost; no version history; no disaster recovery
- Impact: Network filtering completely lost; must rebuild rules manually
- Add: Automated daily export to JSON file; versioned backups in /opt/tonbilaios/backups; restore endpoint

**No audit log for admin actions:**
- Problem: Can't trace who changed what firewall rule or disabled a device; security compliance violation
- Impact: Breach investigation impossible; can't prove rule authorship
- Add: Log all API mutations (POST/PATCH/DELETE) with username, timestamp, before/after state; store in MariaDB audit table (immutable)

**No rate limiting on public-facing endpoints:**
- Problem: Chat, DNS, traffic endpoints exposed without request throttling; attackers can DoS via API
- Impact: API consumed entirely by malicious requests
- Add: Implement per-user/IP rate limits using Redis; add circuit breaker for downstream services; return 429 on limit

**No alerting mechanism for critical events:**
- Problem: Threat analyzer detects threats but users unaware; no notification system (besides Telegram)
- Impact: Active attacks go unnoticed if Telegram integration fails
- Add: Email alerts; syslog integration; Slack webhooks; dashboard alert widget

## Test Coverage Gaps

**DNS proxy DoT (DNS-over-TLS) untested:**
- What's not tested: TLS handshake success/failure; certificate validation; client IP extraction from DoT context
- Files: `backend/app/workers/dns_proxy.py` (lines 600-700 approx: DoT handler)
- Risk: Unencrypted fallback possible; privacy leak if TLS validation bypassed
- Priority: High

**Flow tracker conntrack parsing under malformed input:**
- What's not tested: Missing fields in conntrack output; IPv6 addresses; timeout handling for stuck connections
- Files: `backend/app/workers/flow_tracker.py` (lines 248-330: parse_conntrack_line)
- Risk: Parser crashes on unexpected format; flows dropped silently
- Priority: Medium

**Chat NLP intent classification with ambiguous input:**
- What's not tested: Multiple intents in single message; entity extraction conflicts; low-confidence fallback behavior
- Files: `backend/app/services/ai_engine.py` (lines 200-350: intent scoring), `backend/app/api/v1/chat.py` (lines 400-600: command parsing)
- Risk: Unintended commands executed (disable all devices instead of one); silent failures
- Priority: High

**Frontend widget layout breakage on unsupported screen sizes:**
- What's not tested: Mobile (< 768px); TV displays (> 2560px); tablet landscape vs portrait
- Files: `frontend/src/components/dashboard/DashboardGrid.tsx`, `frontend/src/config/widgetRegistry.tsx`
- Risk: Dashboard layout jumps or widgets stack unexpectedly
- Priority: Medium

**Firewall rule conflict detection:**
- What's not tested: Overlapping IP ranges; port conflicts; rule precedence edge cases
- Files: `backend/app/api/v1/firewall.py`, `backend/app/hal/linux_nftables.py`
- Risk: Conflicting rules silently overwrite; blocking rule becomes allow rule
- Priority: Medium

**Profile-to-device sync failures:**
- What's not tested: Partial sync (DB succeeds, Redis fails); concurrent profile edits; device removal during sync
- Files: `backend/app/api/v1/profiles.py`, `backend/app/workers/blocklist_worker.py`
- Risk: Device inherits wrong profile; filtering disabled unexpectedly
- Priority: High

---

*Concerns audit: 2026-02-25*
