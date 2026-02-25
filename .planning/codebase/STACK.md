# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.x - Backend FastAPI application and worker processes
- TypeScript 5.6.0 - Frontend type-safe React components
- JavaScript (ES2020) - Build output and runtime

**Secondary:**
- Bash - System scripts and deployment automation
- SQL (MariaDB dialect) - Database queries via SQLAlchemy ORM

## Runtime

**Environment:**
- Python 3 - FastAPI/Uvicorn backend (systemd service: tonbilaios-backend)
- Node.js - Frontend development and build
- Raspberry Pi Linux - Deployment target (network driver: Linux nftables, tc, DHCP)

**Package Manager:**
- pip - Python dependencies (`backend/requirements.txt`)
- npm - Node.js dependencies (`frontend/package.json`)
- Lockfile: `frontend/package-lock.json` present

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API and WebSocket framework
- React 18.3.0 - Frontend UI library
- SQLAlchemy 2.0.36 with asyncio - ORM for MariaDB
- Uvicorn 0.32.0 - ASGI server

**Build/Dev:**
- Vite 6.0.0 - Frontend bundler and dev server
- TypeScript 5.6.0 compiler
- pytest-like patterns (testing structure in place)

**Styling:**
- TailwindCSS 3.4.0 - Utility-first CSS framework
- PostCSS 8.4.47 - CSS transformation
- Autoprefixer 10.4.20 - Vendor prefixing

**UI Components:**
- Recharts 2.13.0 - Data visualization and charting
- react-grid-layout 2.2.2 - Responsive drag-and-drop dashboard grid
- Lucide React 0.460.0 - Icon library
- react-router-dom 6.28.0 - Client-side routing
- react-simple-maps 3.0.0 - SVG map rendering for DDoS visualization

## Key Dependencies

**Critical (Backend):**
- httpx 0.28.0 - HTTP client for async LLM API calls (replaces requests)
- aiomysql 0.2.0 - Async MySQL driver for MariaDB
- redis[hiredis] 5.2.0 - Redis cache client with C speedup
- websockets 13.1 - WebSocket server for real-time data
- bcrypt 4.2.0 - Password hashing
- PyJWT 2.9.0 - JWT token generation and validation
- cryptography 44.0.0 - Cryptographic operations
- pydantic 2.10.0 - Data validation and settings
- pydantic-settings 2.6.0 - Environment variable management
- python-dotenv 1.0.1 - .env file loading
- alembic 1.14.0 - Database schema migrations
- python-multipart 0.0.18 - Form data parsing

**Critical (Frontend):**
- axios 1.7.0 - HTTP client for REST API calls with interceptors
- clsx 2.1.0 - Conditional CSS class composition

**Dev Dependencies (Frontend):**
- @vitejs/plugin-react 4.3.0 - React Fast Refresh for Vite
- @types/react 18.3.0 - React type definitions
- @types/react-dom 18.3.0 - ReactDOM type definitions
- @tailwindcss/forms 0.5.9 - Form element styling
- Vite plugins as specified in `vite.config.ts`

## Configuration

**Environment:**
- `.env` file required at `backend/.env` (configured via pydantic-settings)
- `backend/app/config.py` loads settings: DATABASE_URL, REDIS_URL, SECRET_KEY, ENVIRONMENT, CORS_ORIGINS, TRUSTED_PROXIES
- `frontend/vite.config.ts` defines dev server proxy: `/api/*` → `http://backend:8000`
- TypeScript config: `frontend/tsconfig.json` (strict: false, target: ES2020)

**Build:**
- `frontend/vite.config.ts` - Vite configuration with React plugin and dev proxy
- Frontend build output: `dist/` directory (sourcemap: false in production)
- Backend entry: `backend/app/main.py`

**Security:**
- JWT token-based authentication (PyJWT)
- CORS middleware with configurable origins
- Trusted proxy IP filtering to prevent spoofing
- Secret key validation (minimum 32 chars in production)

## Platform Requirements

**Development:**
- Python 3.7+
- Node.js 18+ (for npm)
- MariaDB 10.5+ or MySQL 8.0+
- Redis 6.0+
- Git

**Production:**
- Raspberry Pi (ARM-based Linux)
- Linux kernel with nftables support
- WireGuard kernel module (for VPN)
- MariaDB service
- Redis service
- Systemd for service management
- SSH access (via jump host pi.tonbil.com:2323)

## Infrastructure Dependencies

**System Libraries (Backend):**
- nftables - Firewall rule management (no Python package, exec via HAL)
- Linux Traffic Control (tc) - QoS management (no Python package)
- conntrack - Connection tracking parser (no Python package)
- WireGuard - VPN management (no Python package, wg CLI via subprocess)

**Database:**
- MariaDB 10.5+ - Production data store
- Schema: `tonbilaios` (created via SQLAlchemy on first run)

**Cache:**
- Redis 6.0+ - Session cache, real-time flow tracking, DNS domain sets

## Notable Architectural Patterns

**Async Throughout:**
- All database queries are async via `aiomysql` and `SQLAlchemy[asyncio]`
- WebSocket connections handled by `websockets` library
- Redis operations are async-compatible
- LLM API calls use `httpx` for async HTTP

**Worker Model:**
- Background workers started in FastAPI lifespan events:
  - `blocklist_worker` - DNS blocklist downloads and category domain caching
  - `dns_proxy` - DNS query interception and filtering
  - `device_discovery` - ARP-based LAN discovery
  - `dhcp_worker` - DHCP lease management
  - `flow_tracker` - Per-flow connection tracking (20s intervals)
  - `traffic_monitor` - Traffic aggregation and analysis
  - `bandwidth_monitor` - Per-device bandwidth tracking
  - `threat_analyzer` - DDoS and threat detection
  - `telegram_worker` - Telegram bot message polling
  - `llm_log_analyzer` - Log analysis via LLM
  - `system_monitor_worker` - System metrics collection

**Multi-Provider LLM Support:**
- OpenAI (GPT-4o, GPT-3.5-turbo)
- Anthropic Claude (Sonnet, Haiku)
- Local/self-hosted via custom base_url
- No vendor lock-in; httpx used for all API calls

---

*Stack analysis: 2026-02-25*
