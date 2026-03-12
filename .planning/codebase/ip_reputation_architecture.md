# IP Reputation System Architecture

**Analysis Date:** 2026-03-12

## Pattern Overview

**Overall:** Event-driven worker + REST API + dual storage (Redis cache + MariaDB persistent)

**Key Characteristics:**
- Background worker polls active connections every 300s and checks IP reputation via AbuseIPDB + GeoIP
- Three AbuseIPDB API pools tracked independently: check (per-IP), check-block (subnet), blacklist (bulk)
- Dual storage: Redis HASH for hot cache (24h TTL), MariaDB for persistent history
- Automatic escalation: high-score IPs trigger auto-block via `threat_analyzer` + nftables
- Critical IPs (score >= 80) automatically trigger /24 subnet analysis via `check_abuseipdb_block()`

## System Components

### 1. IP Reputation Worker (Background)

**Location:** `backend/app/workers/ip_reputation.py`

**Purpose:** Continuously monitors active network flows and checks external IPs against AbuseIPDB and ip-api.com GeoIP.

**Lifecycle:**
- Started in `backend/app/main.py` via `asyncio.create_task(start_ip_reputation())`
- 180s startup delay (waits for other workers)
- Runs `_run_reputation_cycle()` every 300s in infinite loop
- Cancelled on application shutdown

**Cycle Flow:**
1. Check `reputation:enabled` Redis flag (skip if "0")
2. Auto-fetch blacklist if 24h since last fetch
3. Load blocked countries list from Redis
4. Get AbuseIPDB API key from Redis
5. Collect active external IPs from flow tracker (`flow:active_ids` + `flow:live:{id}`)
6. Filter already-cached IPs (`reputation:ip:{ip}` exists check)
7. Process max 10 unchecked IPs per cycle
8. For each IP: AbuseIPDB check + GeoIP lookup + cache + UPSERT to SQL
9. Score >= 80: CRITICAL AiInsight + Telegram + auto-block + auto subnet /24 check
10. Score >= 50: WARNING AiInsight + Telegram
11. Country block check (independent of score)

**Key Functions:**
- `start_ip_reputation()` - main entry point, infinite loop
- `_run_reputation_cycle()` - single cycle logic
- `_process_ip(ip, api_key, redis)` - per-IP processing pipeline
- `_get_active_external_ips()` - collects public IPs from flow tracker Redis data
- `check_abuseipdb(ip, api_key)` - single IP AbuseIPDB query
- `check_geoip(ip)` - ip-api.com GeoIP query
- `fetch_abuseipdb_blacklist(force)` - bulk blacklist download
- `check_abuseipdb_block(subnet, api_key, auto_block)` - subnet CIDR analysis
- `_check_block_for_critical_ip(ip, api_key)` - auto-triggered /24 subnet check for critical IPs
- `_check_country_block(ip, country_code, blocked_countries)` - country-based blocking

**Configuration Constants:**
```python
STARTUP_DELAY        = 180    # seconds
CHECK_INTERVAL       = 300    # seconds between cycles
MAX_CHECKS_PER_CYCLE = 10     # max IPs per cycle
CACHE_TTL            = 86400  # Redis cache TTL (24h)
DAILY_LIMIT          = 900    # AbuseIPDB daily limit buffer (max 1000, 100 buffer)
GEOIP_SLEEP          = 1.5    # ip-api.com rate limit (40/min max)
HTTP_TIMEOUT         = 10     # HTTP request timeout
CHECK_BLOCK_AUTO_THRESHOLD = 3   # malicious IPs in subnet to trigger auto-block
CHECK_BLOCK_MIN_SCORE      = 50  # minimum score to count as malicious in subnet
```

### 2. IP Reputation API

**Location:** `backend/app/api/v1/ip_reputation.py`
**Route prefix:** `/api/v1/ip-reputation` (registered in `backend/app/api/v1/router.py`)

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/config` | Get reputation config (enabled, masked API key, blocked countries) |
| PUT | `/config` | Update config (enabled, API key, blocked countries) |
| GET | `/summary` | Stats: total checked, critical/warning counts, daily usage, AbuseIPDB rate limits |
| GET | `/ips` | List checked IPs (SQL primary, Redis fallback), filterable by `min_score` |
| DELETE | `/cache` | Clear all reputation cache (Redis + SQL) |
| POST | `/test` | Test AbuseIPDB API key with 8.8.8.8 |
| GET | `/api-usage` | Live AbuseIPDB check API usage (consumes 1 check) |
| POST | `/check-block` | Trigger subnet CIDR analysis |
| GET | `/check-block/results` | List cached subnet analysis results |
| GET | `/check-block/api-usage` | Check-block pool rate limit (separate from check pool) |
| DELETE | `/check-block/cache` | Clear subnet analysis cache |
| GET | `/check-block/{network:path}` | Get cached detail for specific subnet |
| GET | `/blacklist/api-usage` | Blacklist pool rate limit |
| GET | `/blacklist` | List blacklisted IPs (SQL primary, Redis fallback) |
| POST | `/blacklist/fetch` | Trigger manual blacklist download |
| GET | `/blacklist/config` | Get blacklist settings (auto_block, min_score, limit) |
| PUT | `/blacklist/config` | Update blacklist settings |

**Important:** The `{network:path}` catch-all endpoint MUST be defined last in the router to avoid shadowing static paths.

### 3. IP Management API

**Location:** `backend/app/api/v1/ip_management.py`
**Route prefix:** `/api/v1/ip-management`

**Purpose:** CRUD for trusted and blocked IPs. Bridges DB persistence with Redis-based threat blocking.

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/stats` | Counts: trusted, blocked (DB + Redis combined) |
| GET | `/trusted` | List trusted IPs |
| POST | `/trusted` | Add trusted IP + sync to threat_analyzer |
| DELETE | `/trusted/{id}` | Remove trusted IP |
| GET | `/blocked` | List blocked IPs (DB + Redis merged, expired cleanup) |
| POST | `/blocked` | Manual IP block (DB + Redis) |
| PUT | `/blocked/duration` | Update block duration (DB + Redis) |
| POST | `/unblock` | Remove IP block (DB + Redis) |
| PUT | `/blocked/bulk-unblock` | Bulk unblock |
| PUT | `/blocked/bulk-duration` | Bulk duration update |

### 4. Threat Analyzer

**Location:** `backend/app/workers/threat_analyzer.py`

**Purpose:** DNS-level threat detection (flood, DGA, scan patterns). Provides IP blocking primitives used by all modules.

**Key exports used by IP reputation system:**
- `auto_block_ip(ip, reason)` - adds IP to `dns:threat:blocked` Redis SET + nftables
- `manual_block_ip(ip, reason, ttl_seconds)` - manual blocking with optional TTL
- `manual_unblock_ip(ip)` - remove block
- `update_block_ttl(ip, ttl_seconds)` - update existing block duration
- `get_blocked_ips()` - list all Redis-blocked IPs
- `is_ip_blocked(ip)` - check if IP is blocked (used by DNS proxy)
- `is_trusted_ip(ip)` - check trusted IP list
- `TRUSTED_IPS` - in-memory set, loaded from file + DB

### 5. Domain Reputation Service

**Location:** `backend/app/services/domain_reputation.py`

**Purpose:** Heuristic domain risk scoring (NOT IP-based). Used by DNS proxy and threat analyzer.

**Scoring factors:**
- Shannon entropy (DGA detection): >= 4.0 → +30 points
- Domain length: >= 30 chars → +10 points
- Digit ratio: > 40% → +15 points
- Vowel ratio: < 10% → +10 points
- High-risk TLDs (.xyz, .top, .tk, etc.): +20 points
- Deep subdomains (5+ levels): +10 points
- Safe domain whitelist: immediate score 0

**Redis cache:** `dns:reputation:{domain}` HASH, 1h TTL

### 6. DDoS Service

**Location:** `backend/app/services/ddos_service.py`

**Purpose:** nftables-based DDoS protection (SYN/UDP/ICMP flood, connection limits).

**nftables integration:**
- Table: `inet tonbilai`
- Attacker sets: `ddos_syn_attackers`, `ddos_udp_attackers`, `ddos_icmp_attackers`, `ddos_invalid_attackers`, `ddos_conn_attackers`
- Per-IP rate limiting via nftables `meter`
- Attacker set timeout: 30 minutes, size: 4096

### 7. nftables HAL (Hardware Abstraction Layer)

**Location:** `backend/app/hal/linux_nftables.py`

**IP/Subnet blocking functions:**
- `add_blocked_subnet(subnet, timeout_seconds)` - adds nftables rules for subnet CIDR blocking (forward + input chains)
- `remove_blocked_subnet(subnet)` - removes subnet rules by comment pattern
- `sync_blocked_ips(ip_timeout_pairs)` - bulk sync blocked IPs to nftables `blocked_ips` set
- `ensure_tonbilai_table()` - creates `inet tonbilai` table with `blocked_ips` set (type `ipv4_addr`, flags `timeout`)

**nftables structure:**
```
table inet tonbilai {
    set blocked_macs { type ether_addr; }
    set blocked_ips  { type ipv4_addr; flags timeout; }
    chain input  { ... ip saddr @blocked_ips counter drop }
    chain forward { ... }
}
```

**Subnet rules use comment-based tracking:** `blocked_subnet_{cidr}_{direction}` for later removal by handle.

## Data Flow

### IP Reputation Check Flow

```
flow_tracker.py (conntrack, 20s)
    → Redis: flow:active_ids SET, flow:live:{id} HASH
        ↓
ip_reputation.py worker (300s cycle)
    → _get_active_external_ips() reads flow Redis data
    → filter: is_public_ip(), not in reputation:ip:{ip} cache
    → _process_ip():
        ├── AbuseIPDB API → abuse_score, total_reports, country
        ├── ip-api.com → country, city, isp, org, asn
        ├── Redis HASH: reputation:ip:{ip} (24h TTL)
        ├── SQL UPSERT: ip_reputation_checks table
        ├── score >= 80 → auto_block_ip() + subnet /24 check
        ├── score >= 50 → AiInsight WARNING
        └── country in blocked_countries → auto_block_ip()
```

### IP Blocking Flow (Multi-layer)

```
Trigger sources:
  ├── ip_reputation worker (score >= 80)
  ├── threat_analyzer (flood/DGA/scan detection)
  ├── blacklist fetch (bulk auto-block)
  ├── subnet check-block (auto threshold)
  └── manual UI action (IP Management page)
      ↓
threat_analyzer.auto_block_ip(ip, reason)
  ├── Redis SET: dns:threat:blocked
  ├── Redis STRING: dns:threat:block_expire:{ip} (reason, TTL)
  ├── Redis STRING: dns:threat:block_time:{ip} (timestamp, TTL)
  └── Redis HINCRBY: dns:threat:stats.total_auto_blocks
      ↓
DNS Proxy (dns_proxy.py)
  └── is_ip_blocked(client_ip) → drops queries from blocked IPs
      ↓
nftables sync (periodic)
  └── sync_blocked_ips() → blocked_ips set in inet tonbilai table
```

### Blacklist Fetch Flow

```
Trigger: auto (24h interval) or manual POST /blacklist/fetch
    ↓
fetch_abuseipdb_blacklist()
    ├── AbuseIPDB /api/v2/blacklist (confidenceMinimum, limit params)
    ├── Redis pipeline: blacklist_ips SET + blacklist_data:{ip} HASH
    ├── SQL batch INSERT: ip_blacklist_entries table
    ├── Auto-block (top 500): dns:threat:blocked SET
    └── AiInsight summary notification
```

### Subnet Analysis Flow

```
Trigger: manual POST /check-block or auto (critical IP detected)
    ↓
check_abuseipdb_block(subnet)
    ├── AbuseIPDB /api/v2/check-block (network, maxAgeInDays)
    ├── Count malicious IPs (score >= 50)
    ├── If malicious >= 3: add_blocked_subnet() via nftables
    ├── Cache: reputation:check_block:{subnet} STRING (24h)
    ├── Results index: reputation:check_block_results ZSET
    └── AiInsight + Telegram notification
```

## Database Models

### `ip_reputation_checks` table
**Model:** `backend/app/models/ip_reputation_check.py` → `IpReputationCheck`
**Purpose:** Persistent store for per-IP reputation checks (UPSERT on ip_address)

| Column | Type | Purpose |
|--------|------|---------|
| ip_address | VARCHAR(45), UNIQUE | IP address (IPv4/IPv6) |
| abuse_score | INT | AbuseIPDB confidence score (0-100) |
| total_reports | INT | Number of abuse reports |
| country | VARCHAR(100) | Country name |
| country_code | VARCHAR(10) | ISO country code |
| city | VARCHAR(100) | City |
| isp | VARCHAR(200) | ISP name |
| org | VARCHAR(200) | Organization |
| checked_at | DATETIME | Last check timestamp |

**Indexes:** `idx_irc_score` (abuse_score), `idx_irc_checked_at` (checked_at)

### `ip_blacklist_entries` table
**Model:** `backend/app/models/ip_blacklist_entry.py` → `IpBlacklistEntry`
**Purpose:** Persistent store for AbuseIPDB blacklist downloads (full replace on each fetch)

| Column | Type | Purpose |
|--------|------|---------|
| ip_address | VARCHAR(45), UNIQUE | Blacklisted IP |
| abuse_score | INT | Confidence score |
| country | VARCHAR(10) | Country code |
| last_reported_at | VARCHAR(50) | ISO timestamp from AbuseIPDB |
| fetched_at | DATETIME | When this batch was fetched |

### `blocked_ips` table
**Model:** `backend/app/models/blocked_ip.py` → `BlockedIp`
**Purpose:** Persistent manual/auto IP blocks with optional expiration

| Column | Type | Purpose |
|--------|------|---------|
| ip_address | VARCHAR(45), UNIQUE | Blocked IP |
| reason | VARCHAR(500) | Block reason |
| blocked_at | DATETIME | When blocked |
| expires_at | DATETIME, NULL | NULL = permanent |
| is_manual | BOOLEAN | True=manual, False=auto |
| source | VARCHAR(100) | "manual", "threat_analyzer", "api" |

### `trusted_ips` table
**Model:** `backend/app/models/trusted_ip.py` → `TrustedIp`
**Purpose:** IPs exempt from auto-blocking

| Column | Type | Purpose |
|--------|------|---------|
| ip_address | VARCHAR(45), UNIQUE | Trusted IP |
| description | VARCHAR(500) | Why trusted |
| created_at | DATETIME | When added |

## Redis Key Structure

### IP Reputation Cache
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `reputation:ip:{ip}` | HASH | 24h | Per-IP cache: abuse_score, total_reports, country, city, isp, org, checked_at |
| `reputation:enabled` | STRING | none | "1"/"0" - worker enable flag |
| `reputation:abuseipdb_key` | STRING | none | AbuseIPDB API key |
| `reputation:blocked_countries` | STRING (JSON) | none | ["CN", "RU", ...] blocked country codes |
| `reputation:daily_checks` | STRING (int) | 24h | Local daily AbuseIPDB check counter |

### AbuseIPDB Rate Limit Tracking (3 separate pools)
| Key Pattern | Type | TTL | Pool |
|-------------|------|-----|------|
| `reputation:abuseipdb_remaining` | STRING | 24h | check (per-IP) |
| `reputation:abuseipdb_limit` | STRING | 24h | check (per-IP) |
| `reputation:check_block_api_remaining` | STRING | 24h | check-block (subnet) |
| `reputation:check_block_api_limit` | STRING | 24h | check-block (subnet) |
| `reputation:blacklist_api_remaining` | STRING | 24h | blacklist (bulk) |
| `reputation:blacklist_api_limit` | STRING | 24h | blacklist (bulk) |

### Blacklist Data
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `reputation:blacklist_ips` | SET | 48h | All blacklisted IP addresses |
| `reputation:blacklist_data:{ip}` | HASH | 48h | Per-IP blacklist detail: abuse_score, country, last_reported_at |
| `reputation:blacklist_last_fetch` | STRING | none | UTC ISO timestamp of last fetch |
| `reputation:blacklist_count` | STRING | none | Total IPs in last fetch |
| `reputation:blacklist_daily_fetches` | STRING | 24h | Daily fetch counter |
| `reputation:blacklist_auto_block` | STRING | none | "1"/"0" auto-block toggle |
| `reputation:blacklist_min_score` | STRING | none | Minimum score for auto-block (default 100) |
| `reputation:blacklist_limit` | STRING | none | Max IPs to download (default 10000) |

### Subnet Analysis (Check-Block)
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `reputation:check_block:{subnet}` | STRING (JSON) | 24h | Full analysis result for a subnet |
| `reputation:check_block_results` | ZSET | 24h | Index of analyzed subnets, score = malicious_count |

### Threat Blocking (shared with threat_analyzer)
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `dns:threat:blocked` | SET | none | All currently blocked IPs |
| `dns:threat:block_expire:{ip}` | STRING | block_duration | Block reason text |
| `dns:threat:block_time:{ip}` | STRING | block_duration | Block start timestamp |
| `dns:threat:stats` | HASH | none | total_auto_blocks counter |

### Domain Reputation
| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `dns:reputation:{domain}` | HASH | 1h | Domain risk score, risk_level, factors |

## Frontend Architecture

### Firewall Page with IP Reputation Tab

**Location:** `frontend/src/pages/FirewallPage.tsx`
**Tab component:** `frontend/src/components/firewall/IpReputationTab.tsx`

The FirewallPage uses a tab system with the IP Reputation tab being one of 4 tabs:
- Kurallar (firewall rules)
- DDoS Koruma
- IP Itibar (IpReputationTab)
- Guvenlik Ayarlari

### IpReputationTab Component

**Location:** `frontend/src/components/firewall/IpReputationTab.tsx` (~1600 lines)

**Sections:**
1. **API Usage Top Bar** - Unified bar showing 3 AbuseIPDB API pools (check, check-block, blacklist) with remaining/limit
2. **Configuration** - AbuseIPDB API key input, enable/disable toggle, API test button
3. **Summary Stats** - Total checked, critical/warning counts, daily usage
4. **Country Blocking** - Add/remove country codes with tag interface
5. **Checked IPs Table** - Sortable table with score color-coding, search filter
6. **Blacklist Section** - Config (auto_block, min_score, limit), fetch trigger, IP list
7. **Subnet Analysis (Check-Block)** - CIDR input, analyze button, results table with per-IP detail expansion

**State management:** Local React state with `useEffect` polling. No global state management.

### IP Management Page

**Location:** `frontend/src/pages/IpManagementPage.tsx` (~900 lines)

**Tabs:**
- Trusted IPs - CRUD with description
- Blocked IPs - CRUD with duration selection, bulk operations, source indicators

### API Service Layer

**IP Reputation:** `frontend/src/services/ipReputationApi.ts` - 16 API functions
**IP Management:** `frontend/src/services/ipManagementApi.ts` - 8 API functions

Both use the shared Axios instance from `frontend/src/services/api.ts`.

## External API Integrations

### AbuseIPDB (Primary)

**API Version:** v2
**Base URL:** `https://api.abuseipdb.com/api/v2/`
**Auth:** API key in `Key` header
**Rate Limits (free plan):**
- `/check`: 1000/day
- `/check-block`: separate pool (plan-dependent)
- `/blacklist`: 5/day (tracked separately)

**Endpoints used:**
| Endpoint | Purpose | Rate Pool |
|----------|---------|-----------|
| `/check` | Single IP reputation check | check |
| `/check-block` | Subnet CIDR analysis | check-block |
| `/blacklist` | Bulk download of worst IPs | blacklist |

**Rate limit tracking:** X-RateLimit-Remaining and X-RateLimit-Limit headers cached in Redis per pool.

### ip-api.com (GeoIP)

**URL:** `http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp,org,as,query`
**Rate limit:** 40 requests/minute (enforced with 1.5s sleep between requests)
**Auth:** None (free tier)

## Cross-Cutting Integration Points

### DNS Proxy Integration
**File:** `backend/app/workers/dns_proxy.py`
- Imports `is_ip_blocked`, `report_external_query`, `report_local_query`, `is_trusted_ip` from `threat_analyzer`
- Every DNS query checks `is_ip_blocked(client_ip)` before processing
- Blocked IPs get silently dropped (no DNS response)

### Flow Tracker Integration
**File:** `backend/app/workers/flow_tracker.py`
- Provides active connection data in Redis (`flow:active_ids`, `flow:live:{id}`)
- IP reputation worker reads flow data to discover which external IPs to check

### AiInsight + Telegram Integration
- Critical/warning scores write to `ai_insights` table via `_write_ai_insight()`
- Telegram notifications sent via `notify_ai_insight()` from `backend/app/services/telegram_service.py`
- Cooldown: 30 minutes per unique event

### nftables Integration
- Single IPs blocked via `blocked_ips` nftables SET (type ipv4_addr, flags timeout)
- Subnets blocked via individual nftables rules with comment-based tracking
- DDoS attacker IPs tracked in separate nftables sets (ddos_syn_attackers, etc.)

## Error Handling Strategy

**Dual-source fallback pattern:** SQL is the primary data store; Redis is the fallback.
- GET endpoints try SQL first, fall back to Redis SCAN on SQL error
- Worker writes to both Redis (fast cache) and SQL (persistent) independently
- Each write has independent try/except — one failure doesn't block the other

**API error handling:** HTTP status codes from AbuseIPDB (401, 429, 402) are mapped to user-friendly Turkish messages.

## Where to Add New Code

**New reputation data source:**
- Add query function in `backend/app/workers/ip_reputation.py` (alongside `check_abuseipdb`, `check_geoip`)
- Integrate into `_process_ip()` result merging
- Add Redis cache fields to `reputation:ip:{ip}` HASH

**New API endpoint for IP reputation:**
- Add to `backend/app/api/v1/ip_reputation.py`
- Static path endpoints MUST be defined before the `{network:path}` catch-all

**New frontend section in IP Reputation tab:**
- Add section in `frontend/src/components/firewall/IpReputationTab.tsx`
- Add API function in `frontend/src/services/ipReputationApi.ts`

**New blocking mechanism:**
- Use `auto_block_ip(ip, reason)` from `backend/app/workers/threat_analyzer.py`
- For subnets, use `add_blocked_subnet(subnet, timeout)` from `backend/app/hal/linux_nftables.py`

---

*Architecture analysis: 2026-03-12*
