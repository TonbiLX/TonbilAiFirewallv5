# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**LLM (AI Analysis & Chat):**
- OpenAI API - Chat completions (GPT-4o, GPT-3.5-turbo, GPT-4.1)
  - SDK/Client: httpx (no official SDK, direct HTTP calls)
  - Auth: API key stored in `AiConfig` database table
  - Endpoint: Configurable via `AiConfig.base_url` (default: https://api.openai.com)
  - Usage: `backend/app/services/llm_providers.py` + `backend/app/services/llm_service.py`

- Anthropic Claude API - Chat completions (Claude Sonnet 4.5, Claude Haiku 4.5)
  - SDK/Client: httpx (no official SDK, direct HTTP calls)
  - Auth: API key stored in `AiConfig` database table
  - Endpoint: Configurable via `AiConfig.base_url` (default: https://api.anthropic.com)
  - Usage: `backend/app/services/llm_providers.py` + `backend/app/services/llm_service.py`
  - Features: 200K context window, streaming support planned

- Local/Self-Hosted LLM - Custom endpoint support
  - SDK/Client: httpx
  - Auth: Optional API key in `AiConfig.api_key_local`
  - Endpoint: User-configurable in UI
  - Usage: Same service architecture, different base_url

**Telegram Bot API:**
- Telegram Bot API - Push notifications and interactive commands
  - SDK/Client: httpx (direct API calls, no aiogram library)
  - Auth: Bot token from `TelegramConfig.bot_token` (database table)
  - Methods Used: `getUpdates` (polling), `sendMessage`, message parsing
  - Endpoints:
    - WebHook receiver: `GET /api/v1/telegram/webhook` (TODO: implement)
    - Polling worker: `backend/app/workers/telegram_worker.py`
  - Config: `backend/app/models/telegram_config.py`
  - Notifications:
    - New device detected
    - IP blocked/unblocked
    - Trusted IP threat alerts
    - AI insights generated

## Data Storage

**Databases:**
- MariaDB 10.5+ (Primary data store)
  - Connection: `mysql+aiomysql://tonbilai:PASSWORD@localhost:3306/tonbilaios`
  - Env var: `DATABASE_URL`
  - Client: SQLAlchemy 2.0.36 + aiomysql async driver
  - ORM: SQLAlchemy declarative base in `backend/app/models/`
  - Migrations: Alembic (not currently in use, manual schema management)
  - Tables: 30+ models covering devices, DNS, firewall, VPN, users, logs, etc.

**Cache & Real-Time:**
- Redis 6.0+ (Session cache, flow tracking, DNS domain sets)
  - Connection: `redis://localhost:6379/0` (configurable via REDIS_URL)
  - Client: redis-py 5.2.0 with hiredis C speedup
  - Key patterns:
    - `flow:live:{flow_id}` - Active connection flow data (60s TTL)
    - `flow:active_ids` - Set of active flow IDs (60s TTL)
    - `flow:device:{device_id}` - Device's flow IDs (60s TTL)
    - `flow:large` - Large transfer tracking ZSET (60s TTL)
    - `dns:category_domains:{key}` - Blocklist domains by category
    - `dns:profile_domains:{profile_id}` - Profile filter domain union
    - `dns:device_profile:{device_id}` - Device-to-profile mapping
    - `dns:ip_to_device:{ip}` - IP-to-device reverse mapping
    - `dns:blocked_domains` - Global blocklist
    - `dns:blocked_device_ids` - Set of blocked devices
  - Usage: Per-flow real-time tracking, DNS filtering cache, session storage

**File Storage:**
- Local filesystem only
  - Blocklist downloads: `/opt/tonbilaios/backend/cache/blocklists/` (cached, 6-hour rotation)
  - Log archives: `/opt/tonbilaios/backend/logs/signed/` (2-year retention per 5651 Law)
  - Frontend build: `/opt/tonbilaios/frontend/dist/` (static assets)
  - System config: `/opt/tonbilaios/config/` (TLS certs, VPN configs, system settings)

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based authentication
  - Implementation: `backend/app/api/v1/auth.py`
  - Token storage: Frontend localStorage (key: token, refresh_token)
  - Token lifetime: Configurable in AiConfig
  - Validation: PyJWT 2.9.0 with SECRET_KEY from environment
  - Password hashing: bcrypt 4.2.0
  - Endpoints:
    - `POST /api/v1/auth/login` - Username/password → JWT
    - `POST /api/v1/auth/setup` - Initial admin setup (if no users)
    - `GET /api/v1/auth/check` - Verify token validity
    - `POST /api/v1/auth/change-password` - Password update
    - `GET /api/v1/auth/me` - Current user profile
    - `POST /api/v1/auth/logout` - Clear token (frontend handles)

- Frontend token management: `frontend/src/services/tokenStore.ts`
  - Interceptor: All requests include `Authorization: Bearer {token}`
  - Refresh: Automatic on 401 response
  - Storage: localStorage with fallback to sessionStorage

## Monitoring & Observability

**Error Tracking:**
- Not detected - Errors logged to stdout/systemd journal

**Logs:**
- System logs: FastAPI logger to stdout (captured by systemd)
- Database logs: `SystemLog` model in MariaDB
- DNS logs: `DnsQueryLog` model (queries, blocks, timing)
- Device logs: `DeviceConnectionLog` (connection events)
- Signed logs: Cryptographic signatures stored in `LogSignature` model
  - Signing worker: `backend/app/workers/log_signer.py`
  - Retention: 2 years (730 days) per Turkish Law 5651
  - Location: `/opt/tonbilaios/backend/logs/signed/`
  - Archival: Automatic rotation and compression

**System Metrics:**
- System Monitor Service: `backend/app/services/system_monitor_service.py`
  - CPU, memory, disk, temperature tracking
  - Polling interval: 5 seconds
  - History buffer: 60 entries (5 minute window)
  - WebSocket real-time updates

## CI/CD & Deployment

**Hosting:**
- Raspberry Pi on local network (192.168.1.2)
- Remote access via SSH jump host (pi.tonbil.com:2323)
- IP: 192.168.1.2, Port 2323 for API (behind reverse proxy)

**CI Pipeline:**
- Not detected - Manual deployment via:
  - `deploy_dist.py` - Base64-chunked SFTP transfer script
  - `sync_from_pi.py` - Reverse sync (Pi → Local development)
  - Paramiko for SSH tunneling through jump host

**Deployment Process:**
1. Frontend: `npm run build` → `dist/` → SFTP to `/opt/tonbilaios/frontend/dist/`
2. Backend: Manual copy → `/opt/tonbilaios/backend/app/`
3. Systemd restart: `systemctl restart tonbilaios-backend`

## Environment Configuration

**Required env vars (backend/.env):**
- `DATABASE_URL` - MariaDB connection string (mysql+aiomysql://...)
- `REDIS_URL` - Redis connection (redis://localhost:6379/0)
- `ENVIRONMENT` - "development" or "production"
- `SECRET_KEY` - JWT signing key (min 32 chars in production)
- `CORS_ORIGINS` - Comma-separated allowed origins
- `TRUSTED_PROXIES` - CIDR ranges for reverse proxy IPs

**Optional env vars:**
- `SYNC_INTERVAL_SECONDS` - Worker sync frequency (default: 60)
- `MOCK_TRAFFIC_INTERVAL_SECONDS` - Test data generation (default: 5.0)
- `MOCK_DEVICE_COUNT` - Number of mock devices (default: 8)
- `DNS_BLOCKLIST_UPDATE_HOURS` - Blocklist refresh interval (default: 6)
- `DHCP_SIMULATOR_INTERVAL_SECONDS` - DHCP test data (default: 30.0)
- `LOG_RETENTION_DAYS` - Archive retention (default: 730)
- `LOG_SIGNING_ENABLED` - Cryptographic signing (default: true)
- `FLOW_TRACK_INTERVAL_SECONDS` - Connection tracking poll (default: 20)
- `FLOW_DB_SYNC_INTERVAL_SECONDS` - Flow persistence interval (default: 60)
- `FLOW_RETENTION_DAYS` - Flow history retention (default: 7)

**Secrets location:**
- Primary: `.env` file (gitignored, must be manually created)
- Database: Encrypted in MariaDB (API keys in `AiConfig`, `TelegramConfig`)
- JWT tokens: In-memory during session, localStorage client-side

## Webhooks & Callbacks

**Incoming:**
- Telegram webhook endpoint: `GET /api/v1/telegram/webhook` (TODO implementation)
- Current method: Polling via `backend/app/workers/telegram_worker.py`

**Outgoing:**
- Telegram Bot API messages (sendMessage)
- No other external webhook notifications currently implemented

## API Client Architecture

**Frontend HTTP Client:**
- Axios instance: `frontend/src/services/api.ts`
  - Base URL: `/api/v1` (relative, proxied via Vite dev server)
  - Interceptors:
    - Request: Add `Authorization: Bearer {token}` header
    - Response: Handle 401 → refresh token flow
  - Timeout: Axios defaults (no custom timeout set)

**Backend HTTP Client:**
- httpx for all external API calls (async)
  - Used by: LLM providers, Telegram Bot API, future integrations
  - No requests library (async incompatible with workers)
  - SSRF protection: Blocks requests to private/local IPs in `llm_providers.py`

**WebSocket (Real-Time Data):**
- Endpoint: `WS /api/v1/ws`
- Server: websockets 13.1 library
- Client: Built-in browser WebSocket API in `frontend/src/hooks/useWebSocket.ts`
- Data streams:
  - Bandwidth metrics (5s updates)
  - DNS query logs (real-time)
  - Device status changes
  - Flow connection events

---

*Integration audit: 2026-02-25*
