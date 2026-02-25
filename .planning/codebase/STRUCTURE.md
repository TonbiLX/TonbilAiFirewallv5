# Codebase Structure

**Analysis Date:** 2026-02-25

## Directory Layout

```
project-root/
├── frontend/                      # React 18 + TypeScript + Vite (SPA)
│   ├── src/
│   │   ├── main.tsx              # Entry point (React mount)
│   │   ├── App.tsx               # Root routes, AuthGuard
│   │   ├── index.css             # Global styles + grid overrides
│   │   ├── ddos-map-animations.css # DDoS map animations
│   │   ├── vite-env.d.ts         # Vite type definitions
│   │   │
│   │   ├── types/                # TypeScript interfaces
│   │   │   ├── index.ts          # Core models (Profile, Device, TrafficLog, etc.)
│   │   │   ├── websocket.ts      # WS message types
│   │   │   └── dashboard-grid.ts # WidgetDefinition, DashboardPreferences
│   │   │
│   │   ├── config/               # App configuration
│   │   │   ├── widgetRegistry.tsx     # Dashboard widgets (11 widgets + default layouts)
│   │   │   └── systemMonitorWidgetRegistry.tsx # System monitor widgets
│   │   │
│   │   ├── hooks/                # Custom React hooks (state management)
│   │   │   ├── useWebSocket.ts   # Real-time WS connection + data state
│   │   │   ├── useDashboard.ts   # Dashboard summary data (API call)
│   │   │   ├── useDashboardLayout.ts # Grid layout state + localStorage persist
│   │   │   ├── useSystemMonitorLayout.ts # System monitor layout state
│   │   │   ├── useDhcp.ts        # DHCP data fetching
│   │   │   ├── useDnsBlocking.ts # DNS blocking data fetching
│   │   │   └── ...               # Other domain hooks
│   │   │
│   │   ├── services/             # API client layer
│   │   │   ├── api.ts            # Axios instance + interceptors (JWT auth)
│   │   │   ├── tokenStore.ts     # JWT token management (localStorage)
│   │   │   ├── authApi.ts        # Auth endpoints
│   │   │   ├── dashboardApi.ts   # Dashboard summary
│   │   │   ├── deviceApi.ts      # Device CRUD
│   │   │   ├── dnsApi.ts         # DNS queries + blocking
│   │   │   ├── contentCategoryApi.ts # Content category CRUD + blocklist linking
│   │   │   ├── dhcpApi.ts        # DHCP pool + leases
│   │   │   ├── firewallApi.ts    # Firewall rules
│   │   │   ├── vpnApi.ts         # WireGuard VPN
│   │   │   ├── trafficApi.ts     # Live flows + history
│   │   │   ├── chatApi.ts        # AI chat
│   │   │   ├── profileApi.ts     # Profiles + bandwidth
│   │   │   ├── ddosApi.ts        # DDoS protection
│   │   │   ├── telegramApi.ts    # Telegram notifications
│   │   │   ├── systemMonitorApi.ts # System metrics
│   │   │   └── ... (15 more API services)
│   │   │
│   │   ├── components/           # Reusable UI components
│   │   │   ├── auth/
│   │   │   │   └── AuthGuard.tsx # Protected route wrapper
│   │   │   │
│   │   │   ├── common/           # Shared building blocks
│   │   │   │   ├── GlassCard.tsx        # Glassmorphism container (cyan border)
│   │   │   │   ├── StatCard.tsx        # Stat display card
│   │   │   │   ├── NeonBadge.tsx       # Colored status badge
│   │   │   │   └── LoadingSpinner.tsx  # Loading animation
│   │   │   │
│   │   │   ├── layout/           # Page structure
│   │   │   │   ├── MainLayout.tsx      # Sidebar + content area
│   │   │   │   ├── Sidebar.tsx        # Navigation menu (drawer on mobile)
│   │   │   │   └── TopBar.tsx         # Top navigation (breadcrumbs, actions)
│   │   │   │
│   │   │   ├── dashboard/        # Dashboard grid system
│   │   │   │   ├── DashboardGrid.tsx   # react-grid-layout Responsive container
│   │   │   │   ├── WidgetWrapper.tsx   # Widget frame (drag handle + card)
│   │   │   │   └── WidgetToggleMenu.tsx # Hide/show dropdown
│   │   │   │
│   │   │   ├── charts/           # Data visualization
│   │   │   │   ├── BandwidthGauge.tsx
│   │   │   │   ├── CategoryPie.tsx
│   │   │   │   └── TrafficChart.tsx (Recharts)
│   │   │   │
│   │   │   ├── ddos/             # DDoS components
│   │   │   │   ├── DdosWorldMap.tsx    # SVG world map (react-simple-maps)
│   │   │   │   └── AttackFeed.tsx      # Attack feed table
│   │   │   │
│   │   │   ├── devices/          # Device management
│   │   │   │   ├── DeviceCard.tsx
│   │   │   │   ├── DeviceList.tsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── dns/              # DNS management
│   │   │   │   ├── BlocklistCard.tsx
│   │   │   │   ├── DnsQueryTable.tsx
│   │   │   │   ├── DnsStatsChart.tsx
│   │   │   │   ├── DomainSearch.tsx
│   │   │   │   └── DeviceCustomRulesTab.tsx
│   │   │   │
│   │   │   ├── dhcp/             # DHCP components
│   │   │   ├── firewall/         # Firewall components
│   │   │   ├── profiles/         # Profile management
│   │   │   ├── chat/             # AI chat renderer
│   │   │   └── ui/               # Logo, brand components
│   │   │
│   │   └── pages/                # Full-page components (Route-bound)
│   │       ├── LoginPage.tsx     # Auth form (public route)
│   │       ├── DashboardPage.tsx # Main dashboard (react-grid-layout)
│   │       ├── SystemMonitorPage.tsx # System metrics dashboard
│   │       ├── DevicesPage.tsx   # Device list + management
│   │       ├── DeviceDetailPage.tsx # Single device detail + per-flow tracking
│   │       ├── DeviceServicesPage.tsx # Device services/applications
│   │       ├── ProfilesPage.tsx  # Profile CRUD + categories
│   │       ├── ContentCategoriesPage.tsx # Category CRUD + blocklist link
│   │       ├── DnsBlockingPage.tsx # DNS queries + global rules
│   │       ├── DhcpPage.tsx      # DHCP pool + leases
│   │       ├── FirewallPage.tsx  # Firewall rules + DDoS tab
│   │       ├── VpnPage.tsx       # WireGuard peer management
│   │       ├── VpnClientPage.tsx # External VPN client config
│   │       ├── TlsPage.tsx       # TLS certificate management
│   │       ├── TrafficPage.tsx   # Live flows (3 tabs: live, large, history)
│   │       ├── DdosMapPage.tsx   # World map attack visualization
│   │       ├── ChatPage.tsx      # AI assistant
│   │       ├── TelegramPage.tsx  # Bot configuration
│   │       ├── InsightsPage.tsx  # AI insights list
│   │       ├── SystemLogsPage.tsx # System event logs
│   │       ├── SystemTimePage.tsx # Time/NTP config
│   │       ├── IpManagementPage.tsx # Trusted/blocked IPs
│   │       ├── SettingsPage.tsx  # User preferences
│   │       ├── AiSettingsPage.tsx # AI model config
│   │       └── SystemManagementPage.tsx # Reboot, update, etc.
│   │
│   ├── public/                   # Static assets
│   ├── dist/                     # Build output (Vite)
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                      # Python FastAPI + async
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan (startup/shutdown)
│   │   ├── config.py            # Settings (env vars, database URL, etc.)
│   │   │
│   │   ├── api/v1/              # REST endpoints + WebSocket
│   │   │   ├── router.py        # Main APIRouter (includes all sub-routers)
│   │   │   ├── auth.py          # Login, token refresh
│   │   │   ├── dashboard.py     # Dashboard summary (GET)
│   │   │   ├── devices.py       # Device CRUD + block/unblock
│   │   │   ├── dns.py           # DNS queries, global blocking rules
│   │   │   ├── dhcp.py          # DHCP pool + lease management
│   │   │   ├── firewall.py      # Firewall rules CRUD
│   │   │   ├── vpn.py           # WireGuard peer management
│   │   │   ├── vpn_client.py    # External VPN config
│   │   │   ├── tls.py           # TLS certificates
│   │   │   ├── content_categories.py # Category CRUD + blocklist linking + rebuild
│   │   │   ├── profiles.py      # Profile CRUD + domain rebuild + bandwidth apply
│   │   │   ├── traffic.py       # Per-flow tracking (live, history, stats)
│   │   │   ├── chat.py          # LLM-based chat endpoint
│   │   │   ├── insights.py      # AI insights CRUD
│   │   │   ├── services.py      # Service blocking (YouTube, Netflix, etc.)
│   │   │   ├── ddos.py          # DDoS config + status
│   │   │   ├── ws.py            # WebSocket: real-time data broadcast
│   │   │   ├── system_logs.py   # Event log queries + export
│   │   │   ├── system_time.py   # NTP + time zone config
│   │   │   ├── system_monitor.py # CPU/memory/disk metrics
│   │   │   ├── telegram.py      # Telegram bot config
│   │   │   ├── ip_management.py # Trusted/blocked IP CRUD
│   │   │   ├── device_custom_rules.py # Per-device DNS rules
│   │   │   ├── ai_settings.py   # AI model selection/config
│   │   │   └── system_management.py # Reboot, service restart
│   │   │
│   │   ├── models/              # SQLAlchemy ORM (MariaDB tables)
│   │   │   ├── __init__.py      # Export all models
│   │   │   ├── user.py          # Admin user (username, hashed_password)
│   │   │   ├── device.py        # Device (MAC, IP, hostname, profile_id, risk_score)
│   │   │   ├── profile.py       # Profile (content_filters JSON, bandwidth_limit)
│   │   │   ├── content_category.py # Content filter categories
│   │   │   ├── category_blocklist.py # M2M: Category ↔ Blocklist
│   │   │   ├── blocklist.py     # Blocklist (name, URL, format)
│   │   │   ├── dns_query_log.py # DNS queries (timestamp, domain, device_id, action)
│   │   │   ├── dns_rule.py      # Global DNS rules (whitelist/blacklist)
│   │   │   ├── dhcp_pool.py     # DHCP pool (subnet, gateway)
│   │   │   ├── dhcp_lease.py    # DHCP leases (MAC, IP, expiry)
│   │   │   ├── traffic_log.py   # Legacy traffic (deprecated, use connection_flows)
│   │   │   ├── connection_flow.py # Per-flow connections (src/dst IP/port, state, bytes)
│   │   │   ├── firewall_rule.py # Firewall rules (src/dst, action)
│   │   │   ├── vpn_peer.py      # WireGuard peers
│   │   │   ├── vpn_client.py    # External VPN config
│   │   │   ├── tls_config.py    # TLS certificates
│   │   │   ├── chat_message.py  # AI chat history
│   │   │   ├── ai_insight.py    # AI insights (threats, anomalies)
│   │   │   ├── blocked_service.py # Service definitions (YouTube, etc.)
│   │   │   ├── device_blocked_service.py # Per-device service blocks
│   │   │   ├── device_custom_rule.py # Per-device DNS overrides
│   │   │   ├── device_traffic_snapshot.py # Device bandwidth snapshots
│   │   │   ├── telegram_config.py # Telegram bot token
│   │   │   ├── ddos_config.py   # DDoS thresholds
│   │   │   ├── ai_config.py     # LLM model selection
│   │   │   ├── blocked_ip.py    # Blocked external IPs
│   │   │   ├── trusted_ip.py    # Trusted external IPs
│   │   │   ├── device_connection_log.py # Device connection events (deprecated)
│   │   │   ├── log_signature.py # Log integrity hashes
│   │   │   └── ...              # 30 models total
│   │   │
│   │   ├── schemas/             # Pydantic request/response models
│   │   │   ├── (auto-generated per endpoint)
│   │   │   └── Used for validation + OpenAPI docs
│   │   │
│   │   ├── services/            # Business logic layer
│   │   │   ├── ai_engine.py     # AI threat analysis orchestration
│   │   │   ├── llm_service.py   # LLM (Claude, GPT) integration
│   │   │   ├── dns_fingerprint.py # OS/device detection from DNS
│   │   │   ├── system_monitor_service.py # CPU/memory/disk metrics
│   │   │   └── ...              # Other services
│   │   │
│   │   ├── workers/             # Long-running background tasks
│   │   │   ├── dns_proxy.py      # Port 53 + 853 (DoT) DNS interceptor
│   │   │   ├── blocklist_worker.py # Download blocklists, rebuild Redis caches
│   │   │   ├── device_discovery.py # ARP scan for LAN devices + DHCP integration
│   │   │   ├── dhcp_worker.py   # ISC DHCP server integration (pool + leases)
│   │   │   ├── traffic_monitor.py # Tcpdump + domain aggregation (legacy)
│   │   │   ├── bandwidth_monitor.py # Per-device bandwidth tracking
│   │   │   ├── flow_tracker.py  # Conntrack per-flow tracking (20s interval)
│   │   │   ├── threat_analyzer.py # IP reputation, anomaly detection
│   │   │   ├── mac_resolver_worker.py # MAC vendor lookup + OUI database
│   │   │   ├── telegram_worker.py # Telegram alert dispatch
│   │   │   ├── llm_log_analyzer.py # LLM-based log analysis
│   │   │   ├── log_signer.py    # Tamper-proof log signing
│   │   │   ├── traffic_simulator.py # Test traffic generation (dev only)
│   │   │   ├── dhcp_simulator.py # Test DHCP simulation (dev only)
│   │   │   └── sync_worker.py   # Data sync utils
│   │   │
│   │   ├── hal/                 # Hardware Abstraction Layer
│   │   │   ├── base_driver.py   # Abstract base class
│   │   │   ├── driver_factory.py # Factory (select Linux/mock driver)
│   │   │   ├── linux_driver.py  # Network (ip link, route, DNS, MAC)
│   │   │   ├── linux_nftables.py # Modern firewall (nftables tables + rules)
│   │   │   ├── linux_tc.py      # Traffic control (QoS, bandwidth limiting)
│   │   │   ├── linux_dhcp_driver.py # ISC DHCP server management
│   │   │   └── mock_driver.py   # Mock for testing
│   │   │
│   │   ├── db/                  # Database abstraction
│   │   │   ├── session.py       # AsyncSession factory (SQLAlchemy + MariaDB)
│   │   │   ├── base.py          # Declarative base for ORM
│   │   │   ├── redis_client.py  # Redis async client instance
│   │   │   └── __init__.py
│   │   │
│   │   ├── seed/                # Database seeding
│   │   │   └── (scripts for initial data)
│   │   │
│   │   └── __init__.py
│   │
│   ├── tests/                   # Pytest test suite (basic)
│   │   └── (test files)
│   │
│   ├── requirements.txt         # Python dependencies
│   └── __init__.py
│
├── config/                      # Deployment configs
│   ├── (nginx, systemd, etc.)
│
├── deploy/                      # Deployment scripts
│   ├── (deployment automation)
│
├── docs/                        # Documentation + screenshots
│   └── screenshots/
│
├── .planning/codebase/          # GSD analysis documents
│   ├── ARCHITECTURE.md          # This file's sibling
│   └── STRUCTURE.md             # Directory/file guide
│
├── CLAUDE.md                    # Project instructions (keep in sync!)
├── README.md                    # Project overview
├── .env.example                 # Environment template
├── setup.sh                     # Initial setup script
└── deploy_dist.py              # Deploy frontend build to Pi
```

## Directory Purposes

**frontend/src/**
- Purpose: React application source
- Contains: Components, pages, hooks, services, styles, types
- Key files: `main.tsx` (entry), `App.tsx` (router), `index.css` (global styles)

**frontend/src/services/**
- Purpose: Centralized API client layer
- Contains: Axios instance + per-domain API modules
- Pattern: Each service exports async functions (e.g., `getDevices()`, `updateProfile()`)

**backend/app/api/v1/**
- Purpose: FastAPI route handlers
- Contains: 23 routers (one per domain: auth, devices, DNS, etc.)
- Pattern: Each module defines APIRouter, endpoints decorated with @router.get/post/put/delete

**backend/app/models/**
- Purpose: Database schema definitions
- Contains: 30 SQLAlchemy models with relationships
- Pattern: Each file = one table (one model per file)

**backend/app/workers/**
- Purpose: Long-running background processes
- Contains: 12 async workers (DNS, traffic, discovery, threat analysis, etc.)
- Pattern: `async def start_{worker_name}()` → infinite loop with sleeps

**backend/app/hal/**
- Purpose: System-level abstraction (network, firewall, DHCP)
- Contains: Linux driver implementations + mock for testing
- Pattern: Methods wrap shell commands (nftables, ip, tc, dhcp)

## Key File Locations

**Entry Points:**
- `frontend/src/main.tsx`: Vite app mount point
- `frontend/src/App.tsx`: React Router root
- `backend/app/main.py`: FastAPI app creation + lifespan

**Configuration:**
- `frontend/vite.config.ts`: Build config + API proxy
- `backend/app/config.py`: Environment variables + settings
- `frontend/src/config/widgetRegistry.tsx`: Widget definitions + layout defaults

**Core Logic:**
- `frontend/src/pages/`: User-facing routes (25 pages)
- `backend/app/api/v1/`: HTTP endpoints (23 routers)
- `backend/app/workers/`: Async background tasks (12 workers)

**Testing:**
- `backend/tests/`: Pytest test suite
- Frontend uses no explicit test framework (component testing optional)

## Naming Conventions

**Files:**
- **React components:** PascalCase (e.g., `DashboardPage.tsx`, `GlassCard.tsx`)
- **Services:** camelCase + "Api" suffix (e.g., `dashboardApi.ts`, `deviceApi.ts`)
- **Hooks:** camelCase + "use" prefix (e.g., `useDashboard.ts`, `useWebSocket.ts`)
- **Models:** PascalCase + singular (e.g., `device.py`, `profile.py`)
- **API routes:** snake_case paths (e.g., `/devices/:id`, `/content-categories`)

**Directories:**
- **Components:** Grouped by domain/feature (e.g., `components/dns/`, `components/devices/`)
- **Services:** One file per API domain (e.g., `dnsApi.ts`, `deviceApi.ts`)
- **Routes:** One file per endpoint domain (e.g., `dns.py`, `devices.py`)

**TypeScript/Python:**
- **Interfaces:** PascalCase (e.g., `interface Device {}`)
- **Functions:** camelCase (e.g., `getDevices()`, `updateProfile()`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `DEFAULT_LAYOUTS`, `UPSTREAM_DNS`)
- **Enums:** PascalCase (e.g., `enum ProfileType {}`)

## Where to Add New Code

**New Feature (e.g., "add email notifications"):**
- **Frontend:**
  - Page: `frontend/src/pages/EmailSettingsPage.tsx`
  - Services: `frontend/src/services/emailApi.ts`
  - Components: `frontend/src/components/email/EmailConfigForm.tsx`
  - Routes: Add route to `App.tsx`
  - Menu: Add sidebar item in `components/layout/Sidebar.tsx`
- **Backend:**
  - API: `backend/app/api/v1/email.py`
  - Models: `backend/app/models/email_config.py`
  - Worker: `backend/app/workers/email_notifier.py` (if async)
  - Service: `backend/app/services/email_service.py` (SMTP logic)
  - Register: Include router in `api/v1/router.py`

**New Component/Module (e.g., "add usage statistics"):**
- **Location:** `frontend/src/components/{domain}/StatsComponent.tsx`
- **Hook:** `frontend/src/hooks/useStats.ts` (if needs state/API)
- **Service:** `frontend/src/services/statsApi.ts` (if needs data)
- **Integration:** Import in page, render in JSX

**Utilities/Helpers:**
- **Frontend:** `frontend/src/services/` (general) or `frontend/src/hooks/` (stateful)
- **Backend:** `backend/app/services/` (business logic) or `backend/app/hal/` (system-level)

## Special Directories

**frontend/dist/**
- Purpose: Vite build output (production static files)
- Generated: Yes (by `npm run build`)
- Committed: No (in .gitignore)
- Usage: Deployed to `/opt/tonbilaios/frontend/dist` on Pi

**backend/.pytest_cache/**
- Purpose: Pytest cache
- Generated: Yes (by pytest)
- Committed: No (in .gitignore)
- Usage: Speed up test runs (safe to delete)

**frontend/node_modules/**
- Purpose: NPM dependencies
- Generated: Yes (by `npm install`)
- Committed: No (in .gitignore)
- Usage: Required for dev/build, installed via package-lock.json

**backend/.env**
- Purpose: Runtime environment variables (DATABASE_URL, LLM_KEY, etc.)
- Generated: No (created manually from .env.example)
- Committed: No (in .gitignore, security risk!)
- Usage: Loaded by FastAPI on startup

**docs/screenshots/**
- Purpose: UI screenshots for documentation
- Generated: Manual
- Committed: Yes
- Usage: README.md, documentation

**config/**
- Purpose: Systemd, Nginx, deployment configs
- Generated: No (manual)
- Committed: Yes
- Usage: Production deployment reference

## Redis Key Namespace Convention

| Prefix | Type | Example |
|--------|------|---------|
| `dns:` | Domain filtering | `dns:blocked_domains`, `dns:category_domains:{key}` |
| `flow:` | Traffic flows | `flow:live:{id}`, `flow:active_ids`, `flow:large` |
| `device:` | Device mapping | `device:ip_to_mac:{ip}` |
| `profile:` | Profile cache | `dns:profile_domains:{id}` |
| `session:` | User sessions | `session:{token}` (future) |

---

*Structure analysis: 2026-02-25*
