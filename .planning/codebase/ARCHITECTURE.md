# Architecture

**Analysis Date:** 2026-02-25

## Pattern Overview

**Overall:** Layered monolithic architecture with client-server separation. Backend uses event-driven workers for real-time processing, frontend uses component-based reactive UI with Redux-free state management.

**Key Characteristics:**
- **Frontend:** React 18 with React Router (SPA with layout composition)
- **Backend:** FastAPI with async/await, SQLAlchemy ORM, WebSocket for real-time updates
- **Data:** MariaDB (persistent), Redis (real-time caching), filesystem (blocklists, configs)
- **Processing:** Background workers (DNS proxy, device discovery, traffic monitoring, threat analysis)
- **Network Abstraction:** HAL (Hardware Abstraction Layer) for Linux system calls

## Layers

**Frontend Presentation (React):**
- Purpose: Interactive UI rendered in browser, layout management, user interactions
- Location: `frontend/src/`
- Contains: Pages, components, hooks, styles, type definitions
- Depends on: API services, custom hooks for state management
- Used by: End user browsers

**Frontend Services (API Client):**
- Purpose: HTTP/WebSocket communication with backend
- Location: `frontend/src/services/`
- Contains: Axios instance, per-domain API clients (auth, dashboard, devices, DNS, etc.), token management
- Depends on: Backend API endpoints
- Used by: Pages and custom hooks

**Frontend Component Layer:**
- Purpose: Reusable UI building blocks (GlassCard, NeonBadge, StatCard, charts)
- Location: `frontend/src/components/`
- Contains: Common components, layout scaffolding, domain-specific components (devices, DNS, firewall, etc.)
- Depends on: Lucide icons, Recharts, react-grid-layout
- Used by: Pages and other components

**Frontend State Management:**
- Purpose: Application state for dashboard layout, WebSocket data, user preferences
- Location: `frontend/src/hooks/` (custom hooks), `frontend/src/config/` (registries)
- Contains: useWebSocket, useDashboard, useDashboardLayout, useSystemMonitorLayout
- Depends on: Services, localStorage
- Used by: Pages and components

**Backend API Layer (FastAPI):**
- Purpose: HTTP endpoints for CRUD operations, WebSocket handler, real-time data streaming
- Location: `backend/app/api/v1/`
- Contains: 23 router modules (auth, devices, DNS, DHCP, firewall, VPN, traffic, chat, system)
- Depends on: Database session, workers, services
- Used by: Frontend, external tools

**Backend Service Layer:**
- Purpose: Business logic, orchestration, LLM integration, threat analysis
- Location: `backend/app/services/`
- Contains: AI engine, LLM service, DNS fingerprinting, system monitoring
- Depends on: Models, workers, database
- Used by: API layer

**Backend Worker Layer (Async Background Tasks):**
- Purpose: Long-running, event-driven processing for system operations
- Location: `backend/app/workers/`
- Contains: 12 workers (DNS proxy, device discovery, traffic monitor, bandwidth monitor, DHCP, blocklist, flow tracker, threat analyzer, MAC resolver, telegram, log signing, LLM log analyzer)
- Depends on: Database, Redis, HAL
- Used by: Main application (started at boot via lifespan)

**Backend Data Layer (SQLAlchemy ORM):**
- Purpose: Persistent storage abstraction
- Location: `backend/app/models/`
- Contains: 30 SQLAlchemy models (Device, Profile, DnsQueryLog, TrafficLog, FirewallRule, VpnPeer, etc.)
- Depends on: MariaDB via async SQLAlchemy engine
- Used by: API, services, workers

**Backend Cache Layer (Redis):**
- Purpose: Real-time data, session storage, set operations for DNS filtering
- Location: Accessed via `backend/app/db/redis_client.py`
- Contains: DNS domain sets, profile cache, device profile mapping, device IP mapping, flow tracker data
- Used by: DNS proxy, workers, API endpoints

**Hardware Abstraction Layer (HAL):**
- Purpose: System-level operations (network management, firewall rules, DHCP, traffic control)
- Location: `backend/app/hal/`
- Contains: Base driver, Linux driver (iptables, network), nftables (modern firewall), traffic control (TC), DHCP driver
- Depends on: Linux system calls via Paramiko/SSH or direct execution
- Used by: Workers, API layer (firewall rules, DHCP management)

## Data Flow

**User Login Flow:**
1. `LoginPage` → `POST /auth/login` (authApi.ts)
2. Backend validates credentials against MariaDB users table
3. Returns JWT token
4. Frontend stores token in localStorage/sessionStorage via `tokenStore.ts`
5. `AuthGuard` checks token presence, redirects if missing
6. Subsequent API calls include token in Authorization header (via axios interceptor)

**Real-Time Dashboard Data Flow:**
1. `DashboardPage` mounts → calls `useWebSocket()` hook
2. WebSocket connects to `ws://backend/api/v1/ws/live`
3. Backend `ws.py` handler broadcasts:
   - Bandwidth data (every 2s): upload/download BPS, per-device totals
   - DNS data: queries/min, blocked count, top domains
   - Device status: online/offline, IP changes
   - Traffic logs: per-flow connections
4. Frontend receives via `wsData` → renders widgets in `DashboardGrid`
5. Dashboard state persisted to localStorage (layout, visible widgets)

**DNS Filtering & Profiling Flow:**
1. Device makes DNS query → DNS proxy (`dns_proxy.py`) intercepts on port 53
2. Lookup sequence:
   a. Check whitelist (redis `dns:whitelist`)
   b. Check device is not blocked globally
   c. Check service-level blocks (independent of profile)
   d. Check profile-based filters:
      - Device has profile_id → fetch `redis:dns:profile_domains:{profile_id}` (UNION of category domains)
      - No profile → use global `redis:dns:blocked_domains`
   e. Check reputation (threat analyzer)
3. If blocked: return NXDOMAIN or sinkhole IP
4. If allowed: forward to upstream (Cloudflare, Google)
5. Response logged to `dns_query_logs` table

**Traffic Monitoring & Per-Flow Tracking:**
1. `flow_tracker.py` reads conntrack every 20s via `conntrack -L`
2. Parses inbound/outbound TCP/UDP flows
3. Matches flow to device via source IP → `dns:ip_to_device:{ip}` Redis mapping
4. Applies service detection (40+ port-based: SSH, MQTT, DNS; 80+ domain-based: WhatsApp, YouTube)
5. Stores live data: `redis:flow:live:{flow_id}` (hash, 60s TTL)
6. Syncs to MariaDB `connection_flows` table every 60s (7-day retention)
7. Frontend `TrafficPage` fetches via `/traffic/flows/live` (3s refresh), `/traffic/flows/history` (paginated)

**Profile & Content Category Management:**
1. Admin creates profile with `content_filters: ["adult", "gambling", ...]` in `ProfilesPage`
2. `POST /profiles` → backend stores in `profiles` table
3. Triggers rebuild: `rebuild_profile_domains()` reads all blocklists linked to categories
4. SUNIONSTORE result → `redis:dns:profile_domains:{profile_id}` (all domain union)
5. When device assigned to profile: store `redis:dns:device_profile:{device_id}` = profile_id
6. Update device bandwidth: apply profile's `bandwidth_limit_mbps` via HAL traffic control

**State Management:**
- Dashboard layout: `localStorage` + `useDashboardLayout` hook (react-grid-layout v2 state)
- WebSocket data: `useWebSocket` hook state (in-memory, no persistence needed for real-time)
- Dashboard summary: `useDashboard` hook (API call on mount + WebSocket updates)
- User preferences: localStorage (widget visibility, layout positions)
- Device IP mapping: Redis `dns:ip_to_device:{ip}` (updated by device discovery + DHCP workers)

## Key Abstractions

**Widget (react-grid-layout):**
- Purpose: Pluggable dashboard elements with drag/resize/hide capabilities
- Examples: `frontend/src/config/widgetRegistry.tsx`, `frontend/src/components/dashboard/WidgetWrapper.tsx`
- Pattern: Define in registry → render via `DashboardGrid` → manage state in `useDashboardLayout`

**API Services:**
- Purpose: Centralized HTTP/WebSocket communication
- Examples: `frontend/src/services/dashboardApi.ts`, `frontend/src/services/dnsApi.ts`, etc.
- Pattern: Export async functions that use Axios instance; intercepts handle auth

**Workers (Backend):**
- Purpose: Autonomous long-running tasks spawned at startup
- Examples: `flow_tracker.py`, `dns_proxy.py`, `device_discovery.py`
- Pattern: Async loop → sleep N seconds → read data → process → write to DB/Redis/HAL

**Router Pattern (FastAPI):**
- Purpose: Modular endpoint organization
- Examples: `backend/app/api/v1/dns.py`, `backend/app/api/v1/devices.py`
- Pattern: Define APIRouter → include in main router with prefix + tags

**HAL Drivers:**
- Purpose: Isolate system-specific operations
- Examples: `backend/app/hal/linux_nftables.py`, `backend/app/hal/linux_driver.py`
- Pattern: Async methods wrapping Linux commands (nftables, ip link, tc, isc-dhcp-server)

## Entry Points

**Frontend:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser load, Vite dev server start, `npm run build`
- Responsibilities: Mount React app to DOM, setup Router, init BrowserRouter

**Frontend App Root:**
- Location: `frontend/src/App.tsx`
- Triggers: Main.tsx render
- Responsibilities: Define routes, apply AuthGuard, layout composition

**Backend:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Responsibilities: Create FastAPI instance, register lifespan handlers, include routers, start workers

**Backend Lifespan (Startup):**
- Location: `backend/app/main.py` lifespan context manager
- Triggers: Uvicorn startup
- Responsibilities:
  1. Create MariaDB tables via SQLAlchemy
  2. Sync blocked devices to nftables
  3. Start 12 background workers (DNS, traffic monitor, device discovery, etc.)
  4. Load blocklists from disk/web
  5. Rebuild Redis caches (category domains, profile domains, device profile mapping)

**WebSocket Endpoint:**
- Location: `backend/app/api/v1/ws.py` route: `/api/v1/ws/live`
- Triggers: Frontend `useWebSocket()` connection
- Responsibilities: Accept client connection, broadcast bandwidth/DNS/device/traffic data every 2s

## Error Handling

**Strategy:**
- Frontend: Try-catch blocks in async API calls, user feedback via notifications
- Backend: FastAPI exception handlers (HTTPException for validation), async try-catch in workers
- Database: SQLAlchemy session rollback on exception, transaction atomicity

**Patterns:**
- **Validation:** Pydantic schemas validate request input (auto 422 response on fail)
- **Auth:** 401 Unauthorized triggers logout + redirect to login (via axios response interceptor)
- **Worker Failures:** Try-catch logs error, continues loop (no hard fail)
- **HAL Failures:** Return error response to API, user sees "Operation failed" message

## Cross-Cutting Concerns

**Logging:**
- Backend: Python logging module (INFO level default, configurable via ENV)
- Frontend: Browser console (console.log/error in development, silent in production)
- Workers: Per-worker logger (tonbilai.{worker_name})

**Validation:**
- Frontend: TypeScript types prevent most errors at compile time
- Backend: Pydantic schemas enforce runtime validation (request/response)
- Database: NOT NULL constraints, foreign keys, unique constraints

**Authentication:**
- Frontend: JWT token in localStorage, included in Authorization header
- Backend: FastAPI Depends(get_current_user) validates token signature + expiry
- Session: Token-based (stateless), no server-side session storage

**Rate Limiting:**
- Backend: API endpoints limited per origin (via middleware in production)
- Frontend: API calls debounced/throttled where needed (e.g., domain search in ContentCategoriesPage)

---

*Architecture analysis: 2026-02-25*
